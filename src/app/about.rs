//! Diálogo «Acerca de DaVinci Flow» siguiendo la estructura oficial unificada.
use super::*;
use gpui_kit::component::Icon;

const DONATIONS_URL: &str = "https://www.biglexj.com/donaciones";
const COFFEE_URL: &str = "https://buymeacoffee.com/biglexj";
const FEEDBACK_URL: &str = "https://github.com/biglexj/DaVinciFlow/issues";
const GITHUB_URL: &str = "https://github.com/biglexj";
const REPO_URL: &str = "https://github.com/biglexj/DaVinciFlow";
const WEBSITE_URL: &str = "https://biglexj.com/desarrollo/davinci-flow";

struct SupportCardSpec {
    id: &'static str,
    icon: IconName,
    title: &'static str,
    subtitle: &'static str,
    url: &'static str,
    accent: u32,
    bg: u32,
    border: u32,
}

impl FlowApp {
    fn about_badge(
        label_text: impl Into<SharedString>,
        bg_hex: u32,
        fg_hex: u32,
        border_hex: u32,
    ) -> Div {
        div()
            .text_size(px(11.))
            .font_weight(FontWeight::SEMIBOLD)
            .text_color(rgb(fg_hex))
            .bg(rgb(bg_hex))
            .border_1()
            .border_color(rgb(border_hex))
            .rounded(px(7.))
            .px(px(9.))
            .py(px(3.))
            .child(label_text.into())
    }

    fn support_card(&self, spec: SupportCardSpec, cx: &mut Context<Self>) -> Stateful<Div> {
        let p = palette();
        let url = spec.url;
        let accent_color = spec.accent;
        row()
            .id(spec.id)
            .role(Role::Button)
            .aria_label(spec.title)
            .w_full()
            .min_w_0()
            .px(px(14.))
            .py(px(12.))
            .gap(px(12.))
            .rounded(px(10.))
            .bg(rgb(spec.bg))
            .border_1()
            .border_color(rgb(spec.border))
            .cursor_pointer()
            .hover(move |s| s.border_color(rgb(accent_color)))
            .child(
                Icon::new(spec.icon)
                    .size(px(18.))
                    .text_color(rgb(accent_color)),
            )
            .child(
                column()
                    .flex_1()
                    .min_w_0()
                    .gap(px(2.))
                    .child(
                        div()
                            .text_size(px(13.))
                            .font_weight(FontWeight::BOLD)
                            .text_color(rgb(p.text))
                            .child(spec.title),
                    )
                    .child(
                        div()
                            .text_size(px(11.))
                            .text_color(rgb(p.muted))
                            .text_ellipsis()
                            .child(spec.subtitle),
                    ),
            )
            .child(
                Icon::new(IconName::ExternalLink)
                    .size(px(14.))
                    .text_color(rgb(p.muted)),
            )
            .on_click(cx.listener(move |_, _, _, cx| cx.open_url(url)))
    }

    fn community_pill(
        &self,
        id: &'static str,
        icon: IconName,
        text: &'static str,
        url: &'static str,
        cx: &mut Context<Self>,
    ) -> Stateful<Div> {
        let p = palette();
        row()
            .id(id)
            .role(Role::Button)
            .aria_label(text)
            .px(px(11.))
            .py(px(6.))
            .gap(px(6.))
            .rounded(px(8.))
            .bg(rgb(p.field))
            .border_1()
            .border_color(rgb(p.line))
            .cursor_pointer()
            .hover(move |s| s.bg(rgb(p.active)).border_color(rgb(p.accent_fg)))
            .child(Icon::new(icon).size(px(13.)).text_color(rgb(p.muted)))
            .child(
                div()
                    .text_size(px(11.5))
                    .font_weight(FontWeight::MEDIUM)
                    .text_color(rgb(p.muted))
                    .child(text),
            )
            .on_click(cx.listener(move |_, _, _, cx| cx.open_url(url)))
    }

    pub fn about_overlay(&self, cx: &mut Context<Self>) -> Div {
        let p = palette();
        let is_light = self.preferences.appearance_mode == "light";
        let (don_bg, don_border, don_accent) = if is_light {
            (0xFFF1F5, 0xF5B8CC, 0xD6336C)
        } else {
            (0x1C1019, 0x5A2742, 0xFB7793)
        };
        let (cof_bg, cof_border, cof_accent) = if is_light {
            (0xFFFBEB, 0xF3D299, 0xB4690E)
        } else {
            (0x1D170E, 0x59431D, 0xF5B942)
        };
        let (mit_bg, mit_fg, mit_border) = if is_light {
            (0xE6F7F2, 0x00695F, 0x99D8C9)
        } else {
            (0x0D2C26, 0x2EE6C5, 0x1E5E50)
        };
        let (author_bg, author_fg, author_border) = if is_light {
            (0xFCE7F3, 0x9D174D, 0xF3B6D4)
        } else {
            (0x2C1322, 0xFB7793, 0x5A2742)
        };

        let header = row()
            .w_full()
            .justify_between()
            .px(px(20.))
            .py(px(14.))
            .border_b_1()
            .border_color(rgb(p.line))
            .child(
                row()
                    .gap(px(8.))
                    .child(
                        Icon::new(IconName::Info)
                            .size(px(17.))
                            .text_color(rgb(p.accent_fg)),
                    )
                    .child(
                        div()
                            .text_size(px(15.))
                            .font_weight(FontWeight::BOLD)
                            .text_color(rgb(p.text))
                            .child("Acerca de DaVinci Flow"),
                    ),
            )
            .child(
                div()
                    .id("about-close")
                    .role(Role::Button)
                    .aria_label("Cerrar")
                    .w(px(28.))
                    .h(px(28.))
                    .rounded(px(7.))
                    .flex()
                    .items_center()
                    .justify_center()
                    .cursor_pointer()
                    .hover(move |s| s.bg(rgb(p.active)))
                    .child(
                        Icon::new(IconName::X)
                            .size(px(16.))
                            .text_color(rgb(p.muted)),
                    )
                    .on_click(cx.listener(|this, _, _, cx| {
                        this.about_open = false;
                        this.about_licenses_open = false;
                        cx.notify();
                    })),
            );

        let hero_card = row()
            .w_full()
            .p(px(16.))
            .gap(px(16.))
            .rounded(px(12.))
            .bg(rgb(p.raised))
            .border_1()
            .border_color(rgb(p.line))
            .child(
                div()
                    .w(px(58.))
                    .h(px(58.))
                    .flex_shrink_0()
                    .rounded(px(14.))
                    .bg(rgb(p.field))
                    .border_1()
                    .border_color(rgb(p.line))
                    .flex()
                    .items_center()
                    .justify_center()
                    .child(img("branding/icon-transparent.png").size(px(42.))),
            )
            .child(
                column()
                    .flex_1()
                    .min_w_0()
                    .gap(px(6.))
                    .child(
                        div()
                            .text_size(px(18.))
                            .font_weight(FontWeight::BOLD)
                            .text_color(rgb(p.text))
                            .child("DaVinci Flow Desktop"),
                    )
                    .child(
                        div()
                            .text_size(px(12.5))
                            .text_color(rgb(p.muted))
                            .child(
                                "Automatización modular de subtítulos, Fusion, voz y edición para DaVinci Resolve.",
                            ),
                    )
                    .child(
                        row()
                            .gap(px(8.))
                            .child(Self::about_badge(
                                format!("v{}", env!("CARGO_PKG_VERSION")),
                                p.active,
                                p.accent_fg,
                                p.accent_fg,
                            ))
                            .child(Self::about_badge(
                                "Windows 64-bit",
                                p.secondary,
                                p.text,
                                p.line,
                            ))
                            .child(Self::about_badge(
                                "Licencia MIT",
                                mit_bg,
                                mit_fg,
                                mit_border,
                            ))
                            .child(Self::about_badge(
                                "biglexj © 2026",
                                author_bg,
                                author_fg,
                                author_border,
                            )),
                    ),
            );

        let licenses_section = column()
            .w_full()
            .gap(px(6.))
            .child(
                row()
                    .id("about-licenses-toggle")
                    .role(Role::Button)
                    .aria_label("Licencias y componentes de terceros")
                    .gap(px(6.))
                    .px(px(4.))
                    .py(px(2.))
                    .cursor_pointer()
                    .child(
                        Icon::new(if self.about_licenses_open {
                            IconName::ChevronDown
                        } else {
                            IconName::ChevronRight
                        })
                        .size(px(14.))
                        .text_color(rgb(p.muted)),
                    )
                    .child(
                        div()
                            .text_size(px(12.5))
                            .font_weight(FontWeight::MEDIUM)
                            .text_color(rgb(p.text))
                            .child("Licencias y componentes de terceros"),
                    )
                    .on_click(cx.listener(|this, _, _, cx| {
                        this.about_licenses_open = !this.about_licenses_open;
                        cx.notify();
                    })),
            )
            .when(self.about_licenses_open, |col| {
                col.child(
                    column()
                        .w_full()
                        .p(px(12.))
                        .gap(px(4.))
                        .rounded(px(10.))
                        .bg(rgb(p.field))
                        .border_1()
                        .border_color(rgb(p.line))
                        .child(label("• Rust + GPUI Kit — Interfaz nativa acelerada por GPU"))
                        .child(label("• DaVinci Resolve Scripting API & MCP stdio — Integración con Resolve 21"))
                        .child(label("• FFmpeg — Reproducción multimedia, vistas previas y caché de audio"))
                        .child(label("• Python 3.13 — Motor editorial, proveedores de IA y voz de Aurora"))
                        .child(label("• Lucide Icons — Iconografía bajo licencia ISC")),
                )
            });

        let support_section = column()
            .w_full()
            .p(px(16.))
            .gap(px(12.))
            .rounded(px(12.))
            .bg(rgb(p.raised))
            .border_1()
            .border_color(rgb(p.line))
            .child(
                row()
                    .gap(px(8.))
                    .child(
                        Icon::new(IconName::Heart)
                            .size(px(16.))
                            .text_color(rgb(don_accent)),
                    )
                    .child(
                        div()
                            .text_size(px(13.5))
                            .font_weight(FontWeight::BOLD)
                            .text_color(rgb(p.text))
                            .child("Apoyo Oficial & Canales de la Comunidad"),
                    ),
            )
            .child(
                div()
                    .text_size(px(12.))
                    .text_color(rgb(p.muted))
                    .child(
                        "DaVinci Flow es un proyecto de código abierto desarrollado con dedicación por biglexj. Si la aplicación te resulta útil en tus ediciones o flujos de trabajo, puedes apoyar el desarrollo continuo:",
                    ),
            )
            .child(
                div()
                    .w_full()
                    .grid()
                    .grid_cols(2)
                    .gap(px(10.))
                    .child(self.support_card(
                        SupportCardSpec {
                            id: "about-donations",
                            icon: IconName::Heart,
                            title: "Donaciones Oficiales",
                            subtitle: "Yape, Plin y transferencias directas",
                            url: DONATIONS_URL,
                            accent: don_accent,
                            bg: don_bg,
                            border: don_border,
                        },
                        cx,
                    ))
                    .child(self.support_card(
                        SupportCardSpec {
                            id: "about-coffee",
                            icon: IconName::Coffee,
                            title: "Buy Me a Coffee",
                            subtitle: "Apoyo para café y servidores",
                            url: COFFEE_URL,
                            accent: cof_accent,
                            bg: cof_bg,
                            border: cof_border,
                        },
                        cx,
                    )),
            )
            .child(
                row()
                    .w_full()
                    .gap(px(8.))
                    .child(self.community_pill(
                        "about-web",
                        IconName::Globe,
                        "biglexj.com",
                        WEBSITE_URL,
                        cx,
                    ))
                    .child(self.community_pill(
                        "about-github",
                        IconName::Github,
                        "@biglexj",
                        GITHUB_URL,
                        cx,
                    ))
                    .child(self.community_pill(
                        "about-repo",
                        IconName::ExternalLink,
                        "Repositorio DaVinci Flow",
                        REPO_URL,
                        cx,
                    ))
                    .child(self.community_pill(
                        "about-feedback",
                        IconName::MessageSquare,
                        "Reportar error",
                        FEEDBACK_URL,
                        cx,
                    )),
            );

        div()
            .absolute()
            .inset_0()
            .flex()
            .items_center()
            .justify_center()
            .bg(rgb(p.card))
            .child(
                column()
                    .w(px(660.))
                    .max_w_full()
                    .rounded(px(14.))
                    .bg(rgb(p.card))
                    .border_1()
                    .border_color(rgb(p.line))
                    .overflow_hidden()
                    .gap_0()
                    .child(header)
                    .child(
                        column()
                            .w_full()
                            .p(px(20.))
                            .gap(px(14.))
                            .child(hero_card)
                            .child(self.update_panel(cx))
                            .child(support_section)
                            .child(licenses_section),
                    ),
            )
    }
}
