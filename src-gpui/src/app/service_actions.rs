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
    pub(super) fn load_settings(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.work(
            "Consultando los ajustes…",
            window,
            cx,
            services::settings,
            |this, settings, window, cx| {
                this.settings_provider = settings.provider.clone();
                this.settings_model = settings.model.clone();
                this.settings_models = settings.models.clone();
                this.settings_status = if settings.has_key {
                    "Clave configurada.".into()
                } else {
                    "Falta la clave API del proveedor.".into()
                };
                this.settings_model_input.update(cx, |state, cx| {
                    state.set_value(settings.model.clone(), window, cx)
                });
                // La credencial nunca se lee de memoria: se muestra enmascarada.
                if settings.has_key {
                    this.settings_key
                        .update(cx, |state, cx| state.set_value(MASKED_KEY, window, cx));
                }
                this.settings = Some(settings);
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

    pub(super) fn check_release(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.work(
            "Consultando GitHub Releases…",
            window,
            cx,
            services::release,
            |this, release, _, cx| {
                this.release_checked = true;
                match release {
                    Some(release) => {
                        let message = if release.is_newer {
                            format!("🚀 Nueva versión v{} disponible.", release.version)
                        } else {
                            "Estás en la última versión.".into()
                        };
                        this.release = Some(release);
                        this.notify(Ok(message), cx);
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
            services::templates,
            |this, (templates, diagnostics), _, cx| {
                let count = templates.len();
                this.templates = templates;
                this.catalog_diagnostics = diagnostics;
                this.notify(Ok(format!("{count} plantillas disponibles.")), cx);
            },
        );
    }
}
