//! Acciones explícitas de medios. No se reintentan generaciones con cobro.
use super::*;

impl FlowApp {
    pub(super) fn voice_logout(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.work(
            "Cerrando el acceso de Aurora…",
            window,
            cx,
            media::logout,
            |this, _, _, cx| {
                this.voice_catalog = media::VoiceCatalog::default();
                this.voice_selected = None;
                this.voice_quote = None;
                this.notify(Ok("Sesión de Aurora cerrada en este checkout.".into()), cx);
            },
        );
    }
    pub(super) fn fetch_analyze(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let url = self.fetch_url.read(cx).value().trim().to_owned();
        self.work(
            "Consultando el enlace…",
            window,
            cx,
            move || media::analyze(&url),
            |this, info, _, cx| {
                this.fetch_info = Some(info);
                this.notify(Ok("Enlace analizado.".into()), cx);
            },
        );
    }
    pub(super) fn fetch_download(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let url = self.fetch_url.read(cx).value().trim().to_owned();
        let directory = self.fetch_directory.read(cx).value().trim().to_owned();
        let kind = if self.fetch_audio { "audio" } else { "video" };
        let import = self.fetch_import;
        self.work(
            "Descargando y procesando el medio…",
            window,
            cx,
            move || media::download(&url, kind, &directory, import),
            |this, result, _, cx| {
                let message = format!(
                    "Guardado: {} · {} {}",
                    result.path.display(),
                    if result.imported {
                        "Importado a Resolve."
                    } else {
                        "Guardado en disco."
                    },
                    result.message
                );
                this.fetch_result = Some(result);
                this.notify(Ok(message), cx);
            },
        );
    }
    pub(super) fn choose_fetch_folder(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let receiver = cx.prompt_for_paths(PathPromptOptions {
            files: false,
            directories: true,
            multiple: false,
            prompt: Some("Carpeta de descargas".into()),
        });
        cx.spawn_in(window, async move |this, cx| {
            let selection = receiver.await;
            let _ = this.update_in(cx, |this, window, cx| match selection {
                Ok(Ok(Some(paths))) => {
                    if let Some(path) = paths.first() {
                        this.fetch_directory.update(cx, |state, cx| {
                            state.set_value(path.to_string_lossy().into_owned(), window, cx)
                        });
                    }
                }
                Ok(Ok(None)) => {}
                _ => this.notify(Err("No se pudo abrir el selector de carpetas.".into()), cx),
            });
        })
        .detach();
    }
    pub(super) fn refresh_voices(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.work(
            "Consultando las voces disponibles…",
            window,
            cx,
            media::voices,
            |this, catalog, _, cx| {
                this.voice_selected = None;
                this.voice_quote = None;
                this.voice_catalog = catalog;
                this.notify(
                    if this.voice_catalog.warnings.is_empty() {
                        Ok("Voces consultadas. Selecciona una para continuar.".into())
                    } else {
                        Err(this.voice_catalog.warnings.join(" "))
                    },
                    cx,
                );
            },
        );
    }
    pub(super) fn voice_login(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.work(
            "Preparando el acceso a Aurora…",
            window,
            cx,
            media::login,
            |this, url, _, cx| {
                cx.open_url(&url);
                this.notify(
                    Ok("Completa el acceso en el navegador y pulsa «Completar acceso».".into()),
                    cx,
                );
            },
        );
    }
    pub(super) fn voice_complete(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.work(
            "Completando el acceso…",
            window,
            cx,
            || {
                media::complete_login()?;
                media::voices()
            },
            |this, catalog, _, cx| {
                this.voice_selected = None;
                this.voice_quote = None;
                this.voice_catalog = catalog;
                this.notify(Ok("Acceso a Aurora confirmado.".into()), cx);
            },
        );
    }
    pub(super) fn quote_voice(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let Some(voice) = self
            .voice_selected
            .and_then(|index| self.voice_catalog.voices.get(index))
            .cloned()
        else {
            return;
        };
        let text = self.voice_text.read(cx).value().trim().to_owned();
        if text.is_empty() || text.chars().count() > 10_000 {
            self.notify(Err("Escribe entre 1 y 10.000 caracteres.".into()), cx);
            return;
        }
        self.work(
            "Calculando el consumo…",
            window,
            cx,
            move || Ok((media::quote(&text, &voice)?, text, voice.id)),
            |this, (cost, text, id), _, cx| {
                this.voice_quote = Some((text, id, cost));
                this.notify(Ok(format!("Consumo confirmado: {cost} créditos.")), cx);
            },
        );
    }
    pub(super) fn generate_voice(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let Some(voice) = self
            .voice_selected
            .and_then(|index| self.voice_catalog.voices.get(index))
            .cloned()
        else {
            return;
        };
        let Some((text, id, cost)) = self.voice_quote.clone() else {
            return;
        };
        if text != self.voice_text.read(cx).value().trim() || id != voice.id {
            self.voice_quote = None;
            cx.notify();
            return;
        }
        self.voice_quote = None;
        self.work(
            "Generando la voz. Espera la confirmación del servicio…",
            window,
            cx,
            move || media::generate(&text, &voice, cost),
            |this, path, _, cx| {
                this.voice_output = Some(path.clone());
                this.voice_catalog.balance = None;
                this.voice_catalog.pending = false;
                this.notify(Ok(format!("Audio generado: {}", path.display())), cx);
            },
        );
    }
    pub(super) fn recover_voice(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.work(
            "Consultando la generación pendiente…",
            window,
            cx,
            media::recover,
            |this, path, _, cx| {
                this.voice_output = Some(path);
                this.voice_catalog.pending = false;
                this.notify(Ok("Audio pendiente recuperado.".into()), cx);
            },
        );
    }
    pub(super) fn import_file(
        &mut self,
        path: PathBuf,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        self.work(
            "Importando al proyecto de Resolve…",
            window,
            cx,
            move || media::import(&path),
            |this, _, _, cx| this.notify(Ok("Archivo importado al Media Pool.".into()), cx),
        );
    }
    pub(super) fn preview_media(
        &mut self,
        path: PathBuf,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        self.media_source = Some(path.clone());
        self.media_preview = None;
        self.work(
            "Extrayendo una vista previa…",
            window,
            cx,
            move || media::preview(&path),
            |this, path, _, cx| {
                this.media_preview = Some(path);
                this.notify(Ok("Vista previa lista.".into()), cx);
            },
        );
    }
    pub(super) fn play_sfx(&mut self, id: String, window: &mut Window, cx: &mut Context<Self>) {
        self.work(
            "Preparando el efecto de sonido…",
            window,
            cx,
            move || media::sfx(&id),
            |this, path, _, cx| {
                cx.open_with_system(&path);
                this.notify(
                    Ok("Efecto abierto en el reproductor del sistema.".into()),
                    cx,
                );
            },
        );
    }
}
