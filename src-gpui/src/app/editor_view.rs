//! Pestaña «Editor»: captura del montaje y estado de la mesa editorial.
use super::*;
use gpui_kit::component::Icon;

impl FlowApp {
    fn stage_chips(&self, cx: &mut Context<Self>) -> Div {
        let stages = [
            (1u8, "1. Montaje y Subtítulos", IconName::Download),
            (2, "2. Mesa de Revisión", IconName::Star),
            (3, "3. Aplicación en Resolve", IconName::Clapperboard),
        ];
        row()
            .gap(px(10.))
            .children(stages.iter().map(|(number, label, icon)| {
                let current = self.editor_stage == *number;
                let past = self.editor_stage > *number;
                let background = if current {
                    0x1F4037
                } else if past {
                    0x162320
                } else {
                    0x1A2126
                };
                let border = if current {
                    ACCENT
                } else if past {
                    0x2A4A43
                } else {
                    0x2B353B
                };
                let text = if current {
                    0xFFFFFF
                } else if past {
                    TEXT
                } else {
                    MUTED
                };
                let stage = *number;
                let weak = cx.entity().downgrade();
                row()
                    .id(("stage", stage as usize))
                    .role(Role::Button)
                    .aria_label(*label)
                    .focusable()
                    .tab_index(0)
                    .px(px(12.))
                    .py(px(6.))
                    .rounded(px(16.))
                    .gap(px(6.))
                    .bg(rgb(background))
                    .border_1()
                    .border_color(rgb(border))
                    .cursor_pointer()
                    .hover(|item| item.bg(rgb(CARD)))
                    .child(
                        Icon::new(*icon)
                            .size(px(14.))
                            .text_color(rgb(if current || past { ACCENT } else { MUTED })),
                    )
                    .child(
                        div()
                            .text_size(px(12.))
                            .font_weight(if current {
                                FontWeight::SEMIBOLD
                            } else {
                                FontWeight::NORMAL
                            })
                            .text_color(rgb(text))
                            .child(*label),
                    )
                    .on_click({
                        let weak = weak.clone();
                        move |_, _, cx| {
                            if let Some(entity) = weak.upgrade() {
                                entity.update(cx, |this, cx| this.set_stage(stage, cx));
                            }
                        }
                    })
            }))
    }

    fn set_stage(&mut self, stage: u8, cx: &mut Context<Self>) {
        if stage > 1 && self.proposal.is_none() {
            self.notify(
                Err(
                    "Prepara una propuesta o abre una revisión guardada antes de continuar.".into(),
                ),
                cx,
            );
            return;
        }
        self.editor_stage = stage;
        cx.notify();
    }

    fn editor_table(&self, cx: &mut Context<Self>) -> Div {
        let entity = cx.entity().downgrade();
        let count = self.session.document().cues.len();
        let rows = uniform_list("editor-table", count, move |range, _, cx| {
            let Some(entity) = entity.upgrade() else {
                return vec![];
            };
            let this = entity.read(cx);
            range
                .filter_map(|index| this.session.document().cues.get(index))
                .map(|cue| {
                    row()
                        .w_full()
                        .h(px(40.))
                        .px(px(14.))
                        .gap(px(16.))
                        .border_b_1()
                        .border_color(rgb(LINE))
                        .bg(rgb(CARD))
                        .child(
                            div()
                                .w(px(140.))
                                .text_size(px(11.))
                                .text_color(rgb(MUTED))
                                .child(format!(
                                    "{}–{}",
                                    subtitles::timecode(cue.start_ms),
                                    subtitles::timecode(cue.end_ms)
                                )),
                        )
                        .child(
                            div()
                                .flex_1()
                                .min_w_0()
                                .text_ellipsis()
                                .child(cue.text.clone()),
                        )
                })
                .collect::<Vec<_>>()
        });
        column()
            .flex_1()
            .min_h_0()
            .gap_0()
            .bg(rgb(CARD))
            .rounded(px(10.))
            .overflow_hidden()
            .child(
                row()
                    .h(px(38.))
                    .flex_shrink_0()
                    .bg(rgb(HEADING))
                    .px(px(14.))
                    .gap(px(16.))
                    .child(div().w(px(140.)).child(label("Tiempo")))
                    .child(div().flex_1().min_w_0().child(label("Texto del subtítulo"))),
            )
            .child(div().flex_1().min_h_0().child(rows.h_full()))
    }

    pub fn editor_view(&self, cx: &mut Context<Self>) -> Div {
        if self.editor_stage > 1 {
            return column()
                .size_full()
                .min_h_0()
                .gap_3()
                .child(self.stage_chips(cx))
                .child(self.review_view(cx));
        }
        let document = self.session.document();
        let count = document.cues.len();
        let busy = self.busy;

        let summary = if count > 0 {
            format!(
                "{} · {} subtítulos",
                if document.source.is_empty() {
                    "SRT".to_string()
                } else {
                    document.source.clone()
                },
                count
            )
        } else {
            "Captura los subtítulos de tu montaje o abre un SRT.".to_string()
        };

        let view = column()
            .size_full()
            .min_h_0()
            .gap(px(10.))
            .child(self.stage_chips(cx))
            .child(
                card()
                    .gap(px(10.))
                    .child(
                        row()
                            .gap(px(10.))
                            .items_start()
                            .child(
                                column()
                                    .w(px(72.))
                                    .gap(px(4.))
                                    .child(field_label("Pista"))
                                    .child(Input::new(&self.editor_track)),
                            )
                            .child(
                                column()
                                    .w(px(90.))
                                    .gap(px(4.))
                                    .child(field_label("FPS SRT"))
                                    .child(Input::new(&self.editor_fps)),
                            )
                            .child(
                                column()
                                    .w(px(80.))
                                    .gap(px(4.))
                                    .child(field_label("Desde"))
                                    .child(Input::new(&self.editor_first)),
                            )
                            .child(
                                column()
                                    .w(px(80.))
                                    .gap(px(4.))
                                    .child(field_label("Hasta"))
                                    .child(Input::new(&self.editor_last)),
                            )
                            .child(
                                row()
                                    .gap(px(8.))
                                    .child(
                                        button("capture-resolve", "Capturar Resolve", busy)
                                            .on_click(cx.listener(|this, _, window, cx| {
                                                this.capture(window, cx)
                                            })),
                                    )
                                    .child(button("open-srt", "Cargar SRT", busy).on_click(
                                        cx.listener(|this, _, window, cx| {
                                            this.choose_srt(window, cx)
                                        }),
                                    )),
                            ),
                    )
                    .child(
                        row()
                            .child(
                                div()
                                    .flex_1()
                                    .min_w_0()
                                    .text_ellipsis()
                                    .child(label(summary)),
                            )
                            .child(
                                button("check-resolve", "Comprobar conexión", busy).on_click(
                                    cx.listener(|this, _, window, cx| {
                                        this.check_resolve(window, cx)
                                    }),
                                ),
                            ),
                    ),
            );
        let view = view.child(
            row().child(
                button("open-saved-proposal", "Abrir revisión guardada", busy)
                    .on_click(cx.listener(|this, _, w, cx| this.open_proposal(w, cx))),
            ),
        );
        let options = &self.editor_options;
        let view = view.child(
            card()
                .gap(px(6.))
                .child(
                    row()
                        .child(
                            button(
                                "editor-mode",
                                if options.mode == "captions" {
                                    "Subtítulos completos"
                                } else {
                                    "Destacados"
                                },
                                busy,
                            )
                            .on_click(cx.listener(|this, _, _, cx| {
                                this.editor_options.mode =
                                    if this.editor_options.mode == "captions" {
                                        "highlights"
                                    } else {
                                        "captions"
                                    }
                                    .into();
                                cx.notify();
                            })),
                        )
                        .child(
                            button(
                                "editor-format",
                                format!(
                                    "Formato: {}",
                                    match options.format.as_str() {
                                        "horizontal" => "16:9",
                                        "vertical" => "9:16",
                                        _ => "Auto",
                                    }
                                ),
                                busy,
                            )
                            .on_click(cx.listener(|this, _, _, cx| {
                                this.editor_options.format =
                                    match this.editor_options.format.as_str() {
                                        "auto" => "horizontal",
                                        "horizontal" => "vertical",
                                        _ => "auto",
                                    }
                                    .into();
                                cx.notify();
                            })),
                        )
                        .child(
                            button(
                                "editor-density",
                                format!(
                                    "Densidad: {}",
                                    match options.density.as_str() {
                                        "sparse" => "Baja",
                                        "dense" => "Alta",
                                        _ => "Media",
                                    }
                                ),
                                busy,
                            )
                            .on_click(cx.listener(|this, _, _, cx| {
                                this.editor_options.density =
                                    match this.editor_options.density.as_str() {
                                        "balanced" => "dense",
                                        "dense" => "sparse",
                                        _ => "balanced",
                                    }
                                    .into();
                                cx.notify();
                            })),
                        )
                        .child(
                            button(
                                "editor-tracks",
                                format!(
                                    "Pistas: {}",
                                    match options.track_mode.as_str() {
                                        "single" => 1,
                                        "dual" => 2,
                                        _ => 3,
                                    }
                                ),
                                busy,
                            )
                            .on_click(cx.listener(|this, _, _, cx| {
                                this.editor_options.track_mode =
                                    match this.editor_options.track_mode.as_str() {
                                        "triple" => "single",
                                        "single" => "dual",
                                        _ => "triple",
                                    }
                                    .into();
                                cx.notify();
                            })),
                        ),
                )
                .child(Input::new(&self.editor_direction)),
        );
        if count == 0 {
            return view.child(
                card()
                    .items_center()
                    .gap(px(10.))
                    .p(px(36.))
                    .child(
                        Icon::new(IconName::Captions)
                            .size(px(32.))
                            .text_color(rgb(ACCENT)),
                    )
                    .child(
                        div()
                            .text_size(px(17.))
                            .font_weight(FontWeight::MEDIUM)
                            .child("Las ideas empiezan con tu montaje"),
                    )
                    .child(label(
                        "Lee una pista de Resolve o importa un SRT. Después decide qué merece aparecer en pantalla.",
                    )),
            );
        }
        view.child(
            row()
                .child(
                    accent_button("prepare-direct", "Preparar revisión directa", busy).on_click(
                        cx.listener(|this, _, w, cx| this.prepare_proposal(false, w, cx)),
                    ),
                )
                .child(
                    button("prepare-ai", "Proponer con IA", busy)
                        .on_click(cx.listener(|this, _, w, cx| this.prepare_proposal(true, w, cx))),
                )
                .child(
                    button("open-proposal", "Abrir propuesta JSON", busy)
                        .on_click(cx.listener(|this, _, w, cx| this.open_proposal(w, cx))),
                ),
        )
        .child(self.editor_table(cx))
    }
}
