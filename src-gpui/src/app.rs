//! Estado y acciones de la ventana nativa; la presentación vive en los módulos `app::*`.
//!
//! La estructura reproduce la interfaz Flet vigente: barra lateral con las mismas
//! pestañas, encabezado con el nombre del módulo, área de trabajo y pie de estado.
pub mod about;
pub mod ai_actions;
pub mod assistant_view;
pub mod catalogs_view;
pub mod editor_actions;
pub mod editor_view;
pub mod fetch_view;
pub mod library_actions;
pub mod library_view;
pub mod media_actions;
pub mod media_view;
pub mod review_view;
pub mod service_actions;
pub mod settings_view;
pub mod shell;
pub mod subtitles_view;
pub mod updates;
pub mod views;
pub mod voice_view;

use crate::{
    bridge, library,
    preferences::Preferences,
    subtitles::{self, Document},
    ui::*,
};
use davinci_flow_gpui::editorial;
use davinci_flow_gpui::media;
use davinci_flow_gpui::services;
use davinci_flow_gpui::session::SubtitleSession;
use gpui_kit::assets::IconName;
use gpui_kit::component::input::{Input, InputEvent, InputState, Textarea, TextareaState};
use gpui_kit::{prelude::*, *};
use serde_json::Value;
use std::collections::BTreeMap;
use std::path::PathBuf;

/// Pestañas de la ventana; nombres y orden siguen la interfaz vigente.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Tab {
    Assistant,
    Editor,
    Subtitles,
    Voice,
    Brolls,
    Music,
    Sfx,
    Catalog,
    Fetch,
    Library,
    Settings,
}

impl Tab {
    /// Pestañas del grupo principal de la barra lateral.
    pub const MAIN: [Tab; 9] = [
        Tab::Assistant,
        Tab::Editor,
        Tab::Subtitles,
        Tab::Voice,
        Tab::Brolls,
        Tab::Music,
        Tab::Sfx,
        Tab::Catalog,
        Tab::Fetch,
    ];
    /// Pestañas fijadas al pie de la barra lateral.
    pub const FOOT: [Tab; 2] = [Tab::Library, Tab::Settings];

    pub fn label(self) -> &'static str {
        match self {
            Tab::Assistant => "Asistente IA",
            Tab::Editor => "Editor",
            Tab::Subtitles => "Corrección",
            Tab::Voice => "Generación de voz",
            Tab::Brolls => "B-Rolls",
            Tab::Music => "Música",
            Tab::Sfx => "Efectos (SFX)",
            Tab::Catalog => "Plantillas",
            Tab::Fetch => "Luna Fetch",
            Tab::Library => "Biblioteca",
            Tab::Settings => "Ajustes",
        }
    }

    pub fn icon(self) -> IconName {
        match self {
            Tab::Assistant => IconName::Sparkles,
            Tab::Editor => IconName::SquarePen,
            Tab::Subtitles => IconName::SpellCheck,
            Tab::Voice => IconName::MicVocal,
            Tab::Brolls => IconName::Clapperboard,
            Tab::Music => IconName::Music,
            Tab::Sfx => IconName::AudioLines,
            Tab::Catalog => IconName::Type,
            Tab::Fetch => IconName::CloudDownload,
            Tab::Library => IconName::Folder,
            Tab::Settings => IconName::Settings,
        }
    }

    /// El módulo dispone de vista nativa con acciones reales.
    pub fn migrated(self) -> bool {
        matches!(
            self,
            Tab::Assistant
                | Tab::Editor
                | Tab::Subtitles
                | Tab::Brolls
                | Tab::Music
                | Tab::Sfx
                | Tab::Catalog
                | Tab::Library
                | Tab::Settings
                | Tab::Voice
                | Tab::Fetch
        )
    }
}

pub struct FlowApp {
    pub tab: Tab,
    pub pending_tab: Option<Tab>,
    pub session: SubtitleSession,
    pub filtered_cues: Vec<usize>,
    pub find: Entity<InputState>,
    pub replacement: Entity<InputState>,
    pub glossary: Entity<TextareaState>,
    pub edit: Entity<TextareaState>,
    pub case_sensitive: bool,
    pub preferences: Preferences,
    pub library_category: String,
    pub library_inventory: library::Inventory,
    pub library_filter: Entity<InputState>,
    pub library_filtered: Vec<usize>,
    pub library_scan_pending: bool,
    pub editor_track: Entity<InputState>,
    pub editor_fps: Entity<InputState>,
    pub editor_first: Entity<InputState>,
    pub editor_last: Entity<InputState>,
    pub editor_stage: u8,
    pub editor_options: editorial::Options,
    pub editor_direction: Entity<InputState>,
    pub capture_snapshot: Option<Value>,
    pub proposal: Option<editorial::Proposal>,
    pub proposal_input: Vec<(u64, u64, String)>,
    pub proposal_dirty: bool,
    pub review_selected: usize,
    pub review_context: Entity<TextareaState>,
    pub review_main: Entity<TextareaState>,
    pub review_accent: Entity<TextareaState>,
    pub review_note: Entity<InputState>,
    pub review_enabled: bool,
    pub review_templates: BTreeMap<String, String>,
    pub review_template_layer: Option<String>,
    pub template_filter: Entity<InputState>,
    pub last_application: Option<Value>,
    pub fetch_url: Entity<InputState>,
    pub fetch_directory: Entity<InputState>,
    pub fetch_audio: bool,
    pub fetch_import: bool,
    pub fetch_info: Option<media::MediaInfo>,
    pub fetch_result: Option<media::Download>,
    pub voice_text: Entity<TextareaState>,
    pub voice_catalog: media::VoiceCatalog,
    pub voice_selected: Option<usize>,
    pub voice_quote: Option<(String, String, u64)>,
    pub voice_output: Option<PathBuf>,
    pub media_preview: Option<PathBuf>,
    pub media_source: Option<PathBuf>,
    // Panel de IA y guion de la pestaña «Corrección».
    pub ai_panel_open: bool,
    pub ai_script: Entity<TextareaState>,
    pub ai_detect_markers: bool,
    pub ai_markers: Vec<services::Marker>,
    pub ai_snapshot: Option<Value>,
    pub about_open: bool,
    pub busy: bool,
    pub message: String,
    pub error: bool,
    pub resolve: Option<bridge::ResolveStatus>,
    // Asistente IA
    pub assistant_messages: Vec<AssistantMessage>,
    pub assistant_prompt: Entity<InputState>,
    // Ajustes
    pub settings: Option<services::Settings>,
    pub settings_provider: String,
    pub settings_model: String,
    pub settings_model_input: Entity<InputState>,
    pub settings_key: Entity<InputState>,
    pub settings_models: Vec<String>,
    pub settings_status: String,
    // Actualizaciones
    pub release: Option<services::Release>,
    pub release_checked: bool,
    // Catálogos
    pub sfx_assets: Vec<services::SfxAsset>,
    pub templates: Vec<services::TemplateInfo>,
    pub catalog_diagnostics: Vec<String>,
    pub _subscriptions: Vec<Subscription>,
    pub close_prompt: bool,
}

/// Mensaje del hilo del asistente.
#[derive(Clone, Debug)]
pub struct AssistantMessage {
    pub sender: &'static str,
    pub content: String,
    pub is_ai: bool,
}

impl FlowApp {
    pub fn new(window: &mut Window, cx: &mut Context<Self>) -> Self {
        let find = cx.new(|cx| InputState::new(window, cx).placeholder("Buscar texto"));
        let replacement = cx.new(|cx| InputState::new(window, cx).placeholder("Reemplazar por"));
        let glossary = cx.new(|cx| {
            TextareaState::new(window, cx).placeholder("palabra: Reemplazo, término -> Corrección")
        });
        let edit = cx.new(|cx| {
            TextareaState::new(window, cx).placeholder("Selecciona un subtítulo para editarlo")
        });
        let library_filter =
            cx.new(|cx| InputState::new(window, cx).placeholder("Buscar en esta categoría"));
        let editor_track = cx.new(|cx| InputState::new(window, cx).placeholder("Pista"));
        let editor_fps = cx.new(|cx| InputState::new(window, cx).placeholder("FPS SRT"));
        let editor_first = cx.new(|cx| InputState::new(window, cx).placeholder("Desde"));
        let editor_last = cx.new(|cx| InputState::new(window, cx).placeholder("Hasta"));
        let editor_direction = cx.new(|cx| {
            InputState::new(window, cx)
                .placeholder("Dirección creativa para esta propuesta (opcional)")
        });
        let assistant_prompt = cx.new(|cx| {
            InputState::new(window, cx)
                .placeholder("Pregunta sobre ideas, tono narrativo, B-Rolls o dirección creativa…")
        });
        let settings_key = cx.new(|cx| {
            InputState::new(window, cx)
                .placeholder("Clave API")
                .masked(true)
        });
        let settings_model_input = cx.new(|cx| InputState::new(window, cx).placeholder("Modelo"));
        let review_context = cx.new(|cx| TextareaState::new(window, cx).placeholder("Contexto"));
        let review_main =
            cx.new(|cx| TextareaState::new(window, cx).placeholder("Texto principal"));
        let review_accent = cx.new(|cx| TextareaState::new(window, cx).placeholder("Énfasis"));
        let review_note =
            cx.new(|cx| InputState::new(window, cx).placeholder("Motivo de la edición manual"));
        let template_filter =
            cx.new(|cx| InputState::new(window, cx).placeholder("Buscar plantilla"));
        let fetch_url = cx.new(|cx| InputState::new(window, cx).placeholder("Enlace HTTP o HTTPS"));
        let fetch_directory = cx.new(|cx| {
            InputState::new(window, cx).placeholder("Carpeta predeterminada de Luna Fetch")
        });
        let voice_text = cx.new(|cx| {
            TextareaState::new(window, cx)
                .placeholder("Escribe el texto que quieres convertir en voz")
        });
        let ai_script = cx.new(|cx| {
            TextareaState::new(window, cx).placeholder(
                "Pega aquí el guion para alinear omisiones, ortografía y nombres propios…",
            )
        });

        let mut subscriptions = vec![
            cx.subscribe(&find, |this, _, event, cx| {
                if matches!(event, InputEvent::Change) {
                    this.refilter(cx);
                }
            }),
            cx.subscribe(&library_filter, |this, _, event, cx| {
                if matches!(event, InputEvent::Change) {
                    this.filter_library(cx);
                }
            }),
            cx.subscribe(&edit, |this, state, event: &InputEvent, cx| {
                if matches!(event, InputEvent::Change) {
                    this.session.set_draft(state.read(cx).value().to_string());
                }
                cx.notify();
            }),
        ];
        for input in [&review_context, &review_main, &review_accent] {
            subscriptions.push(cx.subscribe(input, |_, _, _: &InputEvent, cx| cx.notify()));
        }
        subscriptions.push(cx.subscribe(&review_note, |_, _, _: &InputEvent, cx| cx.notify()));
        subscriptions.push(cx.subscribe(&template_filter, |_, _, _: &InputEvent, cx| cx.notify()));
        subscriptions.push(cx.subscribe(&voice_text, |this, _, _: &InputEvent, cx| {
            this.voice_quote = None;
            cx.notify();
        }));
        subscriptions.push(cx.subscribe(&fetch_url, |this, _, _: &InputEvent, cx| {
            this.fetch_info = None;
            cx.notify();
        }));

        let weak = cx.entity().downgrade();
        window.on_window_should_close(cx, move |window, cx| {
            weak.update(cx, |this, cx| this.request_close(window, cx))
                .unwrap_or(true)
        });

        let loaded_preferences = Preferences::load_checked();
        let preference_error = loaded_preferences.as_ref().err().cloned();
        let mut app = Self {
            tab: Tab::Editor,
            pending_tab:None,
            session: SubtitleSession::default(),
            filtered_cues: vec![],
            find,
            replacement,
            glossary,
            edit,
            case_sensitive: false,
            preferences: loaded_preferences.unwrap_or_default(),
            library_category: library::CATEGORIES[0].0.to_owned(),
            library_inventory: library::Inventory::default(),
            library_filter,
            library_filtered: vec![],
            library_scan_pending:false,
            editor_track,
            editor_fps,
            editor_first,
            editor_last,
            editor_stage: 1,
            editor_options:editorial::Options::default(),editor_direction,
            capture_snapshot:None,proposal:None,proposal_dirty:false,review_selected:0,
            proposal_input:vec![],
            review_context,review_main,review_accent,review_note,review_enabled:true,
            review_templates:BTreeMap::new(),last_application:None,
            review_template_layer:None,template_filter,
            fetch_url,fetch_directory,fetch_audio:false,fetch_import:false,fetch_info:None,fetch_result:None,
            voice_text,voice_catalog:media::VoiceCatalog::default(),voice_selected:None,voice_quote:None,voice_output:None,
            media_preview:None,media_source:None,
            ai_panel_open:false,ai_script,ai_detect_markers:true,ai_markers:Vec::new(),ai_snapshot:None,
            about_open: false,
            busy: false,
            message: "Listo para abrir tu montaje.".into(),
            error: false,
            resolve: None,
            assistant_messages: vec![AssistantMessage {
                sender: "Asistente",
                content: "Podemos trabajar la dirección narrativa, los B-rolls y los efectos de tu montaje. Comparte tu idea para empezar.".into(),
                is_ai: true,
            }],
            assistant_prompt,
            settings: None,
            settings_provider: "gemini".into(),
            settings_model: String::new(),
            settings_model_input,
            settings_key,
            settings_models: vec![],
            settings_status: String::new(),
            release: None,
            release_checked: false,
            sfx_assets: vec![],
            templates: vec![],
            catalog_diagnostics: vec![],
            _subscriptions: subscriptions,
            close_prompt: false,
        };
        app.set_default_values(window, cx);
        if let Some(error) = preference_error {
            app.notify(Err(error), cx);
        }
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

    fn set_default_values(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let values = [
            (self.editor_track.clone(), "1"),
            (self.editor_fps.clone(), "24"),
            (self.editor_first.clone(), "1"),
            (self.editor_last.clone(), "120"),
        ];
        for (state, value) in values {
            state.update(cx, |state, cx| state.set_value(value, window, cx));
        }
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
        if !self.session.is_dirty()
            && !self.session.has_draft()
            && !self.proposal_dirty
            && !self.review_has_draft(cx)
        {
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

    pub fn notify(&mut self, result: Result<String, String>, cx: &mut Context<Self>) {
        self.error = result.is_err();
        self.message = match result {
            Ok(s) | Err(s) => s,
        };
        cx.notify();
    }

    fn refilter(&mut self, cx: &mut Context<Self>) {
        let query = self.find.read(cx).value().to_lowercase();
        self.filtered_cues = self.session.filtered_indices(&query);
        cx.notify();
    }

    fn filter_library(&mut self, cx: &mut Context<Self>) {
        let query = self.library_filter.read(cx).value().to_lowercase();
        self.library_filtered = self
            .library_inventory
            .resources
            .iter()
            .enumerate()
            .filter(|(_, resource)| {
                query.is_empty() || resource.name.to_lowercase().contains(&query)
            })
            .map(|(index, _)| index)
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
        self.proposal = None;
        self.proposal_input.clear();
        self.proposal_dirty = false;
        self.capture_snapshot = None;
        self.ai_snapshot = None;
        self.ai_markers.clear();
        self.editor_stage = 1;
        self.find.update(cx, |s, cx| s.set_value("", window, cx));
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
                if let Some(tab) = this.pending_tab.take() {
                    this.load_for_tab(tab, window, cx);
                }
                if this.library_scan_pending && !this.busy {
                    this.library_scan_pending = false;
                    this.scan_library(window, cx);
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
        if self.session.is_dirty()
            || self.session.has_draft()
            || self.proposal_dirty
            || self.review_has_draft(cx)
        {
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

    /// Lee los subtítulos de Resolve con los valores de pista y rango del Editor.
    fn capture(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if self.session.is_dirty()
            || self.session.has_draft()
            || self.proposal_dirty
            || self.review_has_draft(cx)
        {
            self.notify(
                Err("Guarda o descarta la edición pendiente y exporta o deshaz los cambios antes de capturar otra fuente.".into()),
                cx,
            );
            return;
        }
        let track = self.number(&self.editor_track, cx, 1);
        let first = self.number(&self.editor_first, cx, 1);
        let last = self.number(&self.editor_last, cx, 120);
        let (track, first, last) = match (track, first, last) {
            (Some(track), Some(first), Some(last)) => (track, first, last),
            _ => {
                self.notify(Err("Pista, Desde y Hasta deben ser números.".into()), cx);
                return;
            }
        };
        self.work(
            "Leyendo subtítulos de Resolve…",
            window,
            cx,
            move || bridge::capture(track, first, last),
            |this, (doc, snapshot), window, cx| {
                this.install_document(doc, window, cx);
                this.capture_snapshot = Some(snapshot);
            },
        );
    }

    /// Lee un valor entero de un campo; `None` cuando no es un número válido.
    fn number(&self, field: &Entity<InputState>, cx: &Context<Self>, fallback: u32) -> Option<u32> {
        let raw = field.read(cx).value().trim().to_owned();
        if raw.is_empty() {
            return Some(fallback);
        }
        let value = raw.parse::<u32>().ok()?;
        if value == 0 { None } else { Some(value) }
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

    // --- Corrección de subtítulos ---

    fn normalize(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let result = self.session.normalize();
        self.after_batch(result, window, cx);
    }

    fn replace(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let find = self.find.read(cx).value().to_string();
        let replacement = self.replacement.read(cx).value().to_string();
        let result = self
            .session
            .replace(&find, &replacement, self.case_sensitive);
        self.after_batch(result, window, cx);
    }

    fn apply_glossary(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let glossary = self.glossary.read(cx).value().to_string();
        let result = self.session.apply_glossary(&glossary);
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

    fn restore_cue(&mut self, index: usize, window: &mut Window, cx: &mut Context<Self>) {
        let result = self.session.restore_cue(index);
        if result.is_ok() {
            self.sync_editor(window, cx);
            self.refilter(cx);
        }
        self.notify(
            result.map(|_| "Subtítulo restaurado a su texto original.".into()),
            cx,
        );
    }

    fn next_cue(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let Some(current) = self.session.selected() else {
            return;
        };
        let next = current + 1;
        if next >= self.session.document().cues.len() {
            self.notify(Ok("No hay más subtítulos en esta fuente.".into()), cx);
            return;
        }
        self.select_cue(next, window, cx);
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

    /// Propaga los subtítulos corregidos al Editor; ambas vistas comparten la sesión.
    fn sync_to_editor(&mut self, cx: &mut Context<Self>) {
        if self.session.document().cues.is_empty() {
            self.notify(Err("No hay subtítulos para sincronizar.".into()), cx);
            return;
        }
        self.tab = Tab::Editor;
        self.notify(
            Ok("Subtítulos corregidos cargados en el Editor.".into()),
            cx,
        );
    }

    /// Carga lo que cada módulo necesita la primera vez que se abre.
    pub fn load_for_tab(&mut self, tab: Tab, window: &mut Window, cx: &mut Context<Self>) {
        self.tab = tab;
        if self.busy {
            self.pending_tab = Some(tab);
            cx.notify();
            return;
        }
        match tab {
            Tab::Settings => {
                if self.settings.is_none() {
                    self.load_settings(window, cx);
                }
            }
            Tab::Sfx => {
                if self.sfx_assets.is_empty() {
                    self.load_sfx_catalog(window, cx);
                }
            }
            Tab::Catalog => {
                if self.templates.is_empty() {
                    self.load_templates(window, cx);
                }
            }
            Tab::Brolls => self.prepare_category("visuals", window, cx),
            Tab::Music => self.prepare_category("music", window, cx),
            Tab::Voice if self.voice_catalog.voices.is_empty() => self.refresh_voices(window, cx),
            _ => {}
        }
        cx.notify();
    }

    fn prepare_category(&mut self, category: &str, window: &mut Window, cx: &mut Context<Self>) {
        if self.library_category != category || self.library_inventory.category != category {
            self.library_category = category.to_owned();
            if self.library_inventory.category != category {
                self.library_inventory = library::scan_category(category, &[], 2000);
                self.library_filtered.clear();
            }
            self.library_filter
                .update(cx, |state, cx| state.set_value("", window, cx));
            self.scan_library(window, cx);
        }
    }

    // --- Ajustes ---
}
