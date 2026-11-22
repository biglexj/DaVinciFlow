use super::*;

/// La credencial se muestra enmascarada; nunca se vuelve a leer de memoria.
pub(super) const MASKED_KEY: &str = "••••••••••••••••";

impl FlowApp {
    pub(super) fn switch_provider(
        &mut self,
        provider: &str,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        if self.busy || self.settings_provider == provider {
            return;
        }
        let key = self.settings_key.read(cx).value();
        if !key.is_empty() && key.chars().any(|c| c != '•') {
            self.notify(
                Err("Guarda la clave pendiente antes de cambiar de proveedor.".into()),
                cx,
            );
            return;
        }
        let provider = provider.to_owned();
        self.work(
            "Consultando el proveedor…",
            window,
            cx,
            move || services::settings_for(&provider),
            |this, settings, window, cx| {
                this.settings_provider = settings.provider.clone();
                this.settings_model = settings.model.clone();
                this.settings_models = settings.models.clone();
                this.settings_model_input.update(cx, |state, cx| {
                    state.set_value(settings.model.clone(), window, cx)
                });
                this.settings_key
                    .update(cx, |state, cx| state.set_value("", window, cx));
                this.settings_status = if settings.has_key {
                    "Clave configurada para este proveedor."
                } else {
                    "Falta la clave API de este proveedor."
                }
                .into();
                this.settings = Some(settings);
                cx.notify();
            },
        );
    }
    pub(super) fn apply_loaded_settings(
        &mut self,
        settings: services::Settings,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        self.settings_provider = settings.provider.clone();
        self.settings_model = settings.model.clone();
        self.settings_models = settings.models.clone();
        self.settings_status = if settings.has_key {
            "Clave configurada.".into()
        } else {
            "Falta la clave API del proveedor.".into()
        };
        if !settings.preferences.mode.is_empty() {
            self.editor_options.mode = settings.preferences.mode.clone();
        }
        if !settings.preferences.format.is_empty() {
            self.editor_options.format = settings.preferences.format.clone();
        }
        if !settings.preferences.density.is_empty() {
            self.editor_options.density = settings.preferences.density.clone();
        }
        if !settings.preferences.track_mode.is_empty() {
            self.editor_options.track_mode = settings.preferences.track_mode.clone();
        }
        if !settings.preferences.batch_size.is_empty() {
            self.editor_batch_size = settings.preferences.batch_size.clone();
        }
        let dir = settings.preferences.direction.clone();
        if self.editor_direction.read(cx).value().trim().is_empty() && !dir.is_empty() {
            self.editor_direction
                .update(cx, |state, cx| state.set_value(dir, window, cx));
        }
        self.settings_model_input.update(cx, |state, cx| {
            state.set_value(settings.model.clone(), window, cx)
        });
        if settings.has_key {
            self.settings_key
                .update(cx, |state, cx| state.set_value(MASKED_KEY, window, cx));
        }
        self.settings = Some(settings);
    }

    pub(super) fn load_settings(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.work(
            "Consultando los ajustes…",
            window,
            cx,
            services::settings,
            |this, settings, window, cx| {
                this.apply_loaded_settings(settings, window, cx);
            },
        );
    }

    pub(super) fn scan_models(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.work(
            "Escaneando modelos de Gemini…",
            window,
            cx,
            services::scan_models,
            |this, models, _, cx| {
                let count = models.len();
                this.settings_models = models;
                this.notify(Ok(format!("{count} modelos disponibles.")), cx);
            },
        );
    }

    pub(super) fn save_settings(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let provider = self.settings_provider.clone();
        let provider_for_job = provider.clone();
        let model = self.settings_model_input.read(cx).value().to_string();
        let key = self.settings_key.read(cx).value().to_string();
        if model.trim().is_empty() {
            self.notify(Err("Selecciona un modelo antes de guardar.".into()), cx);
            return;
        }
        self.work(
            "Guardando los ajustes…",
            window,
            cx,
            move || {
                let preferences = services::settings()?.preferences;
                if !key.trim().is_empty() && !key.chars().all(|character| character == '•') {
                    services::save_key(&provider_for_job, &key)?;
                }
                services::save_settings(&provider_for_job, &model, &preferences)
            },
            move |this, _, window, cx| {
                this.settings_key
                    .update(cx, |state, cx| state.set_value("", window, cx));
                this.settings_model = this.settings_model_input.read(cx).value().to_string();
                this.settings = None;
                this.notify(
                    Ok(format!("Ajustes guardados. Proveedor activo: {provider}.")),
                    cx,
                );
            },
        );
    }

    // --- Asistente IA ---

    pub(super) fn assistant_context(&self) -> String {
        let document = self.session.document();
        if document.cues.is_empty() {
            return "Sin captura directa".into();
        }
        format!(
            "Secuencia activa: {} · {} subtítulos",
            document.source,
            document.cues.len()
        )
    }

    pub(super) fn ask_assistant(
        &mut self,
        prompt: String,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        if self.busy {
            return;
        }
        let request = format!(
            "Contexto del proyecto: {}\n\nConsulta del creador: {prompt}\n\nResponde de forma concisa, práctica y cinematográfica (máximo 3 párrafos). Incluye una frase sintetizada final recomendada como «Dirección creativa».",
            self.assistant_context()
        );
        self.assistant_messages.push(AssistantMessage {
            sender: "Tú",
            content: prompt,
            is_ai: false,
        });
        self.work(
            "Consultando al Asistente IA…",
            window,
            cx,
            move || services::assistant(&request),
            |this, text, _, _cx| {
                this.assistant_messages.push(AssistantMessage {
                    sender: "Asistente",
                    content: text,
                    is_ai: true,
                });
            },
        );
    }

    /// Copia la primera frase de la respuesta del asistente a la dirección creativa.
    pub(super) fn transfer_direction(
        &mut self,
        content: &str,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        let mut direction = content
            .trim()
            .rsplit("Dirección creativa")
            .next()
            .unwrap_or_default()
            .trim_start_matches(['»', '«', ':', '*', ' '])
            .replace('"', "")
            .trim()
            .to_owned();
        if direction.chars().count() > 160 {
            direction = format!("{}…", direction.chars().take(157).collect::<String>());
        }
        if direction.is_empty() {
            self.notify(
                Err("La respuesta no contiene una dirección que transferir.".into()),
                cx,
            );
            return;
        }
        let saved = direction.clone();
        self.work(
            "Transfiriendo la dirección creativa…",
            window,
            cx,
            move || {
                let settings = services::settings()?;
                let mut preferences = settings.preferences;
                preferences.direction = saved.clone();
                services::save_settings(&settings.provider, &settings.model, &preferences)
            },
            move |this, _, window, cx| {
                this.tab = Tab::Editor;
                this.editor_direction.update(cx, |state, cx| {
                    state.set_value(direction.clone(), window, cx)
                });
                this.settings = None;
                this.notify(Ok("¡Dirección transferida al Editor!".into()), cx);
            },
        );
    }

    // --- Actualizaciones y catálogos ---

    /// Persiste en segundo plano las opciones editoriales actuales en `editorial_preferences.json`.
    pub(super) fn persist_editor_preferences(&mut self, cx: &mut Context<Self>) {
        let mode = self.editor_options.mode.clone();
        let format = self.editor_options.format.clone();
        let density = self.editor_options.density.clone();
        let track_mode = self.editor_options.track_mode.clone();
        let batch_size = self.editor_batch_size.clone();
        let direction = self.editor_direction.read(cx).value().trim().to_owned();
        self.editor_options.direction = direction.clone();
        cx.background_executor()
            .spawn(async move {
                if let Ok(settings) = services::settings() {
                    let prefs = services::EditorialPreferences {
                        mode,
                        format,
                        density,
                        direction,
                        track_mode,
                        batch_size,
                    };
                    let _ = services::save_settings(&settings.provider, &settings.model, &prefs);
                }
            })
            .detach();
    }

    pub(super) fn show_toast(
        &mut self,
        message: String,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        self.toast_message = Some(message.clone());
        cx.notify();
        cx.spawn_in(window, async move |this, cx| {
            std::thread::sleep(std::time::Duration::from_secs(4));
            let _ = this.update_in(cx, |this, _, cx| {
                if this.toast_message.as_ref() == Some(&message) {
                    this.toast_message = None;
                    cx.notify();
                }
            });
        })
        .detach();
    }

    pub(super) fn check_release(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.work(
            "Consultando GitHub Releases…",
            window,
            cx,
            services::release,
            |this, release, window, cx| {
                this.release_checked = true;
                match release {
                    Some(release) => {
                        let is_newer = release.is_newer;
                        let message = if is_newer {
                            format!("🚀 Nueva versión v{} disponible.", release.version)
                        } else {
                            "Estás en la última versión.".into()
                        };
                        this.release = Some(release);
                        this.notify(Ok(message), cx);
                        if !is_newer {
                            this.show_toast(
                                format!(
                                    "¡Estás en la última versión! (v{})",
                                    env!("CARGO_PKG_VERSION")
                                ),
                                window,
                                cx,
                            );
                        }
                    }
                    None => this.notify(
                        Err("No se pudo confirmar la última versión publicada.".into()),
                        cx,
                    ),
                }
            },
        );
    }

    pub(super) fn load_sfx_catalog(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.work(
            "Cargando el catálogo de efectos…",
            window,
            cx,
            services::sfx_catalog,
            |this, assets, _, cx| {
                let count = assets.len();
                this.sfx_assets = assets;
                this.notify(Ok(format!("{count} efectos de sonido disponibles.")), cx);
            },
        );
    }

    pub(super) fn load_templates(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.work(
            "Leyendo las plantillas instaladas…",
            window,
            cx,
            services::template_catalog,
            |this, catalog, _, cx| {
                let count = catalog.templates.len();
                this.templates = catalog.templates;
                this.catalog_diagnostics = catalog.diagnostics;
                this.catalog_presets = catalog.presets;
                if this.catalog_selected.is_empty() {
                    this.catalog_selected = catalog.selected_ids.into_iter().collect();
                }
                this.notify(Ok(format!("{count} plantillas disponibles.")), cx);
            },
        );
    }

    pub(super) fn load_project_templates(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.work(
            "Leyendo títulos del Media Pool en Resolve…",
            window,
            cx,
            services::project_templates,
            |this, project_items, _, cx| {
                let count = project_items.len();
                this.templates.retain(|t| t.source != "media_pool");
                this.templates.extend(project_items);
                this.notify(
                    Ok(format!(
                        "{count} plantillas del proyecto disponibles. Elige las que correspondan a este vídeo."
                    )),
                    cx,
                );
            },
        );
    }

    pub(super) fn apply_catalog_pack(
        &mut self,
        pack: &'static str,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        self.work(
            "Aplicando pack de plantillas…",
            window,
            cx,
            move || services::choose_pack(pack),
            move |this, (count, selected), _, cx| {
                this.catalog_selected = selected.into_iter().collect();
                this.notify(
                    Ok(format!(
                        "Pack '{pack}' aplicado ({count} plantillas elegidas)."
                    )),
                    cx,
                );
            },
        );
    }

    pub(super) fn save_catalog_preset(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let name = self.catalog_preset_name.read(cx).value().trim().to_owned();
        let ids: Vec<String> = self.catalog_selected.iter().cloned().collect();
        self.work(
            "Guardando preset de plantillas…",
            window,
            cx,
            move || services::save_preset(&name, &ids),
            |this, (count, presets), _, cx| {
                this.catalog_presets = presets;
                this.notify(
                    Ok(format!(
                        "Preset guardado con {count} plantillas. Disponible para próximas ediciones."
                    )),
                    cx,
                );
            },
        );
    }

    pub(super) fn use_catalog_preset(
        &mut self,
        name: String,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        self.work(
            "Activando preset de plantillas…",
            window,
            cx,
            move || services::use_preset(&name),
            |this, (count, selected), _, cx| {
                this.catalog_selected = selected.into_iter().collect();
                this.notify(
                    Ok(format!(
                        "{count} plantillas del preset preparadas para la próxima propuesta."
                    )),
                    cx,
                );
            },
        );
    }

    pub(super) fn assign_catalog_node(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let ids: Vec<String> = self.catalog_selected.iter().cloned().collect();
        let tool = self.catalog_node_name.read(cx).value().trim().to_owned();
        let input = self.catalog_node_input.read(cx).value().trim().to_owned();
        self.work(
            "Asignando nodo Text+ a la selección…",
            window,
            cx,
            move || services::assign_node(&ids, &tool, &input),
            |this, count, _, cx| {
                this.notify(
                    Ok(format!(
                        "Nodo Text+ asignado y guardado para {count} plantillas."
                    )),
                    cx,
                );
            },
        );
    }

    pub(super) fn preview_catalog_template(
        &mut self,
        template: services::TemplateInfo,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        let title = template.name.clone();
        self.work(
            "Leyendo vista previa de la plantilla…",
            window,
            cx,
            move || services::template_preview(&template),
            move |this, preview, _, cx| {
                this.catalog_preview = Some((title, preview));
                cx.notify();
            },
        );
    }
}
