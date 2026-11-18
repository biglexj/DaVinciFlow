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
        let shell = row()
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
                            .child(
                                div()
                                    .flex_1()
                                    .min_h_0()
                                    .w_full()
                                    .max_w(px(1120.))
                                    .child(content),
                            ),
                    )
                    .child(self.footer()),
            );
        let root = div().relative().size_full().child(shell);
        if self.about_open {
            root.child(self.about_overlay(cx))
        } else {
            root
        }
    }
}
