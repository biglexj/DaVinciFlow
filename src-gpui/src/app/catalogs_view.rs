//! Pestañas «Efectos (SFX)» y «Plantillas»: catálogos reales del proyecto.
use super::*;
use gpui_kit::component::Icon;

/// Etiqueta de origen de una plantilla, como en la interfaz vigente.
fn source_label(template: &services::TemplateInfo) -> &'static str {
    match template.category.as_str() {
        "davinci_flow" => "DaVinci Flow",
        "karaoke" => "DaVinci Flow · Karaoke",
        "shorts" => "📱 Shorts Bold",
        "youtube" => "🎬 YouTube Dinámico",
        "news" => "📰 Noticiero TV",
        _ => match template.source.as_str() {
            "media_pool" => "📁 Proyecto · Media Pool",
            "installed_bin" => "Referencia animada",
            "installed_archive" => "✨ DRFX Instalado",
            _ => "Instalado / archivo",
        },
    }
}

impl FlowApp {
    pub fn sfx_view(&self, cx: &mut Context<Self>) -> Div {
        let view = column().size_full().min_h_0().gap(px(10.)).child(
            card()
                .gap(px(8.))
                .child(
                    row()
                        .gap(px(10.))
                        .child(
                            Icon::new(IconName::AudioLines)
                                .size(px(18.))
                                .text_color(rgb(ACCENT)),
                        )
                        .child(label(format!(
                            "{} efectos de sonido del catálogo oficial",
                            self.sfx_assets.len()
                        ))),
                )
                .child(label(
                    "Escucha los efectos antes de elegirlos para tu montaje.",
                )),
        );
        if self.sfx_assets.is_empty() {
            return view.child(
                card()
                    .flex_1()
                    .min_h_0()
                    .items_center()
                    .gap(px(10.))
                    .p(px(36.))
                    .child(
                        Icon::new(IconName::AudioLines)
                            .size(px(32.))
                            .text_color(rgb(ACCENT)),
                    )
                    .child(
                        div()
                            .text_size(px(17.))
                            .font_weight(FontWeight::MEDIUM)
                            .child("Catálogo de efectos de sonido"),
                    )
                    .child(label("Cargando el catálogo oficial…")),
            );
        }
        let entity = cx.entity().downgrade();
        let rows = uniform_list("sfx-list", self.sfx_assets.len(), move |range, _, cx| {
            let Some(entity) = entity.upgrade() else {
                return vec![];
            };
            let this = entity.read(cx);
            range
                .filter_map(|index| this.sfx_assets.get(index))
                .map(|asset| {
                    let weak = entity.downgrade();
                    let id = asset.id.clone();
                    row()
                        .w_full()
                        .h(px(48.))
                        .px(px(14.))
                        .gap(px(12.))
                        .border_b_1()
                        .border_color(rgb(LINE))
                        .bg(rgb(CARD))
                        .child(
                            div()
                                .flex_1()
                                .min_w_0()
                                .text_ellipsis()
                                .child(asset.name.clone()),
                        )
                        .child(chip(asset.category.clone(), false))
                        .child(
                            button(
                                ElementId::Name(format!("sfx-play-{}", asset.id).into()),
                                "Escuchar",
                                this.busy,
                            )
                            .on_click(move |_, window, cx| {
                                if let Some(entity) = weak.upgrade() {
                                    entity.update(cx, |this, cx| {
                                        this.play_sfx(id.clone(), window, cx)
                                    });
                                }
                            }),
                        )
                        .child(
                            div()
                                .w(px(80.))
                                .text_size(px(11.))
                                .text_color(rgb(MUTED))
                                .child(format!("{:.2} s", asset.duration_seconds)),
                        )
                        .child(
                            div()
                                .w(px(80.))
                                .text_size(px(11.))
                                .text_color(rgb(MUTED))
                                .child(format!("{:.0} dB", asset.recommended_gain_db)),
                        )
                })
                .collect::<Vec<_>>()
        });
        view.child(
            column()
                .flex_1()
                .min_h_0()
                .bg(rgb(CARD))
                .rounded(px(10.))
                .overflow_hidden()
                .child(div().flex_1().min_h_0().child(rows.h_full())),
        )
    }

    pub fn catalog_view(&self, _cx: &mut Context<Self>) -> Div {
        let mut view = column().size_full().min_h_0().gap(px(10.)).child(
            card()
                .gap(px(8.))
                .child(
                    row()
                        .gap(px(10.))
                        .child(
                            Icon::new(IconName::Type)
                                .size(px(18.))
                                .text_color(rgb(ACCENT)),
                        )
                        .child(label(format!(
                            "{} plantillas instaladas",
                            self.templates.len()
                        ))),
                )
                .child(label(
                    "Las plantillas se eligen al revisar cada bloque en la mesa del Editor.",
                )),
        );
        if !self.catalog_diagnostics.is_empty() {
            view = view.child(label(self.catalog_diagnostics.join(" ")));
        }
        if self.templates.is_empty() {
            return view.child(
                card()
                    .flex_1()
                    .min_h_0()
                    .items_center()
                    .gap(px(10.))
                    .p(px(36.))
                    .child(
                        Icon::new(IconName::Type)
                            .size(px(32.))
                            .text_color(rgb(ACCENT)),
                    )
                    .child(
                        div()
                            .text_size(px(17.))
                            .font_weight(FontWeight::MEDIUM)
                            .child("Catálogo de plantillas"),
                    )
                    .child(label("Leyendo las plantillas instaladas…")),
            );
        }
        let rows = self.templates.iter().map(|template| {
            row()
                .w_full()
                .px(px(14.))
                .py(px(8.))
                .gap(px(12.))
                .border_b_1()
                .border_color(rgb(LINE))
                .child(
                    div()
                        .flex_1()
                        .min_w_0()
                        .text_ellipsis()
                        .child(template.name.clone()),
                )
                .child(chip(source_label(template), false))
                .child(
                    div()
                        .w(px(280.))
                        .text_size(px(11.))
                        .text_color(rgb(MUTED))
                        .text_ellipsis()
                        .child(template.locator.clone()),
                )
        });
        view.child(
            column()
                .flex_1()
                .min_h_0()
                .bg(rgb(CARD))
                .rounded(px(10.))
                .overflow_hidden()
                .child(
                    div()
                        .id("catalog-list")
                        .flex_1()
                        .min_h_0()
                        .overflow_y_scroll()
                        .children(rows),
                ),
        )
    }
}
