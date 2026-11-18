//! Lista compacta y vista previa real de los recursos locales.
use super::*;

impl FlowApp {
    fn media_rows(&self, cx: &mut Context<Self>) -> impl IntoElement {
        let entity = cx.entity().downgrade();
        uniform_list(
            "media-resources",
            self.library_filtered.len(),
            move |range, _, cx| {
                let Some(entity) = entity.upgrade() else {
                    return vec![];
                };
                let this = entity.read(cx);
                range
                    .filter_map(|position| this.library_filtered.get(position).copied())
                    .map(|index| {
                        let resource = &this.library_inventory.resources[index];
                        let selected = this.preferences.is_selected(&resource.id);
                        let weak = entity.downgrade();
                        let preview = entity.downgrade();
                        let play = resource.path.clone();
                        let path = resource.path.clone();
                        let audio = resource.category == "music" || resource.category == "sfx";
                        row()
                            .w_full()
                            .h(px(54.))
                            .px_2()
                            .border_b_1()
                            .border_color(rgb(LINE))
                            .child(
                                div()
                                    .flex_1()
                                    .min_w_0()
                                    .child(div().text_ellipsis().child(resource.name.clone()))
                                    .child(label(format!(
                                        "{:.1} MB",
                                        resource.bytes as f64 / 1_048_576.
                                    ))),
                            )
                            .child(
                                button(
                                    ("share", index),
                                    if selected { "✓ IA" } else { "IA" },
                                    this.busy,
                                )
                                .on_click(move |_, _, cx| {
                                    if let Some(entity) = weak.upgrade() {
                                        entity
                                            .update(cx, |this, cx| this.toggle_resource(index, cx));
                                    }
                                }),
                            )
                            .child(
                                button(
                                    ("preview", index),
                                    if audio { "Escuchar" } else { "Ver" },
                                    this.busy,
                                )
                                .on_click(move |_, window, cx| {
                                    if audio {
                                        cx.open_with_system(&play);
                                    } else if let Some(entity) = preview.upgrade() {
                                        entity.update(cx, |this, cx| {
                                            this.preview_media(path.clone(), window, cx)
                                        });
                                    }
                                }),
                            )
                    })
                    .collect::<Vec<_>>()
            },
        )
        .h_full()
    }
    pub fn media_view(&self, category: &str, cx: &mut Context<Self>) -> Div {
        if self.library_inventory.category != category {
            return column().child(label("Preparando la categoría de recursos…"));
        }
        let resources = self.library_filtered.len();
        let mut body = row().flex_1().min_h_0().items_start().child(
            card()
                .flex_1()
                .h_full()
                .min_h_0()
                .p_0()
                .overflow_hidden()
                .child(self.media_rows(cx)),
        );
        if category == "visuals" {
            let mut preview = card()
                .w(px(280.))
                .flex_shrink_0()
                .child(section("Vista previa"));
            if let Some(path) = &self.media_preview {
                preview = preview.child(
                    img(path.clone())
                        .w_full()
                        .h(px(158.))
                        .object_fit(ObjectFit::Contain),
                );
            } else {
                preview = preview.child(
                    div()
                        .h(px(158.))
                        .flex()
                        .items_center()
                        .justify_center()
                        .child(label("Elige «Ver» en un recurso")),
                );
            }
            if let Some(path) = &self.media_source {
                let open = path.clone();
                let import = path.clone();
                preview = preview
                    .child(label(
                        path.file_name()
                            .unwrap_or_default()
                            .to_string_lossy()
                            .into_owned(),
                    ))
                    .child(
                        button("media-play", "Abrir reproductor", self.busy)
                            .on_click(cx.listener(move |_, _, _, cx| cx.open_with_system(&open))),
                    )
                    .child(
                        button("media-import", "Importar a Resolve", self.busy).on_click(
                            cx.listener(move |this, _, window, cx| {
                                this.import_file(import.clone(), window, cx)
                            }),
                        ),
                    );
            }
            body = body.child(preview);
        }
        column()
            .size_full()
            .min_h_0()
            .child(
                row()
                    .child(div().flex_1().child(Input::new(&self.library_filter)))
                    .child(button("add-folder", "Añadir carpeta", self.busy).on_click(
                        cx.listener(|this, _, window, cx| this.choose_library_folder(window, cx)),
                    ))
                    .child(button("index-library", "Actualizar", self.busy).on_click(
                        cx.listener(|this, _, window, cx| this.scan_library(window, cx)),
                    )),
            )
            .child(label(format!(
                "{resources} recursos · {} carpetas · {}/80 compartidos con IA",
                self.preferences.folders_for(category).len(),
                self.preferences.selected.len()
            )))
            .child(body)
    }
}
