//! Pestaña «Ajustes»: proveedor de IA, modelo, credencial y preferencias editoriales.
use super::*;
use gpui_kit::component::Icon;

impl FlowApp {
    fn provider_buttons(&self, cx: &mut Context<Self>) -> Div {
        let providers = [("gemini", "Google Gemini"), ("minimax", "Minimax")];
        row()
            .gap(px(10.))
            .children(providers.iter().map(|(key, name)| {
                let active = self.settings_provider == *key;
                let provider = *key;
                let button = if active {
                    accent_button(format!("provider-{key}"), *name, false)
                } else {
                    button(format!("provider-{key}"), *name, false)
                };
                button.on_click(cx.listener(move |this, _, window, cx| {
                    this.switch_provider(provider, window, cx)
                }))
            }))
    }

    fn model_list(&self, cx: &mut Context<Self>) -> Div {
        if self.settings_models.is_empty() {
            return div();
        }
        div().child(
            column()
                .id("model-options")
                .max_h(px(140.))
                .overflow_y_scroll()
                .gap(px(6.))
                .children(self.settings_models.iter().map(|model| {
                    let active = self.settings_model == *model;
                    let selected = model.clone();
                    let button = if active {
                        accent_button(format!("model-{model}"), model.clone(), false)
                    } else {
                        button(format!("model-{model}"), model.clone(), false)
                    };
                    button.on_click(cx.listener(move |this, _, window, cx| {
                        this.settings_model = selected.clone();
                        this.settings_model_input.update(cx, |state, cx| {
                            state.set_value(selected.clone(), window, cx)
                        });
                    }))
                })),
        )
    }

    pub fn settings_view(&self, cx: &mut Context<Self>) -> Div {
        let status = if self.settings_status.is_empty() {
            "Pulsa «Guardar ajustes» para aplicar los cambios.".to_string()
        } else {
            self.settings_status.clone()
        };
        column()
            .w_full().max_w(px(840.))
            .min_h_0()
            .gap(px(14.))
            .child(
                card()
                    .gap(px(14.))
                    .p(px(12.))
                    .child(section("Modelo de Inteligencia Artificial"))
                    .child(
                        row()
                            .gap(px(10.))
                            .items_center()
                            .child(
                                column()
                                    .gap(px(4.))
                                    .child(field_label("Proveedor de IA"))
                                    .child(self.provider_buttons(cx)),
                            )
                            .child(
                                column()
                                    .flex_1()
                                    .gap(px(4.))
                                    .child(field_label("Selector de modelos"))
                                    .child(Input::new(&self.settings_model_input)),
                            ),
                    )
                    .child(
                        row()
                            .gap(px(10.))
                            .items_center()
                            .child(
                                button("scan-models", "Escanear modelos", self.busy||self.settings_provider!="gemini").on_click(
                                    cx.listener(|this, _, window, cx| this.scan_models(window, cx)),
                                ),
                            )
                            .child(label(if self.settings_models.is_empty() {
                                "Escanea modelos para consultar el catálogo de Gemini.".to_string()
                            } else {
                                format!("{} modelos disponibles.", self.settings_models.len())
                            })),
                    )
                    .child(self.model_list(cx))
                    .child(
                        column()
                            .gap(px(4.))
                            .child(field_label("Clave API"))
                            .child(Input::new(&self.settings_key)),
                    )
                    .child(label(status))
                    .child(
                        row().child(
                            accent_button("save-settings", "Guardar ajustes", self.busy).on_click(
                                cx.listener(|this, _, window, cx| this.save_settings(window, cx)),
                            ),
                        ),
                    ),
            )
            .child(card().child(section("Cuenta de Aurora"))
                .child(label(if self.voice_catalog.authenticated {self.voice_catalog.user.clone()}else{"Accede para usar tus voces y saldo de Aurora.".into()}))
                .child(row()
                    .child(button("account-login","Acceder a Aurora",self.busy).on_click(cx.listener(|this,_,window,cx|this.voice_login(window,cx))))
                    .child(button("account-complete","Completar acceso",self.busy).on_click(cx.listener(|this,_,window,cx|this.voice_complete(window,cx))))
                    .child(button("account-refresh","Actualizar cuenta",self.busy).on_click(cx.listener(|this,_,window,cx|this.refresh_voices(window,cx))))
                    .child(button("account-logout","Cerrar sesión",self.busy||!self.voice_catalog.authenticated).on_click(cx.listener(|this,_,window,cx|this.voice_logout(window,cx))))))
            .child(label(
                "Un error de la API conserva tu propuesta anterior y no cambia de modelo. Aplicar una revisión guardada no vuelve a llamar a la IA.",
            ))
            .child(
                row()
                    .gap(px(8.))
                    .child(
                        Icon::new(IconName::Info)
                            .size(px(16.))
                            .text_color(rgb(MUTED)),
                    )
                    .child(label("La clave se guarda en la configuración del usuario.")),
            )
    }
}
