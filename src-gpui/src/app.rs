use crate::{
    bridge, library,
    subtitles::{self, Document},
    ui::*,
};
use davinci_flow_gpui::session::SubtitleSession;
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
    session: SubtitleSession,
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
            cx.subscribe(&edit, |this, state, event: &InputEvent, cx| {
                if matches!(event, InputEvent::Change) {
                    this.session.set_draft(state.read(cx).value().to_string());
                }
                cx.notify();
            }),
        ];
        let weak = cx.entity().downgrade();
        window.on_window_should_close(cx, move |window, cx| {
            weak.update(cx, |this, cx| this.request_close(window, cx))
                .unwrap_or(true)
        });
        let mut app = Self {
            tab: Tab::Subtitles,
            session: SubtitleSession::default(),
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

    fn sync_editor(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let text = self.session.draft().to_owned();
        self.edit
            .update(cx, |state, cx| state.set_value(text, window, cx));
        cx.notify();
    }

    fn request_close(&mut self, window: &mut Window, cx: &mut Context<Self>) -> bool {
        if self.busy {
            self.notify(
                Err("Espera a que termine la operación antes de cerrar.".into()),
                cx,
            );
            return false;
        }
        if !self.session.is_dirty() && !self.session.has_draft() {
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
        self.filtered_cues = self.session.filtered_indices(&query);
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
        match self.session.select(index) {
            Ok(()) => self.sync_editor(window, cx),
            Err(error) => self.notify(Err(error), cx),
        }
    }

    fn install_document(&mut self, doc: Document, window: &mut Window, cx: &mut Context<Self>) {
        if let Err(error) = self.session.load(doc) {
            self.notify(Err(error), cx);
            return;
        }
        self.filter.update(cx, |s, cx| s.set_value("", window, cx));
        self.refilter(cx);
        self.sync_editor(window, cx);
        let document = self.session.document();
        let warnings = document.warnings.join(" ");
        self.notify(
            Ok(format!(
                "{} subtítulos cargados. {warnings}",
                document.cues.len()
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
        if self.session.is_dirty() || self.session.has_draft() {
            self.notify(
                Err("Guarda o descarta la edición pendiente y exporta o deshaz los cambios antes de abrir otra fuente.".into()),
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
        if self.busy || self.session.document().cues.is_empty() {
            return;
        }
        let snapshot = match self.session.export_snapshot() {
            Ok(snapshot) => snapshot,
            Err(error) => {
                self.notify(Err(error), cx);
                return;
            }
        };
        let directory = std::env::var_os("USERPROFILE")
            .map(PathBuf::from)
            .unwrap_or_else(bridge::root);
        let receiver = cx.prompt_for_new_path(&directory, Some("subtitulos-corregidos.srt"));
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
                            let receipt = snapshot.save_new(&path)?;
                            Ok((path, receipt))
                        },
                        |this, (path, receipt), _, cx| {
                            let result = this
                                .session
                                .accept_export(receipt)
                                .map(|()| format!("SRT exportado: {}", path.display()));
                            this.notify(result, cx);
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
        if self.session.is_dirty() || self.session.has_draft() {
            self.notify(
                Err("Guarda o descarta la edición pendiente y exporta o deshaz los cambios antes de capturar otra fuente.".into()),
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
        let result = self.session.normalize();
        self.after_batch(result, window, cx);
    }

    fn replace(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let find = self.find.read(cx).value();
        let replacement = self.replacement.read(cx).value();
        let result = self
            .session
            .replace(&find, &replacement, self.case_sensitive);
        self.after_batch(result, window, cx);
    }

    fn after_batch(
        &mut self,
        result: Result<usize, String>,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        if result.is_ok() {
            self.sync_editor(window, cx);
            self.refilter(cx);
        }
        self.notify(
            result.map(|n| format!("{n} subtítulos modificados. Los tiempos se conservan.")),
            cx,
        );
    }

    fn save_edit(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let result = self.session.save_draft();
        if result.is_ok() {
            self.sync_editor(window, cx);
            self.refilter(cx);
        }
        self.notify(
            result.map(|_| "Cambio guardado. Exporta el SRT para conservarlo en disco.".into()),
            cx,
        );
    }

    fn discard_edit(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.session.discard_draft();
        self.sync_editor(window, cx);
    }

    fn restore_all(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let result = self.session.restore_all();
        self.after_batch(result, window, cx);
    }

    fn history(&mut self, redo: bool, window: &mut Window, cx: &mut Context<Self>) {
        let result = if redo {
            self.session.redo()
        } else {
            self.session.undo()
        };
        if result.is_ok() {
            self.sync_editor(window, cx);
            self.refilter(cx);
        }
        self.notify(
            result.map(|()| {
                if redo {
                    "Cambio rehecho.".into()
                } else {
                    "Cambio deshecho.".into()
                }
            }),
            cx,
        );
    }
}

mod views;
