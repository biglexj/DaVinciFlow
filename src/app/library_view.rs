//! Pestaña «Biblioteca»: carpetas por categoría y recursos compartibles.
use super::*;
use gpui_kit::component::Icon;
use gpui_kit::component::checkbox::Checkbox;

impl FlowApp {
    fn library_folders(&self, cx: &mut Context<Self>) -> Div {
        let folders = self.preferences.folders_for(&self.library_category);
        if folders.is_empty() {
            return div()
                .text_size(px(12.))
                .text_color(rgb(MUTED))
                .child(format!(
                    "No hay carpetas configuradas para {}. Pulsa «+ Añadir carpeta».",
                    library::label(&self.library_category)
                ));
        }
        column()
            .gap(px(6.))
            .children(folders.iter().enumerate().map(|(index, path)| {
                let weak = cx.entity().downgrade();
                row()
                    .id(("folder", index))
                    .w_full()
                    .justify_between()
                    .gap(px(10.))
                    .px(px(10.))
                    .py(px(4.))
                    .rounded(px(8.))
                    .bg(rgb(FIELD))
                    .border_1()
                    .border_color(rgb(LINE))
                    .child(
                        row()
                            .flex_1()
                            .min_w_0()
                            .gap(px(8.))
                            .child(
                                Icon::new(IconName::Folder)
                                    .size(px(16.))
                                    .text_color(rgb(ACCENT)),
                            )
                            .child(
                                div()
                                    .flex_1()
                                    .min_w_0()
                                    .text_ellipsis()
                                    .text_size(px(12.))
                                    .child(path.to_string_lossy().into_owned()),
                            ),
                    )
                    .child(
                        button(format!("remove-folder-{index}"), "Quitar", false).on_click({
                            let weak = weak.clone();
                            move |_, window, cx| {
                                if let Some(entity) = weak.upgrade() {
                                    entity.update(cx, |this, cx| {
                                        this.remove_library_folder(index, window, cx)
                                    });
                                }
                            }
                        }),
                    )
            }))
    }

    fn library_resources(&self, cx: &mut Context<Self>) -> Div {
        let entity = cx.entity().downgrade();
        let rows = uniform_list(
            "library-list",
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
                        let id = resource.id.clone();
                        let selected = this.preferences.is_selected(&id);
                        let weak = entity.downgrade();
                        row()
                            .id(("resource", index))
                            .w_full()
                            .gap(px(10.))
                            .px(px(6.))
                            .py(px(4.))
                            .rounded(px(8.))
                            .child(
                                Checkbox::new(("resource-check", index))
                                    .checked(selected)
                                    .on_click({
                                        let weak = weak.clone();
                                        move |_, _, cx| {
                                            if let Some(entity) = weak.upgrade() {
                                                entity.update(cx, |this, cx| {
                                                    this.toggle_resource(index, cx)
                                                });
                                            }
                                        }
                                    }),
                            )
                            .child(
                                column()
                                    .flex_1()
                                    .min_w_0()
                                    .gap(px(1.))
                                    .child(
                                        div()
                                            .text_size(px(12.))
                                            .text_ellipsis()
                                            .child(resource.name.clone()),
                                    )
                                    .child(
                                        div()
                                            .text_size(px(11.))
                                            .text_color(rgb(MUTED))
                                            .text_ellipsis()
                                            .child(resource.path.to_string_lossy().into_owned()),
                                    ),
                            )
                            .child(
                                div()
                                    .w(px(96.))
                                    .text_size(px(11.))
                                    .text_color(rgb(ACCENT))
                                    .child(resource.category),
                            )
                            .child(
                                div()
                                    .w(px(80.))
                                    .text_size(px(11.))
                                    .text_color(rgb(MUTED))
                                    .child(format!("{:.1} KB", resource.bytes as f64 / 1024.)),
                            )
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
            .child(div().flex_1().min_h_0().child(rows.h_full()))
    }

    pub fn library_view(&self, cx: &mut Context<Self>) -> Div {
        let categories = library::CATEGORIES;
        let current = self.library_category.clone();
        let resources = self.library_inventory.resources.len();
        let selected = self.preferences.selected.len();
        let warnings = self.library_inventory.warnings.join(" ");

        column()
            .size_full()
            .min_h_0()
            .gap(px(10.))
            .child(
                row()
                    .gap(px(8.))
                    .children(categories.iter().map(|(key, label)| {
                        let active = *key == current;
                        let category = *key;
                        let button = if active {
                            accent_button(format!("category-{key}"), *label, false)
                        } else {
                            button(format!("category-{key}"), *label, false)
                        };
                        button.on_click(cx.listener(move |this, _, window, cx| {
                            this.select_library_category(category, window, cx)
                        }))
                    })),
            )
            .child(
                card()
                    .gap(px(10.))
                    .child(section("Carpetas configuradas:"))
                    .child(self.library_folders(cx))
                    .child(
                        row()
                            .gap(px(10.))
                            .child(button("add-folder", "Añadir carpeta", self.busy).on_click(
                                cx.listener(|this, _, window, cx| {
                                    this.choose_library_folder(window, cx)
                                }),
                            ))
                            .child(
                                accent_button("index-library", "Guardar e indexar", self.busy)
                                    .on_click(cx.listener(|this, _, window, cx| {
                                        this.scan_library(window, cx)
                                    })),
                            )
                            .child(
                                button(
                                    "clear-category",
                                    "Vaciar categoría",
                                    self.busy || self.preferences.folders_for(&current).is_empty(),
                                )
                                .on_click(cx.listener(
                                    |this, _, window, cx| this.clear_library_category(window, cx),
                                )),
                            )
                            .child(
                                button(
                                    "reset-library",
                                    "Restablecer todo",
                                    self.busy
                                        || (self.preferences.folders.values().all(Vec::is_empty)
                                            && self.preferences.selected.is_empty()),
                                )
                                .on_click(
                                    cx.listener(|this, _, window, cx| {
                                        this.reset_library(window, cx)
                                    }),
                                ),
                            )
                            .child(label(format!(
                                "{} carpetas · {} recursos indexados",
                                self.preferences.folders_for(&current).len(),
                                resources
                            ))),
                    ),
            )
            .child(Input::new(&self.library_filter))
            .child(
                row()
                    .justify_between()
                    .child(label(format!(
                        "{resources} recursos · {selected}/80 compartidos"
                    )))
                    .child(
                        row()
                            .gap(px(8.))
                            .child(label(
                                "Comparte hasta 80 recursos con la IA por nombre y categoría.",
                            ))
                            .child(
                                button(
                                    "remove-missing-lib",
                                    "Quitar selección no disponible",
                                    self.busy || selected == 0,
                                )
                                .on_click(cx.listener(
                                    |this, _, window, cx| this.remove_missing_resources(window, cx),
                                )),
                            ),
                    ),
            )
            .child(self.library_resources(cx))
            .child(label(warnings))
    }
}
