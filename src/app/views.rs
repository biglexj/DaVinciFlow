//! Composición de la ventana: barra lateral, encabezado, área de trabajo y pie.
use super::*;

impl Render for FlowApp {
    fn render(&mut self, _window: &mut Window, cx: &mut Context<Self>) -> impl IntoElement {
        let content = match self.tab {
            Tab::Assistant => self.assistant_view(cx),
            Tab::Editor => self.editor_view(cx),
            Tab::Subtitles => self.subtitles_view(cx),
            Tab::Voice => self.voice_view(cx),
            Tab::Fetch => self.fetch_view(cx),
            Tab::Brolls => self.media_view("visuals", cx),
            Tab::Music => self.media_view("music", cx),
            Tab::Sfx => self.sfx_view(cx),
            Tab::Catalog => self.catalog_view(cx),
            Tab::Library => self.library_view(cx),
            Tab::Settings => self.settings_view(cx),
        };
        let p = palette();
        let shell = row()
            .size_full()
            .gap_0()
            .bg(rgb(p.bg))
            .text_color(rgb(p.text))
            .font_family("Segoe UI")
            .text_size(px(13.))
            .child(self.sidebar(cx))
            .child(
                column()
                    .flex_1()
                    .min_w_0()
                    .h_full()
                    .gap_0()
                    .child(
                        column()
                            .flex_1()
                            .min_h_0()
                            .pl(px(18.))
                            .pr(px(20.))
                            .pt(px(12.))
                            .pb(px(10.))
                            .gap(px(10.))
                            .child(self.header())
                            .child(div().flex_1().min_h_0().w_full().child(content)),
                    )
                    .child(self.footer(cx)),
            );
        let mut root = div().relative().size_full().child(shell);
        if let Some(toast) = &self.toast_message {
            root = root.child(
                div()
                    .absolute()
                    .top(px(18.))
                    .left_0()
                    .right_0()
                    .flex()
                    .justify_center()
                    .child(
                        row()
                            .px(px(20.))
                            .py(px(10.))
                            .rounded(px(20.))
                            .bg(rgb(0x182622))
                            .border_1()
                            .border_color(rgb(ACCENT))
                            .gap(px(8.))
                            .child(
                                gpui_kit::component::Icon::new(IconName::CircleCheck)
                                    .size(px(18.))
                                    .text_color(rgb(ACCENT)),
                            )
                            .child(
                                div()
                                    .text_size(px(13.))
                                    .font_weight(FontWeight::MEDIUM)
                                    .text_color(rgb(TEXT))
                                    .child(toast.clone()),
                            ),
                    ),
            );
        }
        if self.about_open {
            root = root.child(self.about_overlay(cx));
        }
        if let Some((title, preview)) = &self.catalog_preview {
            root = root.child(self.catalog_preview_overlay(title, preview, cx));
        }
        if self.video_modal_open {
            root = root.child(self.video_overlay(cx));
        }
        root
    }
}
