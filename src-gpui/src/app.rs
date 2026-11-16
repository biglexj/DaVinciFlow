use crate::{
    bridge, library,
    subtitles::{self, Document},
    ui::*,
};
use gpui_kit::component::input::{Input, InputEvent, InputState, Textarea, TextareaState};
use gpui_kit::{prelude::*, *};
use std::path::PathBuf;

#[derive(Clone, Copy, PartialEq)]
enum Tab {
    Subtitles,
    Library,
    Resolve,
}

pub struct FlowApp {
    tab: Tab,
    document: Document,
    dirty: bool,
    selected: Option<usize>,
    filtered_cues: Vec<usize>,
    inventory: library::Inventory,
    filtered_resources: Vec<usize>,
    filter: Entity<InputState>,
    find: Entity<InputState>,
    replacement: Entity<InputState>,
    edit: Entity<TextareaState>,
    case_sensitive: bool,
    busy: bool,
    message: String,
    error: bool,
    resolve: Option<bridge::ResolveStatus>,
    _subscriptions: Vec<Subscription>,
    close_prompt: bool,
}

impl FlowApp {
    pub fn new(window: &mut Window, cx: &mut Context<Self>) -> Self {
        let filter = cx.new(|cx| InputState::new(window, cx).placeholder("Filtrar por texto…"));
        let find = cx.new(|cx| InputState::new(window, cx).placeholder("Buscar texto"));
        let replacement = cx.new(|cx| InputState::new(window, cx).placeholder("Reemplazar por"));
        let edit = cx.new(|cx| {
            TextareaState::new(window, cx).placeholder("Selecciona un subtítulo para editarlo")
        });
        let subscriptions = vec![
            cx.subscribe(&filter, |this, _, event, cx| {
                if matches!(event, InputEvent::Change) {
                    this.refilter(cx);
                }
            }),
            cx.subscribe(&edit, |_, _, _: &InputEvent, cx| cx.notify()),
        ];
        let weak = cx.entity().downgrade();
        window.on_window_should_close(cx, move |window, cx| {
            weak.update(cx, |this, cx| this.request_close(window, cx))
                .unwrap_or(true)
        });
        let mut app = Self {
            tab: Tab::Subtitles,
            document: Document::default(),
            dirty: false,
            selected: None,
            filtered_cues: vec![],
            inventory: Default::default(),
            filtered_resources: vec![],
            filter,
            find,
            replacement,
            edit,
            case_sensitive: false,
            busy: false,
            message: "Abre un SRT o captura la pista 1 de Resolve para comenzar.".into(),
            error: false,
            resolve: None,
            _subscriptions: subscriptions,
            close_prompt: false,
        };
        if let Some(path) = std::env::args_os().nth(1) {
            let path = PathBuf::from(path);
            app.work(
                "Leyendo SRT…",
                window,
                cx,
                move || subtitles::load(&path),
                |this, doc, window, cx| this.install_document(doc, window, cx),
            );
        }
        app
    }

    fn has_draft(&self, cx: &App) -> bool {
        self.selected
            .is_some_and(|i| self.edit.read(cx).value().as_ref() != self.document.cues[i].text)
    }

    fn request_close(&mut self, window: &mut Window, cx: &mut Context<Self>) -> bool {
        if self.busy {
            self.notify(
                Err("Espera a que termine la operación antes de cerrar.".into()),
                cx,
            );
            return false;
        }
        if !self.dirty && !self.has_draft(cx) {
            return true;
        }
        if self.close_prompt {
            return false;
        }
        self.close_prompt = true;
        let receiver = window.prompt(
            PromptLevel::Warning,
            "Hay cambios sin exportar",
            Some(
                "Puedes volver para exportar el SRT o cerrar y descartar los cambios de esta demo.",
            ),
            &[
                PromptButton::Cancel("Volver".into()),
                PromptButton::Ok("Cerrar sin exportar".into()),
            ],
            cx,
        );
        cx.spawn_in(window, async move |this, cx| {
            let close = receiver.await.ok() == Some(1);
            let _ = this.update_in(cx, |this, window, cx| {
                this.close_prompt = false;
                if close {
                    window.remove_window();
                } else {
                    cx.notify();
                }
            });
        })
        .detach();
        false
    }

    fn notify(&mut self, result: Result<String, String>, cx: &mut Context<Self>) {
        self.error = result.is_err();
        self.message = match result {
            Ok(s) | Err(s) => s,
        };
        cx.notify();
    }

    fn refilter(&mut self, cx: &mut Context<Self>) {
        let query = self.filter.read(cx).value().to_lowercase();
        self.filtered_cues = self
            .document
            .cues
            .iter()
            .enumerate()
            .filter(|(_, c)| {
                query.is_empty()
                    || c.text.to_lowercase().contains(&query)
                    || c.original.to_lowercase().contains(&query)
            })
            .map(|(i, _)| i)
            .collect();
        self.filtered_resources = self
            .inventory
            .resources
            .iter()
            .enumerate()
            .filter(|(_, r)| {
                query.is_empty()
                    || r.name.to_lowercase().contains(&query)
                    || r.category.to_lowercase().contains(&query)
            })
            .map(|(i, _)| i)
            .collect();
        cx.notify();
    }

    fn select_cue(&mut self, index: usize, window: &mut Window, cx: &mut Context<Self>) {
        self.selected = Some(index);
        let text = self.document.cues[index].text.clone();
        self.edit
            .update(cx, |state, cx| state.set_value(text, window, cx));
        cx.notify();
    }

    fn install_document(&mut self, doc: Document, window: &mut Window, cx: &mut Context<Self>) {
        self.document = doc;
        self.dirty = false;
        self.selected = None;
        self.filter.update(cx, |s, cx| s.set_value("", window, cx));
        self.refilter(cx);
        if !self.document.cues.is_empty() {
            self.select_cue(0, window, cx);
        }
        let warnings = self.document.warnings.join(" ");
        self.notify(
            Ok(format!(
                "{} subtítulos cargados. {warnings}",
                self.document.cues.len()
            )),
            cx,
        );
    }

    // Un solo trabajo por ventana; el executor mantiene I/O y Python fuera del render.
    fn work<T: Send + 'static>(
        &mut self,
        message: &str,
        window: &mut Window,
        cx: &mut Context<Self>,
        job: impl FnOnce() -> Result<T, String> + Send + 'static,
        done: impl FnOnce(&mut Self, T, &mut Window, &mut Context<Self>) + 'static,
    ) {
        if self.busy {
            return;
        }
        self.busy = true;
        self.notify(Ok(message.into()), cx);
        let task = cx.background_executor().spawn(async move { job() });
        cx.spawn_in(window, async move |this, cx| {
            let result = task.await;
            let _ = this.update_in(cx, |this, window, cx| {
                this.busy = false;
                match result {
                    Ok(value) => done(this, value, window, cx),
                    Err(e) => this.notify(Err(e), cx),
                }
                cx.notify();
            });
        })
        .detach();
    }

    fn choose_srt(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if self.busy {
            return;
        }
        if self.dirty || self.has_draft(cx) {
            self.notify(
                Err("Exporta o restaura los cambios antes de abrir otra fuente.".into()),
                cx,
            );
            return;
        }
        let receiver = cx.prompt_for_paths(PathPromptOptions {
            files: true,
            directories: false,
            multiple: false,
            prompt: Some("Abrir subtítulos SRT".into()),
        });
        cx.spawn_in(window, async move |this, cx| {
            let selection = receiver.await;
            let _ = this.update_in(cx, |this, window, cx| match selection {
                Ok(Ok(Some(paths))) => {
                    if let Some(path) = paths.into_iter().next() {
                        this.work(
                            "Leyendo SRT…",
                            window,
                            cx,
                            move || subtitles::load(&path),
                            |this, doc, window, cx| this.install_document(doc, window, cx),
                        );
                    }
                }
                Ok(Ok(None)) => {}
                _ => this.notify(Err("No se pudo abrir el selector de archivos.".into()), cx),
            });
        })
        .detach();
    }

    fn export(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if self.busy || self.document.cues.is_empty() {
            return;
        }
        let directory = std::env::var_os("USERPROFILE")
            .map(PathBuf::from)
            .unwrap_or_else(bridge::root);
        let receiver = cx.prompt_for_new_path(&directory, Some("subtitulos-corregidos.srt"));
        let content = self.document.export();
        cx.spawn_in(window, async move |this, cx| {
            let selection = receiver.await;
            let _ = this.update_in(cx, |this, window, cx| match selection {
                Ok(Ok(Some(mut path))) => {
                    if path.extension().is_none() {
                        path.set_extension("srt");
                    }
                    if !path
                        .extension()
                        .is_some_and(|s| s.eq_ignore_ascii_case("srt"))
                    {
                        this.notify(Err("La exportación debe tener extensión .srt.".into()), cx);
                        return;
                    }
                    this.work(
                        "Exportando subtítulos…",
                        window,
                        cx,
                        move || {
                            subtitles::save_new(&path, &content)?;
                            Ok(path)
                        },
                        |this, path, _, cx| {
                            this.dirty = false;
                            this.notify(Ok(format!("SRT exportado: {}", path.display())), cx);
                        },
                    );
                }
                Ok(Ok(None)) => {}
                _ => this.notify(
                    Err("No se pudo abrir el diálogo de exportación.".into()),
                    cx,
                ),
            });
        })
        .detach();
    }

    fn capture(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if self.dirty || self.has_draft(cx) {
            self.notify(
                Err("Exporta o restaura los cambios antes de capturar otra fuente.".into()),
                cx,
            );
            return;
        }
        self.work(
            "Leyendo la pista 1 de Resolve…",
            window,
            cx,
            bridge::subtitles,
            |this, doc, window, cx| {
                this.tab = Tab::Subtitles;
                this.install_document(doc, window, cx);
            },
        );
    }

    fn check_resolve(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.resolve = None;
        self.work(
            "Consultando Resolve…",
            window,
            cx,
            bridge::status,
            |this, status, _, cx| {
                let message = status.description.clone();
                let running = status.running;
                this.resolve = Some(status);
                this.notify(if running { Ok(message) } else { Err(message) }, cx);
            },
        );
    }

    fn choose_library(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let receiver = cx.prompt_for_paths(PathPromptOptions {
            files: false,
            directories: true,
            multiple: false,
            prompt: Some("Elegir carpeta de biblioteca".into()),
        });
        cx.spawn_in(window, async move |this, cx| {
            let selection = receiver.await;
            let _ = this.update_in(cx, |this, window, cx| match selection {
                Ok(Ok(Some(paths))) => {
                    if let Some(path) = paths.into_iter().next() {
                        this.scan_library(path, window, cx);
                    }
                }
                Ok(Ok(None)) => {}
                _ => this.notify(Err("No se pudo abrir el selector de carpetas.".into()), cx),
            });
        })
        .detach();
    }

    fn scan_library(&mut self, path: PathBuf, window: &mut Window, cx: &mut Context<Self>) {
        self.work(
            "Leyendo biblioteca…",
            window,
            cx,
            move || library::scan(&path, 2000),
            |this, inventory, _, cx| {
                let count = inventory.resources.len();
                let warnings = inventory.warnings.join(" ");
                this.inventory = inventory;
                this.refilter(cx);
                this.notify(Ok(format!("{count} recursos encontrados. {warnings}")), cx);
            },
        );
    }

    fn normalize(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let result = self.document.normalize();
        self.after_batch(result, window, cx);
    }

    fn replace(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let find = self.find.read(cx).value();
        let replacement = self.replacement.read(cx).value();
        let result = self
            .document
            .replace(&find, &replacement, self.case_sensitive);
        self.after_batch(result, window, cx);
    }

    fn after_batch(
        &mut self,
        result: Result<usize, String>,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        if let Ok(count) = &result {
            self.dirty |= *count > 0;
        }
        if let Some(i) = self.selected {
            self.select_cue(i, window, cx);
        }
        self.refilter(cx);
        self.notify(
            result.map(|n| format!("{n} subtítulos modificados. Los tiempos se conservan.")),
            cx,
        );
    }

    fn save_edit(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if let Some(i) = self.selected {
            let value = self
                .edit
                .read(cx)
                .value()
                .lines()
                .map(str::trim)
                .filter(|line| !line.is_empty())
                .collect::<Vec<_>>()
                .join("\n");
            if value.trim().is_empty() {
                self.notify(Err("El subtítulo no puede quedar vacío.".into()), cx);
                return;
            }
            if self.document.cues[i].text != value {
                self.document.cues[i].text = value;
                self.dirty = true;
            }
            self.refilter(cx);
            self.notify(
                Ok(format!(
                    "Cambio guardado en el bloque {}. Exporta el SRT para conservarlo en disco.",
                    i + 1
                )),
                cx,
            );
            self.select_cue(i, window, cx);
        }
    }

    fn restore_all(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        for cue in &mut self.document.cues {
            cue.text = cue.original.clone();
        }
        self.dirty = false;
        if let Some(i) = self.selected {
            self.select_cue(i, window, cx);
        }
        self.refilter(cx);
        self.notify(
            Ok("Se han restaurado los textos de la fuente original.".into()),
            cx,
        );
    }
}

mod views;
