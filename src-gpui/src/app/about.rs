//! Diálogo «Acerca de DaVinci Flow» con la información oficial vigente.
use super::*;

const DONATIONS_URL: &str = "https://www.biglexj.com/donaciones";
const COFFEE_URL: &str = "https://buymeacoffee.com/biglexj";
const FEEDBACK_URL: &str = "https://github.com/biglexj/DaVinciFlow/issues";
const GITHUB_URL: &str = "https://github.com/biglexj";

impl FlowApp {
    fn about_link(
        &self,
        id: &'static str,
        label: &'static str,
        url: &'static str,
        primary: bool,
        cx: &mut Context<Self>,
    ) -> gpui_kit::component::button::Button {
        let button = if primary {
            accent_button(id, label, false)
        } else {
            button(id, label, false)
        };
        button.on_click(cx.listener(move |_, _, _, cx| cx.open_url(url)))
    }

    pub fn about_overlay(&self, cx: &mut Context<Self>) -> Div {
        div()
            .absolute()
            .inset_0()
            .flex()
            .items_center()
            .justify_center()
            .bg(rgba(0x00000099))
            .child(
                card()
                    .w(px(460.))
                    .gap(px(6.))
                    .child(
                        row()
                            .gap(px(12.))
                            .items_center()
                            .child(img("branding/icon-transparent.png").size(px(44.)))
                            .child(
                                column()
                                    .gap(px(2.))
                                    .child(
                                        div()
                                            .text_size(px(20.))
                                            .font_weight(FontWeight::BOLD)
                                            .child("DaVinci Flow"),
                                    )
                                    .child(
                                        div()
                                            .text_size(px(11.))
                                            .font_weight(FontWeight::SEMIBOLD)
                                            .text_color(rgb(ACCENT))
                                            .bg(rgb(0x153630))
                                            .rounded(px(6.))
                                            .px_2()
                                            .py_1()
                                            .child(format!(
                                                "v{} · Licencia MIT",
                                                env!("CARGO_PKG_VERSION")
                                            )),
                                    ),
                            ),
                    )
                    .child(div().h(px(4.)))
                    .child(
                        div()
                            .w_full()
                            .text_size(px(13.))
                            .font_weight(FontWeight::SEMIBOLD)
                            .text_center()
                            .child("Desarrollado por biglexj (2026)"),
                    )
                    .child(
                        div()
                            .w_full()
                            .text_size(px(12.))
                            .text_color(rgb(MUTED))
                            .text_center()
                            .child(
                                "Automatización modular de subtítulos, Fusion y edición para DaVinci Resolve.",
                            ),
                    )
                    .child(
                        div()
                            .w_full()
                            .text_size(px(11.))
                            .text_color(rgb(0x8E9A9F))
                            .text_center()
                            .child(
                                "Si esta herramienta agiliza tu flujo de trabajo diario, considera apoyar su desarrollo continuo.",
                            ),
                    )
                    .child(
                        div()
                            .w_full()
                            .text_size(px(10.))
                            .text_color(rgb(MUTED))
                            .text_center()
                            .child("Rust · GPUI Kit · Ventana nativa"),
                    )
                    .child(div().w_full().h(px(18.)).flex().items_center().child(
                        div().w_full().h(px(1.)).bg(rgb(LINE)),
                    ))
                    .child(self.update_panel(cx))
                    .child(
                        column()
                            .w_full()
                            .gap(px(8.))
                            .child(self.about_link(
                                "about-donations",
                                "Donaciones Oficiales (Yape / Plin / Web)",
                                DONATIONS_URL,
                                true,
                                cx,
                            ))
                            .child(self.about_link(
                                "about-coffee",
                                "Buy Me a Coffee ☕",
                                COFFEE_URL,
                                false,
                                cx,
                            ))
                            .child(self.about_link(
                                "about-feedback",
                                "Enviar Feedback / Reportar Error 💬",
                                FEEDBACK_URL,
                                false,
                                cx,
                            ))
                            .child(self.about_link(
                                "about-github",
                                "Perfil de GitHub",
                                GITHUB_URL,
                                false,
                                cx,
                            )),
                    )
                    .child(
                        row()
                            .justify_end()
                            .child(button("about-close", "Cerrar", false).on_click(cx.listener(
                                |this, _, _, cx| {
                                    this.about_open = false;
                                    cx.notify();
                                },
                            ))),
                    ),
            )
    }
}
