//! Panel de actualizaciones dentro del diálogo «Acerca de», como en la interfaz vigente.
use super::*;
use gpui_kit::component::Icon;

const RELEASES_URL: &str = "https://github.com/biglexj/DaVinciFlow/releases";

impl FlowApp {
    pub fn update_panel(&self, cx: &mut Context<Self>) -> Div {
        let (chip_text, chip_background, chip_color) = match &self.release {
            Some(release) if release.is_newer => (
                format!("Nueva v{}", release.version),
                0x382B14u32,
                0xFFA726u32,
            ),
            Some(_) => ("Al día".to_string(), 0x153630, ACCENT),
            None if self.release_checked => ("Sin confirmar".to_string(), 0x1B262C, MUTED),
            None => ("Comprobación pendiente".to_string(), 0x1B262C, MUTED),
        };

        let content = if let Some(release) = &self.release {
            if release.is_newer {
                column()
                    .gap(px(6.))
                    .child(
                        row()
                            .gap(px(6.))
                            .child(
                                Icon::new(IconName::Rocket)
                                    .size(px(18.))
                                    .text_color(rgb(0x00E5FF)),
                            )
                            .child(
                                div()
                                    .text_size(px(13.))
                                    .font_weight(FontWeight::BOLD)
                                    .child(format!(
                                        "¡Nueva versión v{} disponible!",
                                        release.version
                                    )),
                            ),
                    )
                    .child(label(format!(
                        "Publicada: {}",
                        if release.published_at.is_empty() {
                            "Reciente".to_string()
                        } else {
                            release.published_at.chars().take(10).collect()
                        }
                    )))
                    .child(section("Novedades destacadas:"))
                    .child(
                        div()
                            .id("release-notes")
                            .max_h(px(130.))
                            .overflow_y_scroll()
                            .p(px(10.))
                            .rounded(px(8.))
                            .bg(rgb(FIELD))
                            .border_1()
                            .border_color(rgb(LINE))
                            .text_size(px(11.))
                            .child(release.notes.clone()),
                    )
                    .child(
                        row()
                            .gap(px(8.))
                            .child({
                                let url = release.download_url.clone();
                                accent_button("download-update", "Descargar actualización", false)
                                    .on_click(cx.listener(move |_, _, _, cx| cx.open_url(&url)))
                            })
                            .child({
                                let url = release.page_url.clone();
                                button("open-release", "Ver en GitHub", false)
                                    .on_click(cx.listener(move |_, _, _, cx| cx.open_url(&url)))
                            }),
                    )
            } else {
                column()
                    .gap(px(4.))
                    .p(px(12.))
                    .rounded(px(8.))
                    .bg(rgb(0x14211D))
                    .border_1()
                    .border_color(rgb(0x1E3E36))
                    .child(
                        row()
                            .gap(px(6.))
                            .child(
                                Icon::new(IconName::CircleCheck)
                                    .size(px(17.))
                                    .text_color(rgb(ACCENT)),
                            )
                            .child(
                                div()
                                    .text_size(px(12.))
                                    .font_weight(FontWeight::SEMIBOLD)
                                    .child("Tu versión está completamente al día."),
                            ),
                    )
                    .child(label(
                        "DaVinci Flow cuenta con las plantillas, motores de subtítulos y optimizaciones más recientes.",
                    ))
            }
        } else if self.release_checked {
            div()
                .text_size(px(12.))
                .text_color(rgb(MUTED))
                .child("No se pudo confirmar la última versión publicada.")
        } else {
            row()
                .gap(px(6.))
                .p(px(12.))
                .rounded(px(8.))
                .bg(rgb(FIELD))
                .border_1()
                .border_color(rgb(LINE))
                .child(
                    Icon::new(IconName::Info)
                        .size(px(16.))
                        .text_color(rgb(MUTED)),
                )
                .child(label(
                    "Pulsa «Buscar actualizaciones» para consultar el canal oficial.",
                ))
        };

        card()
            .gap(px(12.))
            .p(px(20.))
            .child(
                row()
                    .gap(px(10.))
                    .items_center()
                    .child(
                        Icon::new(IconName::RefreshCw)
                            .size(px(22.))
                            .text_color(rgb(ACCENT)),
                    )
                    .child(
                        column()
                            .flex_1()
                            .gap(px(1.))
                            .child(section("Actualizaciones"))
                            .child(label("Canal oficial de GitHub Releases")),
                    )
                    .child(
                        div()
                            .text_size(px(11.))
                            .font_weight(FontWeight::SEMIBOLD)
                            .text_color(rgb(chip_color))
                            .bg(rgb(chip_background))
                            .rounded(px(6.))
                            .px_2()
                            .py_1()
                            .child(chip_text),
                    ),
            )
            .child(
                div()
                    .w_full()
                    .h(px(14.))
                    .flex()
                    .items_center()
                    .child(div().w_full().h(px(1.)).bg(rgb(LINE))),
            )
            .child(
                row().gap(px(10.)).items_center().child(
                    button("check-updates", "Buscar actualizaciones", self.busy).on_click(
                        cx.listener(|this, _, window, cx| this.check_release(window, cx)),
                    ),
                ),
            )
            .child(content)
            .child(
                div()
                    .w_full()
                    .h(px(14.))
                    .flex()
                    .items_center()
                    .child(div().w_full().h(px(1.)).bg(rgb(LINE))),
            )
            .child(
                row()
                    .id("release-history")
                    .gap(px(6.))
                    .px(px(6.))
                    .py(px(4.))
                    .rounded(px(6.))
                    .cursor_pointer()
                    .hover(|item| item.bg(rgb(CARD)))
                    .child(
                        Icon::new(IconName::Heading)
                            .size(px(16.))
                            .text_color(rgb(MUTED)),
                    )
                    .child(label("Ver historial completo de versiones en GitHub ↗"))
                    .on_click(cx.listener(move |_, _, _, cx| cx.open_url(RELEASES_URL))),
            )
    }
}
