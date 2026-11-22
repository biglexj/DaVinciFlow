//! Pestaña «Editor»: captura del montaje y mesa editorial de 7 columnas.
use super::editor_actions::ProposalMode;
use super::*;
use gpui_kit::component::Icon;

impl FlowApp {
    pub(super) fn stage_chips(&self, cx: &mut Context<Self>) -> Div {
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
                        move |_, window, cx| {
                            if let Some(entity) = weak.upgrade() {
                                entity.update(cx, |this, cx| this.set_stage(stage, window, cx));
                            }
                        }
                    })
            }))
    }

    fn set_stage(&mut self, stage: u8, window: &mut Window, cx: &mut Context<Self>) {
        if stage > 1 && self.proposal.is_none() {
            if !self.session.document().cues.is_empty() && stage == 2 {
                self.prepare_proposal_with(ProposalMode::Direct, window, cx);
                return;
            }
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
            let proposal = this.proposal.as_ref();
            range
                .filter_map(|index| this.session.document().cues.get(index).map(|c| (index, c)))
                .map(|(index, cue)| {
                    let decision = proposal.and_then(|p| p.decisions.get(index));
                    let has_conflict = this.conflicts.iter().any(|c| c.cue_index == index);
                    let context_txt = decision.map(|d| d.context.as_str()).unwrap_or("—");
                    let main_txt = decision
                        .map(|d| {
                            if d.enabled {
                                d.main.as_str()
                            } else {
                                "Sin rótulo"
                            }
                        })
                        .unwrap_or(cue.text.as_str());
                    let accent_txt = decision.map(|d| d.accent.as_str()).unwrap_or("—");
                    let sfx_txt = match decision {
                        Some(d) if !d.resource_id.is_empty() => proposal
                            .and_then(|p| p.options.as_ref())
                            .and_then(|opts| {
                                opts.resources.iter().find(|r| {
                                    r.get("id").and_then(Value::as_str)
                                        == Some(d.resource_id.as_str())
                                })
                            })
                            .and_then(|r| r.get("name").and_then(Value::as_str))
                            .or_else(|| {
                                this.user_sfx_resources
                                    .iter()
                                    .chain(this.user_broll_resources.iter())
                                    .find(|r| r.id == d.resource_id)
                                    .map(|r| r.name.as_str())
                            })
                            .or_else(|| {
                                this.sfx_assets
                                    .iter()
                                    .find(|a| a.id == d.resource_id)
                                    .map(|a| a.name.as_str())
                            })
                            .unwrap_or(d.resource_id.as_str()),
                        _ => "—",
                    };
                    let tpl_txt = if let (Some(p), Some(d)) = (proposal, decision) {
                        let names: Vec<_> = d
                            .templates
                            .values()
                            .filter_map(|id| p.templates.iter().find(|t| &t.id == id))
                            .map(|t| t.name.as_str())
                            .collect();
                        if names.is_empty() {
                            "Por elegir".to_string()
                        } else {
                            names.join(", ")
                        }
                    } else {
                        "Por elegir".to_string()
                    };
                    let status_label = match decision {
                        Some(d) if d.reviewed => "Revisado",
                        Some(_) => "Pendiente",
                        None => "Fuente",
                    };
                    let is_reviewed = decision.is_some_and(|d| d.reviewed);
                    let row_bg = if has_conflict {
                        0x3B1818
                    } else if this.proposal.is_some() && this.review_selected == index {
                        ACTIVE
                    } else {
                        CARD
                    };
                    let weak = entity.downgrade();
                    row()
                        .id(("editor-row", index))
                        .w_full()
                        .h(px(40.))
                        .px(px(14.))
                        .gap(px(12.))
                        .border_b_1()
                        .border_color(rgb(LINE))
                        .bg(rgb(row_bg))
                        .cursor_pointer()
                        .hover(|item| item.bg(rgb(HEADING)))
                        .child(
                            div()
                                .w(px(110.))
                                .text_size(px(11.))
                                .text_color(rgb(if has_conflict { ERROR } else { MUTED }))
                                .child(format!(
                                    "{}{}–{}",
                                    if has_conflict { "⚠️ " } else { "" },
                                    subtitles::timecode(cue.start_ms),
                                    subtitles::timecode(cue.end_ms)
                                )),
                        )
                        .child(
                            div()
                                .w(px(110.))
                                .text_ellipsis()
                                .text_size(px(12.))
                                .text_color(rgb(MUTED))
                                .child(if context_txt.is_empty() {
                                    "—".to_string()
                                } else {
                                    context_txt.to_string()
                                }),
                        )
                        .child(
                            div()
                                .flex_1()
                                .min_w_0()
                                .text_ellipsis()
                                .child(main_txt.to_string()),
                        )
                        .child(
                            div()
                                .w(px(110.))
                                .text_ellipsis()
                                .text_size(px(12.))
                                .text_color(rgb(ACCENT))
                                .child(if accent_txt.is_empty() {
                                    "—".to_string()
                                } else {
                                    accent_txt.to_string()
                                }),
                        )
                        .child(
                            div()
                                .w(px(90.))
                                .text_ellipsis()
                                .text_size(px(11.))
                                .text_color(rgb(MUTED))
                                .child(sfx_txt.to_string()),
                        )
                        .child(
                            div()
                                .w(px(140.))
                                .text_ellipsis()
                                .text_size(px(11.))
                                .text_color(rgb(MUTED))
                                .child(tpl_txt),
                        )
                        .child(div().w(px(86.)).child(chip(status_label, is_reviewed)))
                        .on_click(move |_, window, cx| {
                            if let Some(entity) = weak.upgrade() {
                                entity.update(cx, |this, cx| {
                                    if this.proposal.is_some() {
                                        this.review_selected = index;
                                        this.editor_stage = 2;
                                        this.sync_review(window, cx);
                                    } else {
                                        this.prepare_proposal_with(
                                            ProposalMode::Direct,
                                            window,
                                            cx,
                                        );
                                    }
                                });
                            }
                        })
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
                    .gap(px(12.))
                    .child(div().w(px(110.)).child(label("Tiempo")))
                    .child(div().w(px(110.)).child(label("Contexto")))
                    .child(div().flex_1().min_w_0().child(label("Principal")))
                    .child(div().w(px(110.)).child(label("Énfasis")))
                    .child(div().w(px(90.)).child(label("Recurso")))
                    .child(div().w(px(140.)).child(label("Plantilla")))
                    .child(div().w(px(86.)).child(label("Revisión"))),
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
            let source_name = if document.source.is_empty() {
                "SRT".to_string()
            } else {
                document.source.clone()
            };
            let batch_info = if self.batch_total > 0 {
                format!(
                    " · avance de secuencia: {}/{}",
                    self.batch_processed, self.batch_total
                )
            } else {
                String::new()
            };
            format!("{source_name} · {count} subtítulos{batch_info}")
        } else {
            "Captura los subtítulos de tu montaje o abre un SRT.".to_string()
        };

        let options = &self.editor_options;
        let source_card = card()
            .w_full()
            .min_w_0()
            .gap(px(8.))
            .child(section("Tramo y fuente"))
            .child(
                div()
                    .w_full()
                    .grid()
                    .grid_cols(2)
                    .gap(px(8.))
                    .child(
                        column()
                            .min_w_0()
                            .gap(px(3.))
                            .child(field_label("Pista"))
                            .child(Input::new(&self.editor_track)),
                    )
                    .child(
                        column()
                            .min_w_0()
                            .gap(px(3.))
                            .child(field_label("FPS SRT"))
                            .child(Input::new(&self.editor_fps)),
                    )
                    .child(
                        column()
                            .min_w_0()
                            .gap(px(3.))
                            .child(field_label("Desde"))
                            .child(Input::new(&self.editor_first)),
                    )
                    .child(
                        column()
                            .min_w_0()
                            .gap(px(3.))
                            .child(field_label("Hasta"))
                            .child(Input::new(&self.editor_last)),
                    ),
            )
            .child(
                div()
                    .w_full()
                    .min_w_0()
                    .overflow_hidden()
                    .whitespace_nowrap()
                    .text_ellipsis()
                    .child(label(summary)),
            );

        let config_card = card()
            .w_full()
            .min_w_0()
            .gap(px(8.))
            .child(section("Configuración editorial"))
            .child(
                div()
                    .w_full()
                    .grid()
                    .grid_cols(2)
                    .gap(px(8.))
                    .child(
                        button(
                            "editor-mode",
                            if options.mode == "captions" {
                                "Modo: Subtítulos"
                            } else {
                                "Modo: Énfasis"
                            },
                            busy,
                        )
                        .w_full()
                        .on_click(cx.listener(|this, _, _, cx| {
                            this.editor_options.mode = if this.editor_options.mode == "captions" {
                                "highlights"
                            } else {
                                "captions"
                            }
                            .into();
                            this.persist_editor_preferences(cx);
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
                        .w_full()
                        .on_click(cx.listener(|this, _, _, cx| {
                            this.editor_options.format =
                                match this.editor_options.format.as_str() {
                                    "auto" => "horizontal",
                                    "horizontal" => "vertical",
                                    _ => "auto",
                                }
                                .into();
                            this.persist_editor_preferences(cx);
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
                        .w_full()
                        .on_click(cx.listener(|this, _, _, cx| {
                            this.editor_options.density =
                                match this.editor_options.density.as_str() {
                                    "balanced" => "dense",
                                    "dense" => "sparse",
                                    _ => "balanced",
                                }
                                .into();
                            this.persist_editor_preferences(cx);
                            cx.notify();
                        })),
                    )
                    .child(
                        button(
                            "editor-tracks",
                            format!(
                                "Pistas: {}",
                                match options.track_mode.as_str() {
                                    "single" => "1 capa",
                                    "dual" => "2 capas",
                                    _ => "3 capas",
                                }
                            ),
                            busy,
                        )
                        .w_full()
                        .on_click(cx.listener(|this, _, _, cx| {
                            this.editor_options.track_mode =
                                match this.editor_options.track_mode.as_str() {
                                    "triple" => "single",
                                    "single" => "dual",
                                    _ => "triple",
                                }
                                .into();
                            this.persist_editor_preferences(cx);
                            cx.notify();
                        })),
                    )
                    .child(
                        button(
                            "editor-batch-size",
                            format!(
                                "Tanda: {}",
                                match self.editor_batch_size.as_str() {
                                    "50" => "50",
                                    "100" => "100",
                                    "500" => "500",
                                    "all" => "Todo",
                                    _ => "20",
                                }
                            ),
                            busy,
                        )
                        .w_full()
                        .on_click(cx.listener(|this, _, _, cx| {
                            this.editor_batch_size = match this.editor_batch_size.as_str() {
                                "20" => "50",
                                "50" => "100",
                                "100" => "500",
                                "500" => "all",
                                _ => "20",
                            }
                            .into();
                            this.persist_editor_preferences(cx);
                            cx.notify();
                        })),
                    )
                    .child(
                        button("open-saved-proposal", "Abrir JSON", busy)
                            .w_full()
                            .on_click(cx.listener(|this, _, w, cx| this.open_proposal(w, cx))),
                    ),
            );

        let capture_card = card()
            .w_full()
            .min_w_0()
            .justify_between()
            .gap(px(8.))
            .child(
                row()
                    .w_full()
                    .justify_between()
                    .gap(px(6.))
                    .child(section("Captura en Resolve o SRT"))
                    .child(button("check-resolve", "Conexión", busy).on_click(
                        cx.listener(|this, _, window, cx| this.check_resolve(window, cx)),
                    )),
            )
            .child(
                div()
                    .w_full()
                    .grid()
                    .grid_cols(2)
                    .gap(px(8.))
                    .child(
                        accent_button("capture-resolve", "Capturar Resolve", busy)
                            .w_full()
                            .on_click(cx.listener(|this, _, window, cx| this.capture(window, cx))),
                    )
                    .child(
                        button("capture-full", "Pista completa", busy)
                            .w_full()
                            .on_click(
                                cx.listener(|this, _, window, cx| this.capture_full(window, cx)),
                            ),
                    ),
            )
            .child(
                div()
                    .w_full()
                    .grid()
                    .grid_cols(3)
                    .gap(px(6.))
                    .child(
                        button("prev-range", "◀ Ant.", busy)
                            .w_full()
                            .on_click(cx.listener(|this, _, window, cx| {
                                this.shift_capture_range(false, window, cx)
                            })),
                    )
                    .child(
                        button("next-range", "Sig. ▶", busy)
                            .w_full()
                            .on_click(cx.listener(|this, _, window, cx| {
                                this.shift_capture_range(true, window, cx)
                            })),
                    )
                    .child(
                        button("open-srt", "Cargar SRT", busy).w_full().on_click(
                            cx.listener(|this, _, window, cx| this.choose_srt(window, cx)),
                        ),
                    ),
            );

        let top_grid = div()
            .w_full()
            .grid()
            .grid_cols(3)
            .gap(px(10.))
            .child(capture_card)
            .child(source_card)
            .child(config_card);

        let view = column()
            .size_full()
            .min_h_0()
            .gap(px(8.))
            .child(self.stage_chips(cx))
            .child(top_grid)
            .child(
                card()
                    .w_full()
                    .py(px(8.))
                    .px(px(12.))
                    .child(Input::new(&self.editor_direction)),
            );
        if count == 0 {
            return view.child(
                card()
                    .flex_1()
                    .items_center()
                    .justify_center()
                    .gap(px(10.))
                    .p(px(36.))
                    .child(
                        Icon::new(IconName::Captions)
                            .size(px(32.))
                            .text_color(rgb(palette().accent_fg)),
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
                .justify_between()
                .child(
                    row()
                        .gap(px(6.))
                        .child(
                            accent_button("prepare-batch", "Generar tanda", busy).on_click(
                                cx.listener(|this, _, w, cx| {
                                    this.prepare_proposal_with(ProposalMode::BatchNext, w, cx)
                                }),
                            ),
                        )
                        .child(button("prepare-ai", "Proponer todo con IA", busy).on_click(
                            cx.listener(|this, _, w, cx| {
                                this.prepare_proposal_with(ProposalMode::Ai, w, cx)
                            }),
                        ))
                        .child(button("prepare-decisions", "Decisiones", busy).on_click(
                            cx.listener(|this, _, w, cx| {
                                this.prepare_proposal_with(ProposalMode::Decisions, w, cx)
                            }),
                        ))
                        .child(button("prepare-direct", "Revisión directa", busy).on_click(
                            cx.listener(|this, _, w, cx| {
                                this.prepare_proposal_with(ProposalMode::Direct, w, cx)
                            }),
                        ))
                        .child(
                            button("open-proposal", "Abrir JSON", busy)
                                .on_click(cx.listener(|this, _, w, cx| this.open_proposal(w, cx))),
                        ),
                )
                .child(
                    row()
                        .gap(px(6.))
                        .child(
                            button(
                                "apply-direct-stage1",
                                "Aplicar revisión",
                                busy || self.proposal.is_none(),
                            )
                            .on_click(cx.listener(|this, _, w, cx| this.apply_proposal(w, cx))),
                        )
                        .child(
                            button(
                                "undo-stage1",
                                "Deshacer",
                                busy || self.last_application.is_none(),
                            )
                            .on_click(cx.listener(|this, _, w, cx| this.undo_application(w, cx))),
                        )
                        .child(
                            button("clean-df-stage1", "Limpiar pistas DF", busy).on_click(
                                cx.listener(|this, _, w, cx| this.clean_df_tracks(w, cx)),
                            ),
                        ),
                ),
        )
        .child(self.editor_table(cx))
    }
}
