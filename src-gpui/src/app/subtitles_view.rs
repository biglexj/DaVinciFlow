//! Pestaña «Corrección»: mesa de subtítulos con herramientas de la interfaz vigente.
use super::*;
use gpui_kit::component::Icon;
use gpui_kit::component::checkbox::Checkbox;

impl FlowApp {
    fn subtitles_table(&self, cx: &mut Context<Self>) -> Div {
        let entity = cx.entity().downgrade();
        let rows = uniform_list(
            "subtitle-table",
            self.filtered_cues.len(),
            move |range, _, cx| {
                let Some(entity) = entity.upgrade() else {
                    return vec![];
                };
                let this = entity.read(cx);
                range
                    .filter_map(|position| this.filtered_cues.get(position).copied())
                    .map(|index| {
                        let cue = &this.session.document().cues[index];
                        let selected = this.session.selected() == Some(index);
                        let modified = cue.changed();
                        let weak = entity.downgrade();
                        row()
                            .id(("cue", index))
                            .role(Role::Button)
                            .focusable()
                            .tab_index(0)
                            .aria_label(format!("Subtítulo {}: {}", index + 1, cue.text))
                            .w_full()
                            .h(px(44.))
                            .px(px(14.))
                            .gap(px(16.))
                            .border_b_1()
                            .border_color(rgb(LINE))
                            .bg(rgb(if selected { ACTIVE } else { CARD }))
                            .cursor_pointer()
                            .hover(|item| item.bg(rgb(HEADING)))
                            .child(
                                div()
                                    .w(px(40.))
                                    .text_color(rgb(MUTED))
                                    .child(format!("{}", index + 1)),
                            )
                            .child(
                                div()
                                    .w(px(120.))
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
                                    .text_color(rgb(MUTED))
                                    .child(cue.original.clone()),
                            )
                            .child(
                                div()
                                    .flex_1()
                                    .min_w_0()
                                    .text_ellipsis()
                                    .text_color(rgb(if modified { TEXT } else { MUTED }))
                                    .child(cue.text.clone()),
                            )
                            .child(div().w(px(100.)).child(chip(
                                if modified { "Modificado" } else { "Original" },
                                modified,
                            )))
                            .on_click({
                                let weak = weak.clone();
                                move |_, window, cx| {
                                    if let Some(entity) = weak.upgrade() {
                                        entity.update(cx, |this, cx| {
                                            if this.busy {
                                                return;
                                            }
                                            this.select_cue(index, window, cx);
                                        });
                                    }
                                }
                            })
                            .on_key_down({
                                let weak = weak.clone();
                                move |event: &KeyDownEvent, window, cx| {
                                    if matches!(event.keystroke.key.as_str(), "enter" | "space")
                                        && let Some(entity) = weak.upgrade()
                                    {
                                        entity.update(cx, |this, cx| {
                                            if !this.busy {
                                                this.select_cue(index, window, cx);
                                            }
                                        });
                                    }
                                }
                            })
                    })
                    .collect::<Vec<_>>()
            },
        );
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
                    .child(div().w(px(40.)).child(label("#")))
                    .child(div().w(px(120.)).child(label("Tiempo")))
                    .child(div().flex_1().min_w_0().child(label("Texto Original")))
                    .child(div().flex_1().min_w_0().child(label("Texto Corregido")))
                    .child(div().w(px(100.)).child(label("Estado"))),
            )
            .child(div().flex_1().min_h_0().child(rows.h_full()))
    }

    fn subtitles_editor_card(&self, index: usize, cx: &mut Context<Self>) -> Div {
        let cue = &self.session.document().cues[index];
        let draft = self.session.has_draft();
        card()
            .gap(px(8.))
            .child(
                row()
                    .justify_between()
                    .gap(px(10.))
                    .child(
                        div()
                            .text_size(px(14.))
                            .font_weight(FontWeight::SEMIBOLD)
                            .child("Edición de subtítulo"),
                    )
                    .child(label(format!(
                        "#{} | {} a {}",
                        index + 1,
                        subtitles::timecode(cue.start_ms),
                        subtitles::timecode(cue.end_ms)
                    ))),
            )
            .child(
                div()
                    .text_size(px(12.))
                    .text_color(rgb(MUTED))
                    .text_ellipsis()
                    .child(format!("Original: {}", cue.original)),
            )
            .child(Textarea::new(&self.edit).h(px(72.)).disabled(self.busy))
            .child(
                row()
                    .gap(px(8.))
                    .child(
                        accent_button("save-edit", "Guardar cambio", self.busy || !draft).on_click(
                            cx.listener(|this, _, window, cx| this.save_edit(window, cx)),
                        ),
                    )
                    .child(
                        button("next-cue", "Siguiente subtítulo", self.busy)
                            .on_click(cx.listener(|this, _, window, cx| this.next_cue(window, cx))),
                    )
                    .child(
                        button(
                            "restore-cue",
                            "Restaurar original",
                            self.busy || !cue.changed(),
                        )
                        .on_click(cx.listener(
                            move |this, _, window, cx| this.restore_cue(index, window, cx),
                        )),
                    )
                    .child(button("close-editor", "Cerrar", self.busy).on_click(
                        cx.listener(|this, _, window, cx| this.discard_edit(window, cx)),
                    )),
            )
    }

    pub fn subtitles_view(&self, cx: &mut Context<Self>) -> Div {
        let document = self.session.document();
        let total = document.cues.len();
        let changed = document.changed();
        let has_cues = total > 0;
        let draft = self.session.has_draft();
        let busy = self.busy;
        let disabled = busy || !has_cues;

        let summary = if has_cues {
            format!(
                "{} · {} subtítulos",
                if document.source.is_empty() {
                    "SRT".to_string()
                } else {
                    document.source.clone()
                },
                total
            )
        } else {
            "Captura subtítulos de Resolve o carga un SRT para comenzar.".to_string()
        };

        let mut view = column()
            .size_full()
            .min_h_0()
            .gap(px(10.))
            .child(
                card().gap(px(6.)).child(
                    row()
                        .justify_between()
                        .gap(px(10.))
                        .child(
                            div()
                                .flex_1()
                                .min_w_0()
                                .text_size(px(12.))
                                .text_color(rgb(MUTED))
                                .child(summary),
                        )
                        .child(
                            row()
                                .gap(px(8.))
                                .child(
                                    accent_button("sync-editor", "Actualizar en Editor", disabled)
                                        .on_click(
                                            cx.listener(|this, _, _, cx| this.sync_to_editor(cx)),
                                        ),
                                )
                                .child(
                                    button("export-srt", "Exportar SRT", disabled || draft)
                                        .on_click(cx.listener(|this, _, window, cx| {
                                            this.export(window, cx)
                                        })),
                                )
                                .child(
                                    button("reload-resolve", "Recargar de Resolve", busy).on_click(
                                        cx.listener(|this, _, window, cx| this.capture(window, cx)),
                                    ),
                                ),
                        ),
                ),
            )
            .child(
                card()
                    .gap(px(10.))
                    .child(
                        row()
                            .justify_between()
                            .child(section("Herramientas Rápidas de Corrección"))
                            .child(
                                row()
                                    .gap(px(8.))
                                    .child(
                                        button(
                                            "toggle-ai-panel",
                                            if self.ai_panel_open {
                                                "Ocultar panel IA / Guion"
                                            } else {
                                                "Alternar panel IA / Guion"
                                            },
                                            busy,
                                        )
                                        .on_click(
                                            cx.listener(|this, _, _, cx| this.toggle_ai_panel(cx)),
                                        ),
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
                            .gap(px(8.))
                            .items_start()
                            .child(
                                column()
                                    .w(px(200.))
                                    .gap(px(4.))
                                    .child(field_label("Buscar texto"))
                                    .child(Input::new(&self.find)),
                            )
                            .child(
                                column()
                                    .w(px(200.))
                                    .gap(px(4.))
                                    .child(field_label("Reemplazar por"))
                                    .child(Input::new(&self.replacement)),
                            )
                            .child(
                                Checkbox::new("match-case")
                                    .label("Mayús/minús")
                                    .checked(self.case_sensitive)
                                    .on_click(cx.listener(|this, checked: &bool, _, cx| {
                                        this.case_sensitive = *checked;
                                        cx.notify();
                                    })),
                            )
                            .child(
                                accent_button("replace-all", "Reemplazar todo", disabled || draft)
                                    .on_click(
                                        cx.listener(|this, _, window, cx| this.replace(window, cx)),
                                    ),
                            )
                            .child(
                                button("normalize", "Normalizar ortografía", disabled || draft)
                                    .on_click(cx.listener(|this, _, window, cx| {
                                        this.normalize(window, cx)
                                    })),
                            ),
                    )
                    .child(
                        row()
                            .gap(px(8.))
                            .items_start()
                            .child(
                                column()
                                    .flex_1()
                                    .gap(px(4.))
                                    .child(field_label("Glosario rápido"))
                                    .child(Textarea::new(&self.glossary).h(px(58.))),
                            )
                            .child(
                                button("apply-glossary", "Aplicar glosario", disabled || draft)
                                    .on_click(cx.listener(|this, _, window, cx| {
                                        this.apply_glossary(window, cx)
                                    })),
                            ),
                    )
                    .when(self.ai_panel_open, |panel| {
                        panel.child(
                            column()
                                .gap(px(8.))
                                .p(px(12.))
                                .bg(rgb(0x152220))
                                .border_1()
                                .border_color(rgb(0x264A43))
                                .rounded(px(8.))
                                .child(
                                    row()
                                        .justify_between()
                                        .child(section(
                                            "Alineación semántica y corrección con IA (Gemini)",
                                        ))
                                        .child(
                                            Checkbox::new("detect-markers")
                                                .label(
                                                    "Detectar marcadores clave en línea de tiempo",
                                                )
                                                .checked(self.ai_detect_markers)
                                                .on_click(cx.listener(
                                                    |this, checked: &bool, _, cx| {
                                                        this.ai_detect_markers = *checked;
                                                        cx.notify();
                                                    },
                                                )),
                                        ),
                                )
                                .child(
                                    column()
                                        .gap(px(4.))
                                        .child(field_label(
                                            "Guion de referencia (opcional para IA)",
                                        ))
                                        .child(Textarea::new(&self.ai_script).h(px(72.))),
                                )
                                .child(
                                    row()
                                        .gap(px(8.))
                                        .child(
                                            accent_button(
                                                "align-with-ai",
                                                "Iniciar corrección con IA",
                                                disabled || draft,
                                            )
                                            .on_click(
                                                cx.listener(|this, _, window, cx| {
                                                    this.align_with_ai(window, cx)
                                                }),
                                            ),
                                        )
                                        .child(
                                            button(
                                                "insert-markers",
                                                "Insertar marcadores en Resolve",
                                                busy || self.ai_markers.is_empty()
                                                    || self.ai_snapshot.is_none(),
                                            )
                                            .on_click(
                                                cx.listener(|this, _, window, cx| {
                                                    this.insert_ai_markers(window, cx)
                                                }),
                                            ),
                                        ),
                                )
                                .when(!self.ai_markers.is_empty(), |panel| {
                                    panel.child(label(format!(
                                        "{} marcador(es) listos para insertar: {}",
                                        self.ai_markers.len(),
                                        self.ai_markers
                                            .iter()
                                            .map(|marker| marker.name.clone())
                                            .collect::<Vec<_>>()
                                            .join(", ")
                                    )))
                                }),
                        )
                    }),
            )
            .child(
                row()
                    .justify_between()
                    .child(label(format!(
                        "{total} subtítulos en total · {changed} corregidos"
                    )))
                    .child(
                        row()
                            .gap(px(8.))
                            .child(
                                button(
                                    "undo-text",
                                    "Deshacer",
                                    disabled || draft || !self.session.can_undo(),
                                )
                                .on_click(cx.listener(
                                    |this, _, window, cx| this.history(false, window, cx),
                                )),
                            )
                            .child(
                                button(
                                    "redo-text",
                                    "Rehacer",
                                    disabled || draft || !self.session.can_redo(),
                                )
                                .on_click(
                                    cx.listener(|this, _, window, cx| {
                                        this.history(true, window, cx)
                                    }),
                                ),
                            ),
                    ),
            );

        if let Some(index) = self.session.selected() {
            view = view.child(self.subtitles_editor_card(index, cx));
        }

        if !has_cues {
            return view.child(
                card()
                    .items_center()
                    .gap(px(10.))
                    .p(px(36.))
                    .child(
                        Icon::new(IconName::SpellCheck)
                            .size(px(32.))
                            .text_color(rgb(ACCENT)),
                    )
                    .child(
                        div()
                            .text_size(px(17.))
                            .font_weight(FontWeight::MEDIUM)
                            .child("Mesa de corrección de subtítulos"),
                    )
                    .child(label(
                        "Revisa, normaliza ortografía y busca y reemplaza términos sobre la mesa.",
                    )),
            );
        }
        view.child(self.subtitles_table(cx))
    }
}
