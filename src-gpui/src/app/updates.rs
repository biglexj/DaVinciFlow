//! Panel compacto de actualizaciones dentro del diálogo «Acerca de».
use super::*;
use gpui_kit::component::Icon;

const RELEASES_URL: &str = "https://github.com/biglexj/DaVinciFlow/releases";

impl FlowApp {
    pub fn update_panel(&self, cx: &mut Context<Self>) -> Div {
        let p = palette();
        let subtitle = match &self.release {
            Some(release) if release.is_newer => {
                format!(
                    "¡Nueva versión v{} disponible en GitHub Releases!",
                    release.version
                )
            }
            Some(_) => "Tu versión está completamente al día.".to_string(),
            None if self.release_checked => {
                "No se pudo confirmar la última versión publicada.".to_string()
            }
            None => "Comprueba nuevas versiones y mejoras en GitHub Releases".to_string(),
        };

        let check_btn = row()
            .id("check-updates")
            .role(Role::Button)
            .aria_label("Buscar actualizaciones")
            .flex_shrink_0()
            .px(px(14.))
            .py(px(8.))
            .gap(px(7.))
            .rounded(px(18.))
            .bg(rgb(p.accent))
            .text_color(rgb(p.on_accent))
            .when(self.busy, |b| b.opacity(0.5).cursor_default())
            .when(!self.busy, |b| {
                b.cursor_pointer()
                    .hover(move |s| s.bg(rgb(p.accent_hover)))
                    .on_click(cx.listener(|this, _, window, cx| this.check_release(window, cx)))
            })
            .child(
                Icon::new(IconName::RefreshCw)
                    .size(px(14.))
                    .text_color(rgb(p.on_accent)),
            )
            .child(
                div()
                    .text_size(px(12.))
                    .font_weight(FontWeight::SEMIBOLD)
                    .text_color(rgb(p.on_accent))
                    .child("Buscar actualizaciones"),
            );

        let mut panel = column()
            .w_full()
            .px(px(16.))
            .py(px(14.))
            .gap(px(10.))
            .rounded(px(12.))
            .bg(rgb(p.raised))
            .border_1()
            .border_color(rgb(p.line))
            .child(
                row()
                    .w_full()
                    .justify_between()
                    .gap(px(12.))
                    .child(
                        row()
                            .flex_1()
                            .min_w_0()
                            .gap(px(10.))
                            .child(
                                Icon::new(IconName::Sparkles)
                                    .size(px(18.))
                                    .text_color(rgb(p.accent_fg)),
                            )
                            .child(
                                column()
                                    .flex_1()
                                    .min_w_0()
                                    .gap(px(2.))
                                    .child(
                                        div()
                                            .text_size(px(13.5))
                                            .font_weight(FontWeight::BOLD)
                                            .text_color(rgb(p.text))
                                            .child("Actualizaciones del Sistema"),
                                    )
                                    .child(
                                        div()
                                            .text_size(px(11.5))
                                            .text_color(rgb(p.muted))
                                            .text_ellipsis()
                                            .child(subtitle),
                                    ),
                            ),
                    )
                    .child(check_btn),
            );

        if let Some(release) = &self.release {
            if release.is_newer {
                let dl_url = release.download_url.clone();
                let page_url = release.page_url.clone();
                panel = panel.child(
                    column()
                        .w_full()
                        .gap(px(8.))
                        .pt(px(6.))
                        .border_t_1()
                        .border_color(rgb(p.line))
                        .child(
                            div()
                                .id("release-notes")
                                .max_h(px(110.))
                                .overflow_y_scroll()
                                .p(px(10.))
                                .rounded(px(8.))
                                .bg(rgb(p.field))
                                .border_1()
                                .border_color(rgb(p.line))
                                .text_size(px(11.5))
                                .text_color(rgb(p.text))
                                .child(release.notes.clone()),
                        )
                        .child(
                            row()
                                .gap(px(8.))
                                .child(
                                    accent_button(
                                        "download-update",
                                        "Descargar actualización",
                                        false,
                                    )
                                    .on_click(cx.listener(move |_, _, _, cx| cx.open_url(&dl_url))),
                                )
                                .child(button("open-release", "Ver en GitHub", false).on_click(
                                    cx.listener(move |_, _, _, cx| cx.open_url(&page_url)),
                                ))
                                .child(button("release-history", "Historial ↗", false).on_click(
                                    cx.listener(|_, _, _, cx| cx.open_url(RELEASES_URL)),
                                )),
                        ),
                );
            } else {
                panel = panel.child(
                    row()
                        .w_full()
                        .justify_between()
                        .pt(px(6.))
                        .border_t_1()
                        .border_color(rgb(p.line))
                        .child(
                            row()
                                .gap(px(6.))
                                .child(
                                    Icon::new(IconName::CircleCheck)
                                        .size(px(15.))
                                        .text_color(rgb(p.accent_fg)),
                                )
                                .child(label("Estás usando la versión más reciente disponible.")),
                        )
                        .child(
                            button("release-history", "Ver versiones ↗", false)
                                .on_click(cx.listener(|_, _, _, cx| cx.open_url(RELEASES_URL))),
                        ),
                );
            }
        }
        panel
    }
}
