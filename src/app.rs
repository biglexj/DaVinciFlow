//! Estado y ciclo de vida de la ventana nativa; la presentación vive en `app::*`.
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
pub mod player_bar;
pub mod review_view;
pub mod service_actions;
pub mod settings_view;
pub mod shell;
pub mod subtitles_actions;
pub mod subtitles_view;
pub mod updates;
pub mod video_modal;
pub mod views;
pub mod voice_view;

use crate::{
    bridge, library,
    preferences::Preferences,
    subtitles::{self, Document},
    ui::*,
};
use davinci_flow_gpui::audio_player::{AudioPlayer, PlayerSnapshot};
use davinci_flow_gpui::editorial;
use davinci_flow_gpui::media;
use davinci_flow_gpui::services;
use davinci_flow_gpui::session::SubtitleSession;
use davinci_flow_gpui::video_player::VideoStreamer;
use gpui_kit::assets::IconName;
use gpui_kit::component::input::{Input, InputEvent, InputState, Textarea, TextareaState};
use gpui_kit::{prelude::*, *};
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};
use std::path::PathBuf;
use std::sync::Arc;

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
        true
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
    pub media_offset: usize,
    pub editor_track: Entity<InputState>,
    pub editor_fps: Entity<InputState>,
    pub editor_first: Entity<InputState>,
    pub editor_last: Entity<InputState>,
    pub editor_stage: u8,
    pub editor_options: editorial::Options,
    pub editor_batch_size: String,
    pub editor_direction: Entity<InputState>,
    pub capture_snapshot: Option<Value>,
    pub proposal: Option<editorial::Proposal>,
    pub proposal_input: Vec<(u64, u64, String)>,
    pub proposal_dirty: bool,
    pub batch_processed: usize,
    pub batch_total: usize,
    pub batch_next: Option<usize>,
    pub conflicts: Vec<editorial::Conflict>,
    pub review_selected: usize,
    pub review_context: Entity<TextareaState>,
    pub review_main: Entity<TextareaState>,
    pub review_accent: Entity<TextareaState>,
    pub review_note: Entity<InputState>,
    pub review_enabled: bool,
    pub review_sfx: String,
    pub review_sfx_open: bool,
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
    pub fetch_history: Vec<media::Download>,
    pub voice_text: Entity<TextareaState>,
    pub voice_catalog: media::VoiceCatalog,
    pub voice_engine: String,
    pub voice_selected: Option<usize>,
    pub voice_quote: Option<(String, String, u64)>,
    pub voice_output: Option<PathBuf>,
    pub voice_waiting_login: bool,
    pub media_preview: Option<PathBuf>,
    pub media_source: Option<PathBuf>,
    pub playing_sound: Option<PathBuf>,
    pub audio_player: AudioPlayer,
    pub player_state: PlayerSnapshot,
    pub player_pump_active: bool,
    pub player_origin: Option<Tab>,
    pub video_streamer: VideoStreamer,
    pub video_frame: Option<Arc<RenderImage>>,
    pub video_synced_epoch: u64,
    pub video_modal_open: bool,
    // Panel de IA y guion de la pestaña «Corrección».
    pub ai_panel_open: bool,
    pub ai_script: Entity<TextareaState>,
    pub ai_detect_markers: bool,
    pub ai_markers: Vec<services::Marker>,
    pub ai_snapshot: Option<Value>,
    pub about_open: bool,
    pub about_licenses_open: bool,
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
    pub toast_message: Option<String>,
    // Catálogos (SFX y Plantillas)
    pub sfx_assets: Vec<services::SfxAsset>,
    pub user_sfx_resources: Vec<library::Resource>,
    pub user_broll_resources: Vec<library::Resource>,
    pub sfx_query: Entity<InputState>,
    pub sfx_category: String,
    pub sfx_track_name: Entity<InputState>,
    pub sfx_anticipation: Entity<InputState>,
    pub sfx_offset: usize,
    pub templates: Vec<services::TemplateInfo>,
    pub catalog_diagnostics: Vec<String>,
    pub catalog_query: Entity<InputState>,
    pub catalog_source: String,
    pub catalog_offset: usize,
    pub catalog_selected: BTreeSet<String>,
    pub catalog_presets: Vec<String>,
    pub catalog_preset_name: Entity<InputState>,
    pub catalog_node_name: Entity<InputState>,
    pub catalog_node_input: Entity<InputState>,
    pub catalog_preview: Option<(String, services::TemplatePreview)>,
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
            InputState::new(window, cx).placeholder(
                "Dirección creativa (ej.: pocas palabras grandes; alternar con planos sin texto)",
            )
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
            cx.new(|cx| InputState::new(window, cx).placeholder("Nota si reescribes el original"));
        let template_filter =
            cx.new(|cx| InputState::new(window, cx).placeholder("Buscar plantilla"));
        let fetch_url = cx.new(|cx| {
            InputState::new(window, cx)
                .placeholder("https://www.youtube.com/watch?v=… o Suno, TikTok, SoundCloud")
        });
        let fetch_directory = cx.new(|cx| {
            InputState::new(window, cx).placeholder("Carpeta predeterminada de Luna Fetch")
        });
        let voice_text = cx.new(|cx| {
            TextareaState::new(window, cx)
                .placeholder("Escribe el texto tal como quieres escucharlo.")
        });
        let ai_script = cx.new(|cx| {
            TextareaState::new(window, cx).placeholder(
                "Pega aquí el guion para alinear omisiones, ortografía y nombres propios…",
            )
        });
        let sfx_query = cx.new(|cx| {
            InputState::new(window, cx).placeholder("Buscar sonido por nombre o palabra clave…")
        });
        let sfx_track_name = cx.new(|cx| InputState::new(window, cx).placeholder("DF_SFX"));
        let sfx_anticipation = cx.new(|cx| InputState::new(window, cx).placeholder("-3"));
        let catalog_query = cx
            .new(|cx| InputState::new(window, cx).placeholder("Buscar títulos por nombre o ruta"));
        let catalog_preset_name =
            cx.new(|cx| InputState::new(window, cx).placeholder("Ej.: Narrativa horizontal"));
        let catalog_node_name =
            cx.new(|cx| InputState::new(window, cx).placeholder("Vacío: detectar un único Text+"));
        let catalog_node_input = cx.new(|cx| InputState::new(window, cx).placeholder("StyledText"));

        let mut subscriptions = vec![
            cx.subscribe(&find, |this, _, event, cx| {
                if matches!(event, InputEvent::Change) {
                    this.refilter(cx);
                }
            }),
            cx.subscribe(&library_filter, |this, _, event, cx| {
                if matches!(event, InputEvent::Change) {
                    this.media_offset = 0;
                    this.filter_library(cx);
                }
            }),
            cx.subscribe(&edit, |this, state, event: &InputEvent, cx| {
                if matches!(event, InputEvent::Change) {
                    this.session.set_draft(state.read(cx).value().to_string());
                }
                cx.notify();
            }),
            cx.subscribe(&sfx_query, |this, _, event, cx| {
                if matches!(event, InputEvent::Change) {
                    this.sfx_offset = 0;
                    cx.notify();
                }
            }),
            cx.subscribe(&catalog_query, |this, _, event, cx| {
                if matches!(event, InputEvent::Change) {
                    this.catalog_offset = 0;
                    cx.notify();
                }
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
            pending_tab: None,
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
            library_scan_pending: false,
            media_offset: 0,
            editor_track,
            editor_fps,
            editor_first,
            editor_last,
            editor_stage: 1,
            editor_options: editorial::Options::default(),
            editor_batch_size: "20".into(),
            editor_direction,
            capture_snapshot: None,
            proposal: None,
            proposal_dirty: false,
            batch_processed: 0,
            batch_total: 0,
            batch_next: None,
            conflicts: vec![],
            review_selected: 0,
            proposal_input: vec![],
            review_context,
            review_main,
            review_accent,
            review_note,
            review_enabled: true,
            review_sfx: String::new(),
            review_sfx_open: false,
            review_templates: BTreeMap::new(),
            last_application: None,
            review_template_layer: None,
            template_filter,
            fetch_url,
            fetch_directory,
            fetch_audio: false,
            fetch_import: true,
            fetch_info: None,
            fetch_result: None,
            fetch_history: vec![],
            voice_text,
            voice_catalog: media::VoiceCatalog::default(),
            voice_engine: "system".into(),
            voice_selected: None,
            voice_quote: None,
            voice_output: None,
            voice_waiting_login: false,
            media_preview: None,
            media_source: None,
            playing_sound: None,
            audio_player: AudioPlayer::new(),
            player_state: PlayerSnapshot::default(),
            player_pump_active: false,
            player_origin: None,
            video_streamer: VideoStreamer::new(),
            video_frame: None,
            video_synced_epoch: 0,
            video_modal_open: false,
            ai_panel_open: false,
            ai_script,
            ai_detect_markers: true,
            ai_markers: Vec::new(),
            ai_snapshot: None,
            about_open: false,
            about_licenses_open: false,
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
            toast_message: None,
            sfx_assets: vec![],
            user_sfx_resources: vec![],
            user_broll_resources: vec![],
            sfx_query,
            sfx_category: "all".into(),
            sfx_track_name,
            sfx_anticipation,
            sfx_offset: 0,
            templates: vec![],
            catalog_diagnostics: vec![],
            catalog_query,
            catalog_source: "all".into(),
            catalog_offset: 0,
            catalog_selected: BTreeSet::new(),
            catalog_presets: vec![],
            catalog_preset_name,
            catalog_node_name,
            catalog_node_input,
            catalog_preview: None,
            _subscriptions: subscriptions,
            close_prompt: false,
        };
        let escape_sub = cx.observe_keystrokes(|this, event, window, cx| {
            if event.keystroke.key == "escape" {
                this.handle_escape(window, cx);
            }
        });
        app._subscriptions.push(escape_sub);
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
        } else {
            app.startup_preload(window, cx);
        }
        app
    }

    fn set_default_values(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let values = [
            (self.editor_track.clone(), "1"),
            (self.editor_fps.clone(), "24"),
            (self.editor_first.clone(), "1"),
            (self.editor_last.clone(), "120"),
            (self.sfx_track_name.clone(), "DF_SFX"),
            (self.sfx_anticipation.clone(), "-3"),
            (self.catalog_node_input.clone(), "StyledText"),
        ];
        for (state, value) in values {
            state.update(cx, |state, cx| state.set_value(value, window, cx));
        }
    }

    /// Cierra diálogos, visores o paneles temporales al pulsar la tecla Escape.
    pub fn handle_escape(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if self.video_modal_open {
            self.video_modal_open = false;
            if self.player_origin != Some(Tab::Brolls) {
                self.stop_audio_with_window(Some(window), cx);
            }
            cx.notify();
            return;
        }
        if self.catalog_preview.is_some() {
            self.catalog_preview = None;
            cx.notify();
            return;
        }
        if self.about_open {
            self.about_open = false;
            self.about_licenses_open = false;
            cx.notify();
            return;
        }
        if self.review_sfx_open || self.review_template_layer.is_some() {
            self.review_sfx_open = false;
            self.review_template_layer = None;
            cx.notify();
        }
    }

    /// Actualiza y persiste la preferencia de apariencia (Aurora/Clásico y Oscuro/Claro).
    pub fn set_appearance_preference(
        &mut self,
        theme: &str,
        mode: &str,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        self.preferences.appearance_theme = theme.to_string();
        self.preferences.appearance_mode = mode.to_string();
        crate::ui::apply_gpui_theme(theme, mode, Some(window), cx);
        let prefs = self.preferences.clone();
        cx.background_executor()
            .spawn(async move {
                let _ = prefs.save();
            })
            .detach();
        cx.notify();
    }

    /// Carga inicial silenciosa de ajustes, sesión de Aurora y estado de Resolve sin bloquear la apertura.
    fn startup_preload(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let task = cx
            .background_executor()
            .spawn(async move { (services::settings(), bridge::status(), media::voices()) });
        cx.spawn_in(window, async move |this, cx| {
            let (settings_res, resolve_res, voices_res) = task.await;
            let _ = this.update_in(cx, |this, window, cx| {
                if let Ok(settings) = settings_res {
                    this.apply_loaded_settings(settings, window, cx);
                }
                if let Ok(status) = resolve_res {
                    this.resolve = Some(status);
                }
                if let Ok(catalog) = voices_res {
                    this.voice_catalog = catalog;
                    this.sync_voice_selection();
                }
                cx.notify();
            });
        })
        .detach();
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
            "Hay cambios sin guardar",
            Some(
                "Tienes subtítulos o revisiones editoriales pendientes de exportar o guardar en archivo. ¿Deseas cerrar de todos modos?",
            ),
            &[
                PromptButton::Cancel("Volver".into()),
                PromptButton::Ok("Cerrar sin guardar".into()),
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

    // Un solo trabajo por ventana; el executor mantiene I/O y Python fuera del render.
    pub(super) fn work<T: Send + 'static>(
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
                if self.voice_catalog.voices.is_empty() {
                    self.refresh_voices(window, cx);
                }
            }
            Tab::Sfx => {
                self.prepare_category("sfx", window, cx);
                if self.sfx_assets.is_empty() && !self.busy {
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

    pub(super) fn prepare_category(
        &mut self,
        category: &str,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        if self.library_category != category || self.library_inventory.category != category {
            self.library_category = category.to_owned();
            self.media_offset = 0;
            if self.library_inventory.category != category {
                self.library_inventory = library::scan_category(category, &[], 2000);
                self.library_filtered.clear();
            }
            self.library_filter
                .update(cx, |state, cx| state.set_value("", window, cx));
            self.scan_library(window, cx);
        }
    }
}
