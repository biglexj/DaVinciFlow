use super::*;

impl FlowApp {
    fn sidebar(&self, cx: &mut Context<Self>) -> Div {
        let entries = [
            (Tab::Subtitles, "01", "Corrección"),
            (Tab::Library, "02", "Biblioteca"),
            (Tab::Resolve, "03", "Conexión"),
        ];
        column()
            .w(px(214.))
            .h_full()
            .flex_shrink_0()
            .bg(rgb(SIDE))
            .p_5()
            .gap_6()
            .child(
                column()
                    .gap_1()
                    .child(
                        div()
                            .text_size(px(22.))
                            .font_weight(FontWeight::BOLD)
                            .child("DaVinci Flow"),
                    )
                    .child(label("ESPACIO DE EDICIÓN")),
            )
            .child(
                column()
                    .id("navigation-tabs")
                    .role(Role::TabList)
                    .aria_label("Navegación principal")
                    .gap_2()
                    .children(entries.into_iter().map(|(tab, number, title)| {
                        let active = self.tab == tab;
                        row()
                            .id(title)
                            .role(Role::Tab)
                            .aria_label(title)
                            .aria_selected(active)
                            .focusable()
                            .tab_index(0)
                            .px_3()
                            .py_3()
                            .rounded_lg()
                            .cursor_pointer()
                            .bg(rgb(if active { 0x193630 } else { SIDE }))
                            .text_color(rgb(if active { ACCENT } else { MUTED }))
                            .hover(|s| s.bg(rgb(CARD)))
                            .child(div().text_size(px(11.)).child(number))
                            .child(div().font_weight(FontWeight::MEDIUM).child(title))
                            .on_click(cx.listener(move |this, _, _, cx| {
                                this.tab = tab;
                                cx.notify();
                            }))
                            .on_key_down(cx.listener(move |this, event: &KeyDownEvent, _, cx| {
                                if matches!(event.keystroke.key.as_str(), "enter" | "space") {
                                    this.tab = tab;
                                    cx.notify();
                                }
                            }))
                    })),
            )
            .child(div().flex_1())
            .child(
                column()
                    .gap_2()
                    .child(label("MIGRACIÓN · DEMO"))
                    .child(
                        div()
                            .text_size(px(12.))
                            .text_color(rgb(ACCENT))
                            .child("Rust + GPUI"),
                    )
                    .child(label("Pestaña por pestaña.")),
            )
    }

    fn subtitles_view(&self, cx: &mut Context<Self>) -> Div {
        let disabled = self.busy || self.session.document().cues.is_empty();
        let draft = self.session.has_draft();
        let entity = cx.entity().downgrade();
        let mut view = column()
            .size_full()
            .min_h_0()
            .gap_4()
            .child(
                row()
                    .justify_between()
                    .child(
                        column()
                            .gap_1()
                            .child(heading("Corrección de subtítulos"))
                            .child(label("Revisa el texto y conserva el ritmo de tu montaje.")),
                    )
                    .child(
                        row()
                            .child(
                                button("open-srt", "Abrir SRT", self.busy)
                                    .on_click(cx.listener(|this, _, w, cx| this.choose_srt(w, cx))),
                            )
                            .child(
                                accent_button("export", "Exportar SRT", disabled || draft)
                                    .on_click(cx.listener(|this, _, w, cx| this.export(w, cx))),
                            ),
                    ),
            )
            .child(
                row()
                    .justify_between()
                    .child(
                        div()
                            .flex_1()
                            .min_w_0()
                            .text_ellipsis()
                            .text_color(rgb(MUTED))
                            .child(if self.session.document().source.is_empty() {
                                "Sin fuente cargada".to_string()
                            } else {
                                self.session.document().source.clone()
                            }),
                    )
                    .child(
                        button("capture", "Leer de Resolve", self.busy)
                            .on_click(cx.listener(|this, _, w, cx| this.capture(w, cx))),
                    ),
            );
        if self.session.document().cues.is_empty() {
            return view.child(empty(
                "Tu transcripción, lista para revisar",
                "Abre un archivo SRT o lee la pista de subtítulos de Resolve.",
            ));
        }
        view = view.child(
            panel()
                .gap_3()
                .child(
                    row()
                        .child(div().flex_1().child(Input::new(&self.find)))
                        .child(div().flex_1().child(Input::new(&self.replacement)))
                        .child(
                            button(
                                "case",
                                if self.case_sensitive {
                                    "Aa: exacto"
                                } else {
                                    "Aa: ignorar"
                                },
                                disabled || draft,
                            )
                            .on_click(cx.listener(|this, _, _, cx| {
                                this.case_sensitive = !this.case_sensitive;
                                cx.notify();
                            })),
                        )
                        .child(
                            button("replace", "Reemplazar", disabled || draft)
                                .on_click(cx.listener(|this, _, w, cx| this.replace(w, cx))),
                        ),
                )
                .child(
                    row()
                        .child(div().flex_1().child(Input::new(&self.filter)))
                        .child(
                            button("normalize", "Normalizar espacios", disabled || draft)
                                .on_click(cx.listener(|this, _, w, cx| this.normalize(w, cx))),
                        )
                        .child(
                            button("restore-all", "Restaurar todo", disabled || draft)
                                .on_click(cx.listener(|this, _, w, cx| this.restore_all(w, cx))),
                        ),
                ),
        );
        let list = uniform_list(
            "subtitle-list",
            self.filtered_cues.len(),
            move |range, _, cx| {
                let Some(entity) = entity.upgrade() else {
                    return vec![];
                };
                let this = entity.read(cx);
                range
                    .filter_map(|i| this.filtered_cues.get(i).copied())
                    .map(|index| {
                        let cue = &this.session.document().cues[index];
                        let selected = this.session.selected() == Some(index);
                        let weak = entity.downgrade();
                        row()
                            .id(("cue", index))
                            .role(Role::Button)
                            .focusable()
                            .tab_index(0)
                            .aria_label(format!("Subtítulo {}: {}", index + 1, cue.text))
                            .w_full()
                            .h(px(66.))
                            .px_4()
                            .gap_4()
                            .border_b_1()
                            .border_color(rgb(LINE))
                            .bg(rgb(if selected { 0x19312E } else { CARD }))
                            .cursor_pointer()
                            .hover(|s| s.bg(rgb(0x242C30)))
                            .child(
                                div()
                                    .w(px(34.))
                                    .text_color(rgb(MUTED))
                                    .child(format!("{:02}", index + 1)),
                            )
                            .child(
                                column()
                                    .w(px(116.))
                                    .gap_1()
                                    .text_size(px(11.))
                                    .text_color(rgb(MUTED))
                                    .child(subtitles::timecode(cue.start_ms))
                                    .child(subtitles::timecode(cue.end_ms)),
                            )
                            .child(
                                column()
                                    .flex_1()
                                    .min_w_0()
                                    .gap_1()
                                    .child(div().text_ellipsis().child(cue.text.clone()))
                                    .when(cue.changed(), |d| {
                                        d.child(
                                            div()
                                                .text_size(px(11.))
                                                .text_color(rgb(MUTED))
                                                .text_ellipsis()
                                                .child(cue.original.clone()),
                                        )
                                    }),
                            )
                            .child(
                                div()
                                    .w(px(68.))
                                    .text_size(px(11.))
                                    .text_color(rgb(if cue.changed() { ACCENT } else { MUTED }))
                                    .child(if cue.changed() { "Editado" } else { "Original" }),
                            )
                            .on_click(move |_, window, cx| {
                                if let Some(entity) = weak.upgrade() {
                                    entity.update(cx, |this, cx| {
                                        if this.busy {
                                            return;
                                        }
                                        this.select_cue(index, window, cx);
                                    });
                                }
                            })
                            .on_key_down({
                                let weak = entity.downgrade();
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
        )
        .w_full()
        .flex_1()
        .min_h_0();
        view = view
            .child(
                row()
                    .justify_between()
                    .child(label(format!(
                        "{} de {} subtítulos",
                        self.filtered_cues.len(),
                        self.session.document().cues.len()
                    )))
                    .child(
                        row()
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
                    )
                    .child(
                        div()
                            .text_color(rgb(ACCENT))
                            .text_size(px(12.))
                            .child(format!(
                                "{} editados{}",
                                self.session.document().changed(),
                                if self.session.is_dirty() {
                                    " · sin exportar"
                                } else {
                                    ""
                                }
                            )),
                    ),
            )
            .child(
                column()
                    .gap_0()
                    .flex_1()
                    .min_h_0()
                    .bg(rgb(CARD))
                    .rounded_lg()
                    .overflow_hidden()
                    .child(list),
            );
        if let Some(i) = self.session.selected() {
            view = view.child(
                panel()
                    .gap_2()
                    .child(
                        row()
                            .justify_between()
                            .child(label(format!(
                                "BLOQUE {} · {} — {}",
                                i + 1,
                                subtitles::timecode(self.session.document().cues[i].start_ms),
                                subtitles::timecode(self.session.document().cues[i].end_ms)
                            )))
                            .child(label(if draft {
                                "Edición pendiente de guardar"
                            } else {
                                "Texto actual"
                            })),
                    )
                    .child(Textarea::new(&self.edit).h(px(72.)).disabled(self.busy))
                    .child(
                        row()
                            .child(
                                accent_button("save-edit", "Guardar cambio", self.busy || !draft)
                                    .on_click(cx.listener(|this, _, w, cx| this.save_edit(w, cx))),
                            )
                            .child(
                                button("cancel-edit", "Descartar edición", self.busy || !draft)
                                    .on_click(
                                        cx.listener(|this, _, w, cx| this.discard_edit(w, cx)),
                                    ),
                            )
                            .child(div().flex_1())
                            .child(label("Los tiempos no se modifican.")),
                    ),
            );
        }
        view
    }

    fn library_view(&self, cx: &mut Context<Self>) -> Div {
        let entity = cx.entity().downgrade();
        let mut view = column()
            .size_full()
            .min_h_0()
            .gap_4()
            .child(
                row()
                    .justify_between()
                    .child(
                        column()
                            .gap_1()
                            .child(heading("Biblioteca"))
                            .child(label("Encuentra tus medios, títulos y documentos locales.")),
                    )
                    .child(
                        accent_button("choose-library", "Elegir carpeta", self.busy)
                            .on_click(cx.listener(|this, _, w, cx| this.choose_library(w, cx))),
                    ),
            )
            .child(
                row()
                    .child(
                        div()
                            .flex_1()
                            .min_w_0()
                            .text_ellipsis()
                            .text_color(rgb(MUTED))
                            .child(if self.inventory.root.as_os_str().is_empty() {
                                "Sin carpeta seleccionada".to_string()
                            } else {
                                self.inventory.root.display().to_string()
                            }),
                    )
                    .child(
                        button(
                            "refresh-library",
                            "Actualizar",
                            self.busy || self.inventory.root.as_os_str().is_empty(),
                        )
                        .on_click(cx.listener(|this, _, w, cx| {
                            this.scan_library(this.inventory.root.clone(), w, cx)
                        })),
                    ),
            );
        if self.inventory.root.as_os_str().is_empty() {
            return view.child(empty(
                "Todos tus recursos, a mano",
                "Elige una carpeta para explorar sus archivos compatibles.",
            ));
        }
        view = view.child(Input::new(&self.filter)).child(label(format!(
            "{} de {} recursos",
            self.filtered_resources.len(),
            self.inventory.resources.len()
        )));
        let list = uniform_list(
            "resource-list",
            self.filtered_resources.len(),
            move |range, _, cx| {
                let Some(entity) = entity.upgrade() else {
                    return vec![];
                };
                let this = entity.read(cx);
                range
                    .filter_map(|i| this.filtered_resources.get(i).copied())
                    .map(|i| {
                        let resource = &this.inventory.resources[i];
                        let path = resource.path.clone();
                        row()
                            .id(("resource", i))
                            .role(Role::Button)
                            .focusable()
                            .tab_index(0)
                            .aria_label(format!("Mostrar {}", resource.name))
                            .w_full()
                            .h(px(58.))
                            .px_4()
                            .border_b_1()
                            .border_color(rgb(LINE))
                            .cursor_pointer()
                            .hover(|s| s.bg(rgb(0x242C30)))
                            .child(
                                div()
                                    .w(px(94.))
                                    .text_color(rgb(ACCENT))
                                    .text_size(px(12.))
                                    .child(resource.category),
                            )
                            .child(
                                div()
                                    .flex_1()
                                    .min_w_0()
                                    .text_ellipsis()
                                    .child(resource.name.clone()),
                            )
                            .child(label(format!("{:.1} KB", resource.bytes as f64 / 1024.)))
                            .on_click({
                                let path = path.clone();
                                move |_, _, cx| cx.reveal_path(&path)
                            })
                            .on_key_down(move |event: &KeyDownEvent, _, cx| {
                                if matches!(event.keystroke.key.as_str(), "enter" | "space") {
                                    cx.reveal_path(&path);
                                }
                            })
                    })
                    .collect::<Vec<_>>()
            },
        )
        .w_full()
        .flex_1()
        .min_h_0();
        view.child(
            column()
                .gap_0()
                .flex_1()
                .min_h_0()
                .bg(rgb(CARD))
                .rounded_lg()
                .overflow_hidden()
                .child(list),
        )
        .child(label(
            "Selecciona un recurso para mostrar su ubicación en el Explorador.",
        ))
    }

    fn resolve_view(&self, cx: &mut Context<Self>) -> Div {
        let (title, description) = match &self.resolve {
            Some(status) if status.running => ("Resolve conectado", status.description.clone()),
            Some(status) => ("Resolve no disponible", status.description.clone()),
            None => (
                "Comprueba tu conexión",
                "La comprobación se realiza cuando la solicitas.".to_string(),
            ),
        };
        column().gap_6().child(column().gap_1().child(heading("Conexión con Resolve"))
            .child(label("Consulta el estado y lee los subtítulos de tu secuencia.")))
            .child(panel().gap_4().child(div().text_size(px(19.)).child(title)).child(label(description))
                .child(row().child(accent_button("check-resolve","Comprobar conexión",self.busy).on_click(cx.listener(|this,_,w,cx|this.check_resolve(w,cx))))
                    .child(button("resolve-subtitles","Leer subtítulos · pista 1",self.busy).on_click(cx.listener(|this,_,w,cx|this.capture(w,cx))))))
            .child(column().gap_2().child(div().font_weight(FontWeight::MEDIUM).child("Tu montaje permanece intacto"))
                .child(label("Esta demo consulta Resolve y exporta archivos SRT. La aplicación de cambios a la secuencia llegará en otro incremento.")))
    }
}

impl Render for FlowApp {
    fn render(&mut self, _window: &mut Window, cx: &mut Context<Self>) -> impl IntoElement {
        let content = match self.tab {
            Tab::Subtitles => self.subtitles_view(cx),
            Tab::Library => self.library_view(cx),
            Tab::Resolve => self.resolve_view(cx),
        };
        row()
            .size_full()
            .gap_0()
            .bg(rgb(BG))
            .text_color(rgb(TEXT))
            .font_family("Segoe UI")
            .text_size(px(13.))
            .child(self.sidebar(cx))
            .child(
                column()
                    .flex_1()
                    .min_w_0()
                    .h_full()
                    .gap_0()
                    .child(div().flex_1().min_h_0().p_6().child(content))
                    .child(
                        row()
                            .h(px(48.))
                            .flex_shrink_0()
                            .border_t_1()
                            .border_color(rgb(LINE))
                            .px_6()
                            .child(div().size(px(7.)).rounded_full().bg(rgb(if self.error {
                                ERROR
                            } else if self.busy {
                                0xFFE6CA
                            } else {
                                ACCENT
                            })))
                            .child(
                                div()
                                    .id("status-message")
                                    .role(Role::Status)
                                    .aria_label(self.message.clone())
                                    .flex_1()
                                    .min_w_0()
                                    .text_ellipsis()
                                    .text_size(px(12.))
                                    .text_color(rgb(if self.error { ERROR } else { MUTED }))
                                    .child(self.message.clone()),
                            )
                            .child(label(if self.busy {
                                "Trabajando…"
                            } else {
                                "Demo · desarrollo"
                            })),
                    ),
            )
    }
}
