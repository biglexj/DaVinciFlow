//! Pestaña «Generación de voz»: motores y voces de Aurora y del sistema, estimación e importación.
use super::*;

const VOICE_STUDIO_URL: &str = "https://biglexj.com/creator-suite/audio?tab=voice_studio";

/// Extrae únicamente el nombre limpio de la voz (sin descripciones ni etiquetas entre paréntesis).
fn voice_short_name(raw: &str) -> String {
    let trimmed = raw.trim();
    let without_paren = if let Some(open) = trimmed.rfind('(')
        && trimmed.ends_with(')')
        && open > 0
    {
        trimmed[..open].trim()
    } else {
        trimmed
    };
    without_paren
        .strip_suffix(" Desktop")
        .unwrap_or(without_paren)
        .trim()
        .to_string()
}

impl FlowApp {
    fn voice_card(
        &self,
        index: usize,
        title: String,
        active: bool,
        disabled: bool,
    ) -> Stateful<Div> {
        let p = palette();
        let heading = if active {
            format!("✓ {title}")
        } else {
            title.clone()
        };
        div()
            .id(("voice", index))
            .role(Role::Button)
            .aria_label(title)
            .w_full()
            .min_w_0()
            .h(px(42.))
            .px(px(10.))
            .rounded(px(8.))
            .overflow_hidden()
            .flex()
            .items_center()
            .justify_center()
            .bg(rgb(if active { p.accent } else { p.raised }))
            .when(!active, |b| b.border_1().border_color(rgb(p.line)))
            .when(disabled, |b| b.opacity(0.45).cursor_default())
            .when(!disabled, |b| {
                b.cursor_pointer().hover(move |style| {
                    if active {
                        style.bg(rgb(p.accent_hover))
                    } else {
                        style.bg(rgb(p.active)).border_color(rgb(p.accent))
                    }
                })
            })
            .child(
                div()
                    .w_full()
                    .min_w_0()
                    .overflow_hidden()
                    .whitespace_nowrap()
                    .text_ellipsis()
                    .text_center()
                    .text_size(px(12.5))
                    .font_weight(if active {
                        FontWeight::BOLD
                    } else {
                        FontWeight::MEDIUM
                    })
                    .text_color(rgb(if active { p.on_accent } else { p.text }))
                    .child(heading),
            )
    }

    pub fn voice_view(&self, cx: &mut Context<Self>) -> Div {
        let status = if self.voice_catalog.authenticated {
            if self.voice_catalog.internal {
                format!(
                    "{} · Acceso interno · Sin consumo de créditos",
                    self.voice_catalog.user
                )
            } else {
                format!(
                    "{} · {} · {} créditos disponibles",
                    self.voice_catalog.user,
                    if self.voice_catalog.plan.is_empty() {
                        "Aurora"
                    } else {
                        self.voice_catalog.plan.as_str()
                    },
                    self.voice_catalog
                        .balance
                        .map(|v| v.to_string())
                        .unwrap_or_else(|| "Sin confirmar".into())
                )
            }
        } else {
            "Voces del sistema · Gratis. Inicia sesión en Ajustes para usar motores de Aurora."
                .into()
        };

        let engine_count = self.voice_catalog.engines.len().max(1) as u16;
        let mut engine_row = div().w_full().grid().grid_cols(engine_count).gap(px(8.));
        if self.voice_catalog.engines.is_empty() {
            let active = self.voice_engine == "system";
            let btn = if active {
                accent_button("eng-system", "Sistema · Gratis", false)
            } else {
                button("eng-system", "Sistema · Gratis", false)
            };
            engine_row = engine_row.child(div().w_full().min_w_0().overflow_hidden().child(
                btn.w_full().on_click(cx.listener(|this, _, _, cx| {
                    this.voice_engine = "system".into();
                    this.sync_voice_selection();
                    this.voice_quote = None;
                    cx.notify();
                })),
            ));
        } else {
            for eng in &self.voice_catalog.engines {
                let key = eng.id.clone();
                let active = self.voice_engine == key;
                let has_voices = self
                    .voice_catalog
                    .voices
                    .iter()
                    .any(|v| v.ready && v.provider == key);
                let enabled = eng.available && has_voices;
                let base_name = if eng.id == "system" {
                    "Sistema · Gratis".to_string()
                } else {
                    eng.name.clone()
                };
                let lbl = if enabled {
                    base_name
                } else {
                    format!("{base_name} · No disp.")
                };
                let btn = if active {
                    accent_button(format!("eng-{key}"), lbl, self.busy || !enabled)
                } else {
                    button(format!("eng-{key}"), lbl, self.busy || !enabled)
                };
                engine_row = engine_row.child(div().w_full().min_w_0().overflow_hidden().child(
                    btn.w_full().on_click(cx.listener(move |this, _, _, cx| {
                        this.voice_engine = key.clone();
                        this.sync_voice_selection();
                        this.voice_quote = None;
                        cx.notify();
                    })),
                ));
            }
        }

        let provider_voices: Vec<(usize, &_)> = self
            .voice_catalog
            .voices
            .iter()
            .enumerate()
            .filter(|(_, voice)| voice.provider == self.voice_engine)
            .collect();
        let mut voices_grid = div().w_full().grid().grid_cols(4).gap(px(8.));
        for (index, voice) in provider_voices {
            let active = self.voice_selected == Some(index);
            let disabled = self.busy || !voice.ready;
            let title = voice_short_name(&voice.name);
            let btn = self.voice_card(index, title, active, disabled);
            let btn = if disabled {
                btn
            } else {
                btn.on_click(cx.listener(move |this, _, _, cx| {
                    this.voice_selected = Some(index);
                    this.voice_quote = None;
                    cx.notify();
                }))
            };
            voices_grid = voices_grid.child(btn);
        }
        // Máximo 3 filas visibles (3 × 42 px + 2 × 8 px = 142 px); desplazamiento vertical para el resto.
        let voices = div()
            .id("voice-options")
            .w_full()
            .max_h(px(144.))
            .overflow_y_scroll()
            .child(voices_grid);

        let char_count = self.voice_text.read(cx).value().trim().chars().count();
        let is_local = self.voice_engine == "system";
        let estimate_label = if is_local {
            format!("{char_count}/10.000 caracteres · Gratis · Generación local")
        } else if let Some((_, _, cost)) = &self.voice_quote {
            format!("{char_count}/10.000 caracteres · {cost} créditos confirmados")
        } else if self.voice_catalog.internal {
            format!("{char_count}/10.000 caracteres · Sin consumo de créditos")
        } else {
            format!("{char_count}/10.000 caracteres · Pulsa «Calcular consumo»")
        };

        let can_generate = !self.busy
            && self.voice_selected.is_some()
            && (1..=10_000).contains(&char_count)
            && (is_local || self.voice_quote.is_some());

        let mut view = column()
            .size_full()
            .min_h_0()
            .gap(px(10.))
            .child(
                card()
                    .gap(px(8.))
                    .child(
                        row()
                            .child(section("Motor y voz"))
                            .child(div().flex_1())
                            .child(
                                button("voice-refresh", "Actualizar acceso", self.busy).on_click(
                                    cx.listener(|this, _, window, cx| {
                                        this.refresh_voices(window, cx)
                                    }),
                                ),
                            )
                            .child(button("voice-account", "Ir a Ajustes", self.busy).on_click(
                                cx.listener(|this, _, window, cx| {
                                    this.load_for_tab(Tab::Settings, window, cx)
                                }),
                            )),
                    )
                    .child(label(status))
                    .child(field_label("Proveedor / modelo"))
                    .child(engine_row)
                    .child(field_label("Voz"))
                    .child(voices)
                    .when(!self.voice_catalog.warnings.is_empty(), |c| {
                        c.child(label(self.voice_catalog.warnings.join(" ")))
                    }),
            )
            .child(
                card()
                    .gap(px(8.))
                    .child(section("Guion de voz"))
                    .child(div().h(px(150.)).child(Textarea::new(&self.voice_text)))
                    .child(
                        row()
                            .child(label(estimate_label))
                            .child(div().flex_1())
                            .when(!is_local, |r| {
                                r.child(
                                    button(
                                        "voice-quote",
                                        "Calcular consumo",
                                        self.busy
                                            || self.voice_selected.is_none()
                                            || char_count == 0,
                                    )
                                    .on_click(cx.listener(
                                        |this, _, window, cx| this.quote_voice(window, cx),
                                    )),
                                )
                            })
                            .child(
                                accent_button(
                                    "voice-generate",
                                    if is_local {
                                        "Generar voz (local)".to_string()
                                    } else {
                                        self.voice_quote
                                            .as_ref()
                                            .map(|(_, _, cost)| {
                                                format!("Generar · {cost} créditos")
                                            })
                                            .unwrap_or_else(|| "Generar voz".into())
                                    },
                                    !can_generate,
                                )
                                .on_click(cx.listener(
                                    |this, _, window, cx| this.generate_voice(window, cx),
                                )),
                            )
                            .child(
                                button(
                                    "voice-recover",
                                    "Recuperar generación",
                                    self.busy || !self.voice_catalog.authenticated,
                                )
                                .on_click(
                                    cx.listener(|this, _, window, cx| {
                                        this.recover_voice(window, cx)
                                    }),
                                ),
                            ),
                    ),
            );

        let audio_label = self
            .voice_output
            .as_ref()
            .map(|p| p.display().to_string())
            .unwrap_or_else(|| {
                "Aún no hay audio. También puedes seleccionar uno descargado de Voice Studio."
                    .into()
            });
        let has_audio = self.voice_output.is_some();
        let output_path = self.voice_output.clone();

        view = view.child(
            card()
                .gap(px(8.))
                .child(section("Audio generado"))
                .child(label(audio_label))
                .child(
                    row()
                        .gap(px(8.))
                        .child({
                            let p = output_path.clone();
                            accent_button(
                                "voice-import",
                                "Importar a Resolve",
                                self.busy || !has_audio,
                            )
                            .on_click(cx.listener(
                                move |this, _, window, cx| {
                                    if let Some(path) = &p {
                                        this.import_voice_file(path.clone(), window, cx);
                                    }
                                },
                            ))
                        })
                        .child({
                            let p = output_path.clone();
                            let is_playing = p
                                .as_ref()
                                .is_some_and(|path| self.playing_sound.as_ref() == Some(path));
                            let disabled = self.busy || !has_audio;
                            let btn = fixed_media_button(
                                "voice-play",
                                if is_playing {
                                    IconName::Pause
                                } else {
                                    IconName::Play
                                },
                                if is_playing { "Pausar" } else { "Reproducir" },
                                is_playing,
                                disabled,
                                118.0,
                            );
                            if disabled {
                                btn
                            } else {
                                btn.on_click(cx.listener(move |this, _, window, cx| {
                                    if let Some(path) = &p {
                                        this.toggle_sound_file(path.clone(), window, cx);
                                    }
                                }))
                            }
                        })
                        .child({
                            let p = output_path.clone();
                            button(
                                "voice-reveal",
                                "Mostrar en carpeta",
                                self.busy || !has_audio,
                            )
                            .on_click(cx.listener(
                                move |_, _, _, cx| {
                                    if let Some(path) = &p {
                                        cx.reveal_path(path);
                                    }
                                },
                            ))
                        })
                        .child(
                            button("voice-pick", "Seleccionar audio", self.busy).on_click(
                                cx.listener(|this, _, window, cx| this.pick_voice_file(window, cx)),
                            ),
                        )
                        .child(
                            button("voice-studio-web", "Voice Studio web ↗", false)
                                .on_click(cx.listener(|_, _, _, cx| cx.open_url(VOICE_STUDIO_URL))),
                        ),
                )
                .child(self.inline_voice_player(cx))
                .child(label(
                    "Se importa al Media Pool del proyecto activo, en «DaVinci Flow · Voces».",
                )),
        );
        div().size_full().min_h_0().child(
            column()
                .id("voice-scroll")
                .size_full()
                .overflow_y_scroll()
                .child(view),
        )
    }
}
