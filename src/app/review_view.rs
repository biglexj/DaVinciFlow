use super::*;

fn layer_label(layer: &str) -> &'static str {
    match layer {
        "context" => "Contexto",
        "main" => "Principal",
        "accent" => "Énfasis",
        _ => "Capa",
    }
}

impl FlowApp {
    pub(super) fn review_view(&self, cx: &mut Context<Self>) -> Div {
        let Some(proposal) = &self.proposal else {
            return column().child(label(
                "Prepara una propuesta desde el montaje o abre una revisión guardada.",
            ));
        };
        let entity = cx.entity().downgrade();
        let list = uniform_list(
            "review-list",
            proposal.decisions.len(),
            move |range, _, cx| {
                let Some(entity) = entity.upgrade() else {
                    return vec![];
                };
                let this = entity.read(cx);
                range
                    .filter_map(|i| this.proposal.as_ref()?.decisions.get(i).map(|d| (i, d)))
                    .map(|(index, d)| {
                        let has_conflict = this.conflicts.iter().any(|c| c.cue_index == index);
                        let row_bg = if has_conflict {
                            0x3B1818
                        } else if index == this.review_selected {
                            ACTIVE
                        } else {
                            CARD
                        };
                        row()
                            .id(("review", index))
                            .role(Role::Button)
                            .aria_label(format!("Revisar bloque {}", index + 1))
                            .w_full()
                            .h(px(46.))
                            .px_3()
                            .gap_3()
                            .bg(rgb(row_bg))
                            .cursor_pointer()
                            .child(label(format!(
                                "{}{}",
                                if has_conflict { "⚠️ " } else { "" },
                                index + 1
                            )))
                            .child(
                                div()
                                    .flex_1()
                                    .min_w_0()
                                    .text_ellipsis()
                                    .text_color(rgb(if d.enabled { TEXT } else { MUTED }))
                                    .child(if d.enabled {
                                        d.main.clone()
                                    } else {
                                        format!("(Excluido) {}", d.main)
                                    }),
                            )
                            .child(chip(
                                if d.reviewed { "Revisado" } else { "Pendiente" },
                                d.reviewed,
                            ))
                            .on_click({
                                let weak = entity.downgrade();
                                move |_, w, cx| {
                                    if let Some(e) = weak.upgrade() {
                                        e.update(cx, |this, cx| this.select_review(index, w, cx));
                                    }
                                }
                            })
                    })
                    .collect::<Vec<_>>()
            },
        )
        .w_full()
        .flex_1()
        .min_h_0();

        let active_count = proposal.decisions.iter().filter(|d| d.enabled).count();
        let batch_label = if self.batch_total > 0 {
            let next_str = self
                .batch_next
                .map(|n| format!(" · siguiente #{n}"))
                .unwrap_or_else(|| " · secuencia completa".into());
            format!(
                " · Tandas: {}/{}{next_str}",
                self.batch_processed, self.batch_total
            )
        } else {
            String::new()
        };

        let mut view = column().size_full().min_h_0().gap_2().child(
            row()
                .justify_between()
                .child(label(format!(
                    "{active_count} rótulos · {} de {} revisados · {}{batch_label}",
                    proposal.reviewed(),
                    proposal.decisions.len(),
                    proposal.model
                )))
                .child(
                    row()
                        .gap(px(6.))
                        .child(
                            button("save-proposal", "Guardar JSON", self.busy)
                                .on_click(cx.listener(|this, _, w, cx| this.save_proposal(w, cx))),
                        )
                        .child(
                            button("approve-all", "Aprobar todo", self.busy).on_click(
                                cx.listener(|this, _, _, cx| this.review_approve_all(cx)),
                            ),
                        )
                        .child(
                            accent_button("apply-top", "Aplicar revisión", self.busy)
                                .on_click(cx.listener(|this, _, w, cx| this.apply_proposal(w, cx))),
                        )
                        .child(
                            button(
                                "undo-top",
                                "Deshacer",
                                self.busy || self.last_application.is_none(),
                            )
                            .on_click(cx.listener(|this, _, w, cx| this.undo_application(w, cx))),
                        )
                        .child(
                            button("clean-top", "Limpiar pistas DF", self.busy).on_click(
                                cx.listener(|this, _, w, cx| this.clean_df_tracks(w, cx)),
                            ),
                        ),
                ),
        );

        if !self.conflicts.is_empty() {
            let summary = self
                .conflicts
                .iter()
                .take(3)
                .map(|c| {
                    format!(
                        "• Pista {} (#{}): clip '{}' [{:.0}–{:.0}] choca con subtítulo #{}",
                        c.track_name,
                        c.track_index,
                        c.clip_name,
                        c.start_frame,
                        c.end_frame,
                        c.cue_index + 1
                    )
                })
                .collect::<Vec<_>>()
                .join("\n");
            view = view.child(
                card()
                    .bg(rgb(0x3B1818))
                    .border_color(rgb(ERROR))
                    .gap(px(6.))
                    .child(section(format!(
                        "⚠️ Conflicto en la línea de tiempo ({} colisiones)",
                        self.conflicts.len()
                    )))
                    .child(
                        div()
                            .text_size(px(12.))
                            .text_color(rgb(TEXT))
                            .child(summary),
                    )
                    .child(
                        row()
                            .gap(px(8.))
                            .child(
                                accent_button("clean-and-retry", "Limpiar pistas DF", self.busy)
                                    .on_click(
                                        cx.listener(|this, _, w, cx| this.clean_df_tracks(w, cx)),
                                    ),
                            )
                            .child(
                                button("dismiss-conflicts", "Ocultar aviso", self.busy).on_click(
                                    cx.listener(|this, _, _, cx| {
                                        this.conflicts.clear();
                                        cx.notify();
                                    }),
                                ),
                            ),
                    ),
            );
        }

        if self.editor_stage == 3 {
            return view.child(
                card()
                    .gap_3()
                    .child(section("Aplicación en Resolve"))
                    .child(label(
                        "Se comprobará la identidad del montaje y la revisión de todos los bloques antes de escribir en las pistas de DaVinci Flow.",
                    ))
                    .child(
                        row()
                            .gap(px(8.))
                            .child(
                                accent_button(
                                    "apply-proposal",
                                    "Aplicar propuesta revisada",
                                    self.busy,
                                )
                                .on_click(cx.listener(|this, _, w, cx| this.apply_proposal(w, cx))),
                            )
                            .child(
                                button(
                                    "undo-application",
                                    "Deshacer última ejecución",
                                    self.busy || self.last_application.is_none(),
                                )
                                .on_click(cx.listener(|this, _, w, cx| {
                                    this.undo_application(w, cx)
                                })),
                            )
                            .child(
                                button("clean-stage3", "Limpiar pistas DF", self.busy).on_click(
                                    cx.listener(|this, _, w, cx| this.clean_df_tracks(w, cx)),
                                ),
                            ),
                    ),
            );
        }

        let current_decision = proposal.decisions.get(self.review_selected);
        let original_text = proposal.snapshot["cues"]
            .get(self.review_selected)
            .and_then(|c| c["text"].as_str())
            .unwrap_or_default()
            .to_owned();
        let reason_text = current_decision
            .map(|d| d.reason.clone())
            .unwrap_or_default();
        let visual_text = current_decision
            .map(|d| d.visual_note.clone())
            .unwrap_or_default();

        let track_mode = self.editor_options.track_mode.as_str();
        let show_context = track_mode == "triple";
        let show_accent = track_mode != "single";

        let mut form = column()
            .w(px(360.))
            .flex_shrink_0()
            .gap(px(6.))
            .child(
                row()
                    .justify_between()
                    .child(section(format!(
                        "Revisar composición · Bloque #{}",
                        self.review_selected + 1
                    )))
                    .child(
                        button("back-stage1", "Cerrar", self.busy).on_click(cx.listener(
                            |this, _, _, cx| {
                                this.editor_stage = 1;
                                cx.notify();
                            },
                        )),
                    ),
            )
            .child(
                div()
                    .text_size(px(11.5))
                    .text_color(rgb(TEXT))
                    .child(format!("Original: {original_text}")),
            )
            .when(!reason_text.is_empty(), |col| {
                col.child(label(format!("Motivo: {reason_text}")))
            })
            .when(!visual_text.is_empty(), |col| {
                col.child(label(format!("Imagen sugerida: {visual_text}")))
            });

        if show_context {
            form = form.child(field_label("Contexto")).child(
                Textarea::new(&self.review_context)
                    .h(px(48.))
                    .disabled(self.busy),
            );
        }
        form = form.child(field_label("Principal")).child(
            Textarea::new(&self.review_main)
                .h(px(64.))
                .disabled(self.busy),
        );
        if show_accent {
            form = form.child(field_label("Énfasis")).child(
                Textarea::new(&self.review_accent)
                    .h(px(48.))
                    .disabled(self.busy),
            );
        }

        form = form
            .child(field_label("Nota si reescribes el original"))
            .child(Input::new(&self.review_note).disabled(self.busy));

        let active_layers: &[&str] = match track_mode {
            "single" => &["main"],
            "dual" => &["main", "accent"],
            _ => &["context", "main", "accent"],
        };

        for &layer in active_layers {
            let name = self
                .review_templates
                .get(layer)
                .and_then(|id| proposal.templates.iter().find(|t| &t.id == id))
                .map(|t| t.name.as_str())
                .unwrap_or("Elegir plantilla");
            let l_label = layer_label(layer);
            form = form.child(
                button(
                    format!("template-{layer}"),
                    format!("Plantilla ({l_label}): {name}"),
                    self.busy,
                )
                .w_full()
                .on_click(cx.listener(move |this, _, _, cx| this.cycle_review_template(layer, cx))),
            );
        }

        if let Some(layer) = self.review_template_layer.clone() {
            let query = self.template_filter.read(cx).value().to_lowercase();
            let choices = proposal
                .templates
                .iter()
                .filter(|t| query.is_empty() || t.name.to_lowercase().contains(&query))
                .collect::<Vec<_>>();
            let mut picker = column()
                .id("template-choices")
                .max_h(px(150.))
                .overflow_y_scroll()
                .gap_1();
            for template in choices.iter().take(60) {
                let id = template.id.clone();
                let layer = layer.clone();
                picker = picker.child(
                    button(
                        format!("choose-template-{}", template.id),
                        template.name.clone(),
                        self.busy,
                    )
                    .w_full()
                    .on_click(cx.listener(move |this, _, _, cx| {
                        this.review_templates.insert(layer.clone(), id.clone());
                        this.review_template_layer = None;
                        cx.notify();
                    })),
                );
            }
            form = form
                .child(Input::new(&self.template_filter))
                .child(label(format!(
                    "{} coincidencias · mostrando hasta 60",
                    choices.len()
                )))
                .child(picker);
        }

        // Selector de recurso (SFX / B-Roll)
        let sfx_display = if self.review_sfx.is_empty() {
            "(Sin recurso)".to_string()
        } else {
            self.user_sfx_resources
                .iter()
                .find(|r| r.id == self.review_sfx)
                .map(|r| format!("{} (SFX)", r.name))
                .or_else(|| {
                    self.user_broll_resources
                        .iter()
                        .find(|r| r.id == self.review_sfx)
                        .map(|r| format!("{} (B-Roll)", r.name))
                })
                .or_else(|| {
                    proposal
                        .options
                        .as_ref()
                        .and_then(|opts| {
                            opts.resources.iter().find(|r| {
                                r.get("id").and_then(Value::as_str)
                                    == Some(self.review_sfx.as_str())
                            })
                        })
                        .and_then(|r| {
                            let name = r.get("name").and_then(Value::as_str)?;
                            let suffix = match r.get("category").and_then(Value::as_str) {
                                Some("visuals") => "B-Roll",
                                _ => "SFX",
                            };
                            Some(format!("{name} ({suffix})"))
                        })
                })
                .or_else(|| {
                    self.sfx_assets
                        .iter()
                        .find(|a| a.id == self.review_sfx)
                        .map(|a| format!("{} ({})", a.name, a.category))
                })
                .unwrap_or_else(|| self.review_sfx.clone())
        };
        form = form.child(
            button(
                "review-sfx-toggle",
                format!("Recurso (SFX / B-Roll): {sfx_display}"),
                self.busy,
            )
            .w_full()
            .on_click(cx.listener(|this, _, window, cx| {
                this.review_sfx_open = !this.review_sfx_open;
                if this.review_sfx_open {
                    if this.sfx_assets.is_empty() {
                        this.load_sfx_catalog(window, cx);
                    }
                    let sfx_folders = this.preferences.folders_for("sfx");
                    this.user_sfx_resources =
                        library::scan_category("sfx", &sfx_folders, 500).resources;
                    let broll_folders = this.preferences.folders_for("visuals");
                    this.user_broll_resources =
                        library::scan_category("visuals", &broll_folders, 500).resources;
                }
                cx.notify();
            })),
        );
        if self.review_sfx_open {
            let mut sfx_list = column()
                .id("review-sfx-choices")
                .max_h(px(160.))
                .overflow_y_scroll()
                .gap_1()
                .child(
                    button("sfx-choice-none", "(Sin recurso)", self.busy)
                        .w_full()
                        .on_click(cx.listener(|this, _, _, cx| {
                            this.review_sfx.clear();
                            this.review_sfx_open = false;
                            cx.notify();
                        })),
                );
            for res in &self.user_sfx_resources {
                let id = res.id.clone();
                sfx_list = sfx_list.child(
                    button(
                        format!("sfx-user-{id}"),
                        format!("{} (SFX)", res.name),
                        self.busy,
                    )
                    .w_full()
                    .on_click(cx.listener(move |this, _, _, cx| {
                        this.review_sfx = id.clone();
                        this.review_sfx_open = false;
                        cx.notify();
                    })),
                );
            }
            for res in &self.user_broll_resources {
                let id = res.id.clone();
                sfx_list = sfx_list.child(
                    button(
                        format!("broll-user-{id}"),
                        format!("{} (B-Roll)", res.name),
                        self.busy,
                    )
                    .w_full()
                    .on_click(cx.listener(move |this, _, _, cx| {
                        this.review_sfx = id.clone();
                        this.review_sfx_open = false;
                        cx.notify();
                    })),
                );
            }
            for asset in &self.sfx_assets {
                let id = asset.id.clone();
                sfx_list = sfx_list.child(
                    button(
                        format!("sfx-choice-{id}"),
                        format!("{} ({})", asset.name, asset.category),
                        self.busy,
                    )
                    .w_full()
                    .on_click(cx.listener(move |this, _, _, cx| {
                        this.review_sfx = id.clone();
                        this.review_sfx_open = false;
                        cx.notify();
                    })),
                );
            }
            form = form.child(sfx_list);
        }

        form = form.child(
            row()
                .gap(px(6.))
                .child(
                    button(
                        "enabled-decision",
                        if self.review_enabled {
                            "✓ Mostrar texto"
                        } else {
                            "Bloque excluido"
                        },
                        self.busy,
                    )
                    .on_click(cx.listener(|this, _, _, cx| {
                        this.review_enabled = !this.review_enabled;
                        cx.notify();
                    })),
                )
                .child(
                    accent_button("save-review", "Guardar revisión", self.busy)
                        .on_click(cx.listener(|this, _, w, cx| this.review_save(w, cx))),
                )
                .child(
                    button("next-review", "Siguiente ▶", self.busy)
                        .on_click(cx.listener(|this, _, w, cx| this.review_next(w, cx))),
                ),
        );

        view = view.child(
            row()
                .flex_1()
                .min_h_0()
                .items_start()
                .gap_4()
                .child(
                    column()
                        .flex_1()
                        .h_full()
                        .min_h_0()
                        .bg(rgb(CARD))
                        .rounded_lg()
                        .child(list),
                )
                .child(
                    div()
                        .id("review-form")
                        .h_full()
                        .overflow_y_scroll()
                        .child(form),
                ),
        );
        view
    }
}
