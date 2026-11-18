use super::*;

impl FlowApp {
    pub fn fetch_view(&self, cx: &mut Context<Self>) -> Div {
        let mut view = column().w_full().max_w(px(820.)).gap(px(12.)).child(
            card()
                .child(section("Descargar un recurso"))
                .child(Input::new(&self.fetch_url))
                .child(
                    row()
                        .child(
                            button("fetch-analyze", "Analizar enlace", self.busy).on_click(
                                cx.listener(|this, _, window, cx| this.fetch_analyze(window, cx)),
                            ),
                        )
                        .child(div().flex_1())
                        .child(
                            button(
                                "fetch-video",
                                if self.fetch_audio {
                                    "Vídeo"
                                } else {
                                    "✓ Vídeo"
                                },
                                self.busy,
                            )
                            .on_click(cx.listener(|this, _, _, cx| {
                                this.fetch_audio = false;
                                cx.notify();
                            })),
                        )
                        .child(
                            button(
                                "fetch-audio",
                                if self.fetch_audio {
                                    "✓ Audio MP3"
                                } else {
                                    "Audio MP3"
                                },
                                self.busy,
                            )
                            .on_click(cx.listener(|this, _, _, cx| {
                                this.fetch_audio = true;
                                cx.notify();
                            })),
                        ),
                )
                .child(field_label("Destino"))
                .child(
                    row()
                        .child(div().flex_1().child(Input::new(&self.fetch_directory)))
                        .child(
                            button("fetch-folder", "Elegir carpeta", self.busy).on_click(
                                cx.listener(|this, _, window, cx| {
                                    this.choose_fetch_folder(window, cx)
                                }),
                            ),
                        ),
                )
                .child(
                    row()
                        .child(
                            button(
                                "fetch-import",
                                if self.fetch_import {
                                    "✓ Importar a Resolve"
                                } else {
                                    "Importar a Resolve"
                                },
                                self.busy,
                            )
                            .on_click(cx.listener(|this, _, _, cx| {
                                this.fetch_import = !this.fetch_import;
                                cx.notify();
                            })),
                        )
                        .child(div().flex_1())
                        .child(
                            accent_button(
                                "fetch-download",
                                "Descargar",
                                self.busy || self.fetch_url.read(cx).value().trim().is_empty(),
                            )
                            .on_click(
                                cx.listener(|this, _, window, cx| this.fetch_download(window, cx)),
                            ),
                        ),
                ),
        );
        if let Some(info) = &self.fetch_info {
            view = view.child(
                card()
                    .child(section(info.title.clone()))
                    .child(label(format!(
                        "{} · {:.0} s",
                        info.uploader.as_deref().unwrap_or("Autor no disponible"),
                        info.duration_seconds
                    ))),
            );
        }
        if let Some(result) = &self.fetch_result {
            let play = result.path.clone();
            let folder = result.path.clone();
            let import = result.path.clone();
            view = view.child(
                card()
                    .child(section(result.title.clone()))
                    .child(label(result.path.display().to_string()))
                    .child(
                        row()
                            .child(button("fetch-play", "Abrir archivo", self.busy).on_click(
                                cx.listener(move |_, _, _, cx| cx.open_with_system(&play)),
                            ))
                            .child(
                                button("fetch-reveal", "Mostrar en carpeta", self.busy).on_click(
                                    cx.listener(move |_, _, _, cx| cx.reveal_path(&folder)),
                                ),
                            )
                            .child(
                                button(
                                    "fetch-import-result",
                                    "Importar a Resolve",
                                    self.busy || result.imported,
                                )
                                .on_click(cx.listener(
                                    move |this, _, window, cx| {
                                        this.import_file(import.clone(), window, cx)
                                    },
                                )),
                            ),
                    ),
            );
        }
        view
    }
}
