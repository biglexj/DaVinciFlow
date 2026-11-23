//! Acciones explícitas de medios, voz de Aurora y Luna Fetch.
use super::*;

impl FlowApp {
    pub(super) fn voice_logout(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.work(
            "Cerrando el acceso de Aurora…",
            window,
            cx,
            media::logout,
            |this, _, _, cx| {
                this.voice_waiting_login = false;
                this.voice_catalog = media::VoiceCatalog::default();
                this.voice_selected = None;
                this.voice_quote = None;
                this.notify(Ok("Sesión de Aurora cerrada en este checkout.".into()), cx);
            },
        );
    }

    pub(super) fn fetch_analyze(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let url = self.fetch_url.read(cx).value().trim().to_owned();
        if url.is_empty() {
            self.notify(Err("Ingresa un enlace antes de analizar.".into()), cx);
            return;
        }
        self.work(
            "Analizando metadatos del enlace…",
            window,
            cx,
            move || media::analyze(&url),
            |this, info, _, cx| {
                if info.is_audio {
                    this.fetch_audio = true;
                }
                this.fetch_info = Some(info);
                this.notify(Ok("Análisis completado. Listo para descargar.".into()), cx);
            },
        );
    }

    pub(super) fn fetch_download(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let url = self.fetch_url.read(cx).value().trim().to_owned();
        if url.is_empty() {
            self.notify(Err("Ingresa un enlace para descargar.".into()), cx);
            return;
        }
        let directory = self.fetch_directory.read(cx).value().trim().to_owned();
        let kind = if self.fetch_audio { "audio" } else { "video" };
        let import = self.fetch_import;
        self.work(
            "Descargando y procesando el medio…",
            window,
            cx,
            move || media::download(&url, kind, &directory, import),
            |this, result, _, cx| {
                let import_label = if result.imported {
                    if result.resolve_bin.is_empty() {
                        "Importado a Resolve.".to_string()
                    } else {
                        format!("Importado en {}.", result.resolve_bin)
                    }
                } else {
                    "Guardado en disco.".to_string()
                };
                let message = format!(
                    "Guardado: {} · {} {}",
                    result.path.display(),
                    import_label,
                    result.message
                );
                this.fetch_history.insert(0, result.clone());
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

    pub(super) fn sync_voice_selection(&mut self) {
        let available_engines: Vec<String> = self
            .voice_catalog
            .engines
            .iter()
            .filter(|e| {
                e.available
                    && self
                        .voice_catalog
                        .voices
                        .iter()
                        .any(|v| v.ready && v.provider == e.id)
            })
            .map(|e| e.id.clone())
            .collect();
        if !available_engines.contains(&self.voice_engine)
            && let Some(first_eng) = available_engines.first()
        {
            self.voice_engine = first_eng.clone();
        }
        let valid_current = self
            .voice_selected
            .and_then(|i| self.voice_catalog.voices.get(i))
            .is_some_and(|v| v.ready && v.provider == self.voice_engine);
        if !valid_current {
            self.voice_selected = self
                .voice_catalog
                .voices
                .iter()
                .position(|v| {
                    v.ready
                        && v.provider == self.voice_engine
                        && v.name.to_lowercase().contains("predeterminada")
                })
                .or_else(|| {
                    self.voice_catalog
                        .voices
                        .iter()
                        .position(|v| v.ready && v.provider == self.voice_engine)
                });
        }
    }

    pub(super) fn refresh_voices(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.work(
            "Consultando las voces disponibles…",
            window,
            cx,
            media::voices,
            |this, catalog, _, cx| {
                this.voice_quote = None;
                this.voice_catalog = catalog;
                this.sync_voice_selection();
                if this.voice_catalog.voices.is_empty() && !this.voice_catalog.warnings.is_empty() {
                    this.notify(Err(this.voice_catalog.warnings.join(" ")), cx);
                } else {
                    this.notify(
                        Ok("Voces consultadas. Selecciona un motor y voz para continuar.".into()),
                        cx,
                    );
                }
            },
        );
    }

    pub(super) fn voice_login_provider(
        &mut self,
        provider: &'static str,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        self.work(
            "Preparando el acceso a Aurora…",
            window,
            cx,
            move || media::login_with(provider),
            |this, url, window, cx| {
                this.voice_waiting_login = true;
                cx.open_url(&url);
                this.notify(
                    Ok("Completa el inicio de sesión en el navegador. Se detectará automáticamente al volver.".into()),
                    cx,
                );
                this.poll_voice_callback(window, cx);
            },
        );
    }

    pub(super) fn voice_cancel_login(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.voice_waiting_login = false;
        self.work(
            "Cancelando espera de inicio de sesión…",
            window,
            cx,
            media::cancel_login,
            |this, _, _, cx| {
                this.notify(Ok("Inicio de sesión cancelado.".into()), cx);
            },
        );
    }

    pub(super) fn poll_voice_callback(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        cx.spawn_in(window, async move |this, cx| {
            for _ in 0..120 {
                std::thread::sleep(std::time::Duration::from_millis(800));
                let still_waiting = this
                    .update_in(cx, |this, _, _| this.voice_waiting_login && !this.busy)
                    .unwrap_or(false);
                if !still_waiting {
                    break;
                }
                if media::callback_ready().unwrap_or(false) {
                    let _ = this.update_in(cx, |this, window, cx| {
                        this.voice_waiting_login = false;
                        this.voice_complete(window, cx);
                    });
                    break;
                }
            }
        })
        .detach();
    }

    pub(super) fn voice_complete(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.voice_waiting_login = false;
        self.work(
            "Completando el acceso…",
            window,
            cx,
            || {
                media::complete_login()?;
                media::voices()
            },
            |this, catalog, _, cx| {
                this.voice_quote = None;
                this.voice_catalog = catalog;
                this.sync_voice_selection();
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
        let text = self.voice_text.read(cx).value().trim().to_owned();
        if text.is_empty() || text.chars().count() > 10_000 {
            self.notify(Err("Escribe entre 1 y 10.000 caracteres.".into()), cx);
            return;
        }
        if voice.provider == "system" {
            self.voice_quote = None;
            self.work(
                "Generando voz en este equipo…",
                window,
                cx,
                move || media::generate(&text, &voice, 0),
                |this, path, _, cx| {
                    this.voice_output = Some(path.clone());
                    this.notify(Ok(format!("Audio generado: {}", path.display())), cx);
                },
            );
            return;
        }
        let Some((quoted_text, id, cost)) = self.voice_quote.clone() else {
            return;
        };
        if quoted_text != text || id != voice.id {
            self.voice_quote = None;
            cx.notify();
            return;
        }
        self.voice_quote = None;
        self.work(
            "Generando la voz en Aurora. Espera la confirmación del servicio…",
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

    pub(super) fn pick_voice_file(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let receiver = cx.prompt_for_paths(PathPromptOptions {
            files: true,
            directories: false,
            multiple: false,
            prompt: Some("Seleccionar audio de Voice Studio".into()),
        });
        cx.spawn_in(window, async move |this, cx| {
            if let Ok(Ok(Some(paths))) = receiver.await
                && let Some(path) = paths.into_iter().next()
            {
                let _ = this.update_in(cx, |this, window, cx| {
                    this.work(
                        "Validando archivo de audio…",
                        window,
                        cx,
                        move || media::validate_voice(&path),
                        |this, validated, _, cx| {
                            this.voice_output = Some(validated.clone());
                            this.notify(
                                Ok(format!("Audio seleccionado: {}", validated.display())),
                                cx,
                            );
                        },
                    );
                });
            }
        })
        .detach();
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

    pub(super) fn import_voice_file(
        &mut self,
        path: PathBuf,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        self.work(
            "Importando audio a «DaVinci Flow · Voces»…",
            window,
            cx,
            move || media::import_voice(&path),
            |this, value, _, cx| {
                let detail = value["detail"]
                    .as_str()
                    .unwrap_or("Audio importado al Media Pool.");
                this.notify(Ok(detail.to_string()), cx);
            },
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

    pub(super) fn toggle_sound_file(
        &mut self,
        path: PathBuf,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        let title = path
            .file_stem()
            .or_else(|| path.file_name())
            .unwrap_or_default()
            .to_string_lossy()
            .into_owned();
        let is_video = davinci_flow_gpui::video_player::is_video_path(&path);
        let kind = match self.tab {
            Tab::Brolls if is_video => "Vídeo",
            Tab::Music => "Música",
            Tab::Sfx => "SFX",
            Tab::Voice => "Voz",
            Tab::Fetch if is_video => "Luna Fetch · Vídeo",
            Tab::Fetch => "Luna Fetch",
            _ if is_video => "Vídeo",
            _ => "Audio",
        };
        let track = davinci_flow_gpui::audio_player::AudioTrack {
            path,
            title,
            kind: kind.into(),
            is_video,
        };
        let origin = self.tab;
        let open_modal = is_video && origin != Tab::Brolls;
        self.play_media_with_queue(
            origin,
            track.clone(),
            vec![track],
            Some(0),
            open_modal,
            window,
            cx,
        );
    }

    pub(super) fn stop_audio(&mut self, cx: &mut Context<Self>) {
        self.stop_audio_with_window(None, cx);
    }

    pub(super) fn stop_audio_with_window(
        &mut self,
        window: Option<&mut Window>,
        cx: &mut Context<Self>,
    ) {
        self.audio_player.stop(false);
        self.video_streamer.stop();
        self.video_modal_open = false;
        self.player_origin = None;
        self.player_pump_active = false;
        if let Some(win) = window {
            self.clear_video_frame(win);
        } else {
            self.video_frame = None;
        }
        self.sync_player_snapshot(None, cx);
        self.notify(Ok("Reproducción detenida.".into()), cx);
    }

    pub(super) fn play_sfx(&mut self, id: String, window: &mut Window, cx: &mut Context<Self>) {
        self.work(
            "Preparando el efecto de sonido…",
            window,
            cx,
            move || media::sfx(&id),
            |this, path, window, cx| {
                this.toggle_sound_file(path, window, cx);
            },
        );
    }
}
