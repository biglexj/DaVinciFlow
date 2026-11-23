//! Pestaña «Ajustes»: cuenta de Aurora, proveedor de IA, modelo y credencial.
use super::*;
use gpui_kit::component::Icon;

impl FlowApp {
    fn provider_buttons(&self, cx: &mut Context<Self>) -> Div {
        let providers = [("gemini", "Google Gemini"), ("minimax", "Minimax")];
        div()
            .w_full()
            .grid()
            .grid_cols(2)
            .gap(px(8.))
            .children(providers.iter().map(|(key, name)| {
                let active = self.settings_provider == *key;
                let provider = *key;
                let button = if active {
                    accent_button(format!("provider-{key}"), *name, false)
                } else {
                    button(format!("provider-{key}"), *name, false)
                };
                div()
                    .w_full()
                    .min_w_0()
                    .overflow_hidden()
                    .child(
                        button
                            .w_full()
                            .on_click(cx.listener(move |this, _, window, cx| {
                                this.switch_provider(provider, window, cx)
                            })),
                    )
            }))
    }

    fn model_list(&self, cx: &mut Context<Self>) -> Div {
        if self.settings_models.is_empty() {
            return div();
        }
        let mut grid = div().w_full().grid().grid_cols(2).gap(px(8.));
        for model in &self.settings_models {
            let active = self.settings_model == *model;
            let selected = model.clone();
            let lbl = if active {
                format!("✓ {model}")
            } else {
                model.clone()
            };
            grid = grid.child(
                fat_button(format!("model-{model}"), lbl, active, false)
                    .w_full()
                    .h(px(36.))
                    .on_click(cx.listener(move |this, _, window, cx| {
                        this.settings_model = selected.clone();
                        this.settings_model_input.update(cx, |state, cx| {
                            state.set_value(selected.clone(), window, cx)
                        });
                    })),
            );
        }
        div().w_full().child(
            div()
                .id("model-options")
                .w_full()
                .max_h(px(176.))
                .overflow_y_scroll()
                .child(grid),
        )
    }

    pub fn settings_view(&self, cx: &mut Context<Self>) -> Div {
        let status = if self.settings_status.is_empty() {
            "Pulsa «Guardar ajustes» para aplicar los cambios.".to_string()
        } else {
            self.settings_status.clone()
        };

        let account_title = if self.voice_catalog.authenticated {
            self.voice_catalog.user.clone()
        } else if self.voice_waiting_login {
            "Esperando el inicio de sesión en el navegador…".to_string()
        } else {
            "Conecta tu cuenta de Aurora".to_string()
        };

        let account_sub = if self.voice_catalog.authenticated {
            if self.voice_catalog.internal {
                "Acceso interno · Sin consumo de créditos".to_string()
            } else {
                format!(
                    "{} · {} créditos disponibles",
                    if self.voice_catalog.plan.is_empty() {
                        "Plan activo"
                    } else {
                        self.voice_catalog.plan.as_str()
                    },
                    self.voice_catalog
                        .balance
                        .map(|v| v.to_string())
                        .unwrap_or_else(|| "Sin confirmar".into())
                )
            }
        } else if self.voice_waiting_login {
            "Al autorizar en el navegador, DaVinci Flow detectará el retorno automáticamente."
                .to_string()
        } else {
            "Inicia sesión con tu cuenta de Aurora para desbloquear motores de voz en la nube y consultar tu saldo.".to_string()
        };

        let account_badge = if self.voice_catalog.authenticated {
            chip("Sesión activa", true)
        } else if self.voice_waiting_login {
            chip("Esperando autorización…", false)
        } else {
            chip("Sin conectar", false)
        };

        let p = palette();
        let aurora_card = card()
            .w_full()
            .gap(px(12.))
            .p(px(16.))
            .child(
                row()
                    .w_full()
                    .justify_between()
                    .child(section("Cuenta de Aurora"))
                    .child(account_badge),
            )
            .child(
                div()
                    .text_size(px(14.))
                    .font_weight(FontWeight::SEMIBOLD)
                    .child(account_title),
            )
            .child(label(account_sub))
            .when(
                !self.voice_catalog.authenticated && !self.voice_waiting_login,
                |c| {
                    c.child(
                        row()
                            .w_full()
                            .gap(px(8.))
                            .child(
                                fat_button(
                                    "account-login-google",
                                    "Continuar con Google",
                                    true,
                                    self.busy,
                                )
                                .on_click(cx.listener(|this, _, window, cx| {
                                    this.voice_login_provider("google", window, cx)
                                })),
                            )
                            .child(
                                fat_button(
                                    "account-login-discord",
                                    "Continuar con Discord",
                                    false,
                                    self.busy,
                                )
                                .on_click(cx.listener(|this, _, window, cx| {
                                    this.voice_login_provider("discord", window, cx)
                                })),
                            ),
                    )
                },
            )
            .when(self.voice_waiting_login, |c| {
                c.child(
                    row()
                        .w_full()
                        .gap(px(8.))
                        .child(
                            fat_button("account-complete", "Completar acceso", true, self.busy)
                                .on_click(cx.listener(|this, _, window, cx| {
                                    this.voice_complete(window, cx)
                                })),
                        )
                        .child(
                            fat_button("account-cancel", "Cancelar inicio", false, self.busy)
                                .on_click(cx.listener(|this, _, window, cx| {
                                    this.voice_cancel_login(window, cx)
                                })),
                        ),
                )
            })
            .child(
                row()
                    .w_full()
                    .gap(px(8.))
                    .child(
                        div().flex_1().flex().flex_col().child(
                            button("account-refresh", "Actualizar acceso", self.busy).on_click(
                                cx.listener(|this, _, window, cx| this.refresh_voices(window, cx)),
                            ),
                        ),
                    )
                    .when(self.voice_catalog.authenticated, |r| {
                        r.child(
                            div().flex_1().flex().flex_col().child(
                                button("account-logout", "Cerrar sesión", self.busy).on_click(
                                    cx.listener(|this, _, window, cx| {
                                        this.voice_logout(window, cx)
                                    }),
                                ),
                            ),
                        )
                    }),
            )
            .child(div().w_full().h(px(1.)).bg(rgb(p.line)))
            .child(label(
                "La sesión de Aurora se cifra localmente mediante Windows DPAPI y es independiente por instalación.",
            ));

        let theme_aurora = self.preferences.appearance_theme != "classic";
        let mode_light = self.preferences.appearance_mode == "light";
        let cur_mode_for_aurora = self.preferences.appearance_mode.clone();
        let cur_mode_for_classic = self.preferences.appearance_mode.clone();
        let cur_theme_for_dark = self.preferences.appearance_theme.clone();
        let cur_theme_for_light = self.preferences.appearance_theme.clone();

        let appearance_card = card()
            .w_full()
            .gap(px(12.))
            .p(px(16.))
            .child(
                row()
                    .w_full()
                    .justify_between()
                    .child(section("Apariencia"))
                    .child(chip(
                        if theme_aurora {
                            "Aurora · Ely turquesa"
                        } else {
                            "Clásico"
                        },
                        theme_aurora,
                    )),
            )
            .child(
                column()
                    .w_full()
                    .gap(px(6.))
                    .child(field_label("Tema"))
                    .child(
                        row()
                            .w_full()
                            .gap(px(8.))
                            .child(
                                fat_button(
                                    "theme-aurora",
                                    if theme_aurora { "✓ Aurora" } else { "Aurora" },
                                    theme_aurora,
                                    false,
                                )
                                .on_click(cx.listener(move |this, _, window, cx| {
                                    this.set_appearance_preference(
                                        "aurora",
                                        &cur_mode_for_aurora,
                                        window,
                                        cx,
                                    )
                                })),
                            )
                            .child(
                                fat_button(
                                    "theme-classic",
                                    if !theme_aurora { "✓ Clásico" } else { "Clásico" },
                                    !theme_aurora,
                                    false,
                                )
                                .on_click(cx.listener(move |this, _, window, cx| {
                                    this.set_appearance_preference(
                                        "classic",
                                        &cur_mode_for_classic,
                                        window,
                                        cx,
                                    )
                                })),
                            ),
                    ),
            )
            .child(
                column()
                    .w_full()
                    .gap(px(6.))
                    .child(field_label("Modo"))
                    .child(
                        row()
                            .w_full()
                            .gap(px(8.))
                            .child(
                                fat_button(
                                    "mode-dark",
                                    if !mode_light { "✓ Oscuro" } else { "Oscuro" },
                                    !mode_light,
                                    false,
                                )
                                .on_click(cx.listener(move |this, _, window, cx| {
                                    this.set_appearance_preference(
                                        &cur_theme_for_dark,
                                        "dark",
                                        window,
                                        cx,
                                    )
                                })),
                            )
                            .child(
                                fat_button(
                                    "mode-light",
                                    if mode_light { "✓ Claro" } else { "Claro" },
                                    mode_light,
                                    false,
                                )
                                .on_click(cx.listener(move |this, _, window, cx| {
                                    this.set_appearance_preference(
                                        &cur_theme_for_light,
                                        "light",
                                        window,
                                        cx,
                                    )
                                })),
                            ),
                    ),
            )
            .child(label(
                "Aurora aplica la paleta compartida con acento Ely turquesa; Clásico conserva la paleta anterior.",
            ));

        let left_column = column()
            .flex_1()
            .flex_basis(px(0.))
            .min_w_0()
            .gap(px(12.))
            .child(aurora_card)
            .child(appearance_card);

        let ai_card = card()
            .flex_1()
            .flex_basis(px(0.))
            .min_w_0()
            .gap(px(12.))
            .p(px(16.))
            .child(section("Modelo de Inteligencia Artificial"))
            .child(
                row()
                    .w_full()
                    .gap(px(10.))
                    .items_end()
                    .child(
                        column()
                            .flex_1()
                            .min_w_0()
                            .gap(px(4.))
                            .child(field_label("Proveedor de IA"))
                            .child(self.provider_buttons(cx)),
                    )
                    .child(
                        column()
                            .flex_1()
                            .min_w_0()
                            .gap(px(4.))
                            .child(field_label("Selector de modelos"))
                            .child(Input::new(&self.settings_model_input)),
                    ),
            )
            .child(
                row()
                    .w_full()
                    .gap(px(10.))
                    .items_center()
                    .child(
                        button(
                            "scan-models",
                            "Escanear modelos",
                            self.busy || self.settings_provider != "gemini",
                        )
                        .on_click(cx.listener(|this, _, window, cx| this.scan_models(window, cx))),
                    )
                    .child(label(if self.settings_provider == "minimax" {
                        "Modelos de Minimax preconfigurados.".to_string()
                    } else if self.settings_models.is_empty() {
                        "Escanea modelos para consultar el catálogo de Gemini.".to_string()
                    } else {
                        format!("{} modelos disponibles.", self.settings_models.len())
                    })),
            )
            .child(self.model_list(cx))
            .child(
                column()
                    .w_full()
                    .gap(px(4.))
                    .child(field_label(if self.settings_provider == "minimax" {
                        "Clave API de Minimax"
                    } else {
                        "Clave API de Gemini"
                    }))
                    .child(Input::new(&self.settings_key)),
            )
            .child(label(status))
            .child(
                row().w_full().child(
                    fat_button("save-settings", "Guardar ajustes", true, self.busy).on_click(
                        cx.listener(|this, _, window, cx| this.save_settings(window, cx)),
                    ),
                ),
            );

        column()
            .size_full()
            .min_h_0()
            .gap(px(12.))
            .child(
                row()
                    .w_full()
                    .items_start()
                    .gap(px(12.))
                    .child(left_column)
                    .child(ai_card),
            )
            .child(label(
                "Un error de la API conserva tu propuesta anterior y no cambia de modelo. Aplicar una revisión guardada no vuelve a llamar a la IA.",
            ))
            .child(
                row()
                    .gap(px(8.))
                    .child(
                        Icon::new(IconName::Info)
                            .size(px(16.))
                            .text_color(rgb(p.muted)),
                    )
                    .child(label("La clave se guarda en la configuración del usuario.")),
            )
    }
}
