use super::*;

impl FlowApp {
    pub fn voice_view(&self, cx: &mut Context<Self>) -> Div {
        let status = if self.voice_catalog.authenticated {
            format!(
                "{} · {} créditos",
                self.voice_catalog.user,
                self.voice_catalog
                    .balance
                    .map(|v| v.to_string())
                    .unwrap_or_else(|| "Sin confirmar".into())
            )
        } else {
            "Voces del sistema y voces de tu cuenta Aurora".into()
        };
        let mut voices = column()
            .id("voice-options")
            .max_h(px(150.))
            .overflow_y_scroll()
            .gap(px(4.));
        for (index, voice) in self.voice_catalog.voices.iter().enumerate() {
            voices = voices.child(
                button(
                    ("voice", index),
                    format!(
                        "{}{} · {}",
                        if self.voice_selected == Some(index) {
                            "✓ "
                        } else {
                            ""
                        },
                        voice.name,
                        voice.provider
                    ),
                    self.busy || !voice.ready,
                )
                .on_click(cx.listener(move |this, _, _, cx| {
                    this.voice_selected = Some(index);
                    this.voice_quote = None;
                    cx.notify();
                })),
            );
        }
        let mut view = column()
            .w_full()
            .max_w(px(860.))
            .gap(px(12.))
            .child(
                card()
                    .child(
                        row()
                            .child(section("Voces disponibles"))
                            .child(div().flex_1())
                            .child(
                                button("voice-refresh", "Actualizar voces", self.busy).on_click(
                                    cx.listener(|this, _, window, cx| {
                                        this.refresh_voices(window, cx)
                                    }),
                                ),
                            )
                            .child(
                                button("voice-account", "Gestionar cuenta", self.busy).on_click(
                                    cx.listener(|this, _, window, cx| {
                                        this.load_for_tab(Tab::Settings, window, cx)
                                    }),
                                ),
                            ),
                    )
                    .child(label(status))
                    .child(voices),
            )
            .child(
                card()
                    .child(section("Texto a voz"))
                    .child(div().h(px(165.)).child(Textarea::new(&self.voice_text)))
                    .child(
                        row()
                            .child(label(format!(
                                "{}/10.000 caracteres",
                                self.voice_text.read(cx).value().chars().count()
                            )))
                            .child(div().flex_1())
                            .child(
                                button(
                                    "voice-quote",
                                    "Calcular consumo",
                                    self.busy || self.voice_selected.is_none(),
                                )
                                .on_click(
                                    cx.listener(|this, _, window, cx| this.quote_voice(window, cx)),
                                ),
                            )
                            .child(
                                accent_button(
                                    "voice-generate",
                                    self.voice_quote
                                        .as_ref()
                                        .map(|(_, _, cost)| format!("Generar · {cost} créditos"))
                                        .unwrap_or_else(|| "Generar voz".into()),
                                    self.busy || self.voice_quote.is_none(),
                                )
                                .on_click(cx.listener(
                                    |this, _, window, cx| this.generate_voice(window, cx),
                                )),
                            ),
                    ),
            );
        // Recuperar es visible incluso si una generación falló antes de actualizar el catálogo.
        view = view.child(
            row().child(
                button(
                    "voice-recover",
                    "Recuperar generación pendiente",
                    self.busy || !self.voice_catalog.authenticated,
                )
                .on_click(cx.listener(|this, _, window, cx| this.recover_voice(window, cx))),
            ),
        );
        if let Some(path) = &self.voice_output {
            let play = path.clone();
            let reveal = path.clone();
            let import = path.clone();
            view = view.child(
                card().child(label(path.display().to_string())).child(
                    row()
                        .child(
                            button("voice-play", "Escuchar", self.busy).on_click(
                                cx.listener(move |_, _, _, cx| cx.open_with_system(&play)),
                            ),
                        )
                        .child(
                            button("voice-reveal", "Mostrar en carpeta", self.busy)
                                .on_click(cx.listener(move |_, _, _, cx| cx.reveal_path(&reveal))),
                        )
                        .child(
                            button("voice-import", "Importar a Resolve", self.busy).on_click(
                                cx.listener(move |this, _, window, cx| {
                                    this.import_file(import.clone(), window, cx)
                                }),
                            ),
                        ),
                ),
            );
        }
        view
    }
}
