use super::*;

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
                        row()
                            .id(("review", index))
                            .role(Role::Button)
                            .aria_label(format!("Revisar bloque {}", index + 1))
                            .w_full()
                            .h(px(50.))
                            .px_3()
                            .gap_3()
                            .bg(rgb(if index == this.review_selected {
                                ACTIVE
                            } else {
                                CARD
                            }))
                            .cursor_pointer()
                            .child(label(format!("{}", index + 1)))
                            .child(
                                div()
                                    .flex_1()
                                    .min_w_0()
                                    .text_ellipsis()
                                    .child(d.main.clone()),
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
        let mut view = column().size_full().min_h_0().gap_3().child(
            row()
                .justify_between()
                .child(label(format!(
                    "{} de {} revisados · {}",
                    proposal.reviewed(),
                    proposal.decisions.len(),
                    proposal.model
                )))
                .child(
                    row()
                        .child(
                            button("save-proposal", "Guardar JSON", self.busy)
                                .on_click(cx.listener(|this, _, w, cx| this.save_proposal(w, cx))),
                        )
                        .child(
                            button("approve-all", "Marcar todos revisados", self.busy).on_click(
                                cx.listener(|this, _, _, cx| this.review_approve_all(cx)),
                            ),
                        ),
                ),
        );
        if self.editor_stage == 3 {
            return view.child(card().gap_3().child(section("Aplicación en Resolve"))
                .child(label("Se comprobará la identidad del montaje y la revisión de todos los bloques antes de escribir."))
                .child(row().child(accent_button("apply-proposal","Aplicar propuesta revisada",self.busy||proposal.validate(true).is_err())
                    .on_click(cx.listener(|this,_,w,cx|this.apply_proposal(w,cx))))
                    .child(button("undo-application","Deshacer última ejecución",self.busy||self.last_application.is_none()).on_click(cx.listener(|this,_,w,cx|this.undo_application(w,cx))))));
        }
        let mut form = column()
            .w(px(320.))
            .flex_shrink_0()
            .gap_2()
            .child(section(format!("Bloque {}", self.review_selected + 1)))
            .child(field_label("Contexto"))
            .child(
                Textarea::new(&self.review_context)
                    .h(px(55.))
                    .disabled(self.busy),
            )
            .child(field_label("Principal"))
            .child(
                Textarea::new(&self.review_main)
                    .h(px(72.))
                    .disabled(self.busy),
            )
            .child(field_label("Énfasis"))
            .child(
                Textarea::new(&self.review_accent)
                    .h(px(55.))
                    .disabled(self.busy),
            )
            .child(Input::new(&self.review_note).disabled(self.busy));
        for layer in ["context", "main", "accent"] {
            let name = self
                .review_templates
                .get(layer)
                .and_then(|id| proposal.templates.iter().find(|t| &t.id == id))
                .map(|t| t.name.as_str())
                .unwrap_or("Elegir plantilla");
            form = form.child(
                button(
                    format!("template-{layer}"),
                    format!("{layer}: {name}"),
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
                .max_h(px(180.))
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
        form = form.child(
            row()
                .child(
                    button(
                        "enabled-decision",
                        if self.review_enabled {
                            "Incluir bloque"
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
