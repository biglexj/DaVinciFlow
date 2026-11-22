//! Visor modal integrado de vídeo (B-Rolls ampliados, Luna Fetch MP4 y animaciones de plantillas).
use super::*;
use gpui_kit::component::Icon;

impl FlowApp {
    pub fn video_overlay(&self, cx: &mut Context<Self>) -> Div {
        let Some(track) = &self.player_state.current else {
            return div();
        };
        if !track.is_video || !self.video_modal_open {
            return div();
        }
        let imp = track.path.clone();
        let viewport = if let Some(frame) = &self.video_frame {
            img(frame.clone())
                .w_full()
                .h(px(460.))
                .object_fit(ObjectFit::Contain)
                .into_any_element()
        } else {
            div()
                .w_full()
                .h(px(460.))
                .flex()
                .items_center()
                .justify_center()
                .child(label("Cargando vídeo…"))
                .into_any_element()
        };

        let p = palette();
        let display_title = track
            .path
            .file_name()
            .map(|n| n.to_string_lossy().into_owned())
            .filter(|s| !s.is_empty())
            .unwrap_or_else(|| track.title.clone());

        div()
            .absolute()
            .inset_0()
            .flex()
            .items_center()
            .justify_center()
            .bg(rgba(0x000000B8))
            .child(
                card()
                    .w(px(860.))
                    .max_w_full()
                    .overflow_hidden()
                    .gap(px(10.))
                    .p(px(16.))
                    .child(
                        row()
                            .w_full()
                            .min_w_0()
                            .gap(px(12.))
                            .justify_between()
                            .child(
                                row()
                                    .flex_1()
                                    .min_w_0()
                                    .overflow_hidden()
                                    .gap(px(8.))
                                    .child(
                                        Icon::new(IconName::Clapperboard)
                                            .size(px(18.))
                                            .text_color(rgb(p.accent_fg)),
                                    )
                                    .child(
                                        div()
                                            .flex_1()
                                            .min_w_0()
                                            .overflow_hidden()
                                            .whitespace_nowrap()
                                            .text_ellipsis()
                                            .text_size(px(13.))
                                            .font_weight(FontWeight::SEMIBOLD)
                                            .text_color(rgb(p.text))
                                            .child(display_title),
                                    ),
                            )
                            .child(
                                row()
                                    .flex_shrink_0()
                                    .gap(px(8.))
                                    .child(
                                        accent_button(
                                            "vid-modal-import",
                                            "Importar a Resolve",
                                            self.busy,
                                        )
                                        .on_click(
                                            cx.listener(move |this, _, window, cx| {
                                                this.import_file(imp.clone(), window, cx)
                                            }),
                                        ),
                                    )
                                    .child(button("vid-modal-close", "Cerrar", false).on_click(
                                        cx.listener(|this, _, window, cx| {
                                            this.video_modal_open = false;
                                            if this.player_origin != Some(Tab::Brolls) {
                                                this.stop_audio_with_window(Some(window), cx);
                                            }
                                            cx.notify();
                                        }),
                                    )),
                            ),
                    )
                    .child(
                        div()
                            .w_full()
                            .h(px(460.))
                            .rounded(px(8.))
                            .bg(rgb(0x0B0E10))
                            .border_1()
                            .border_color(rgb(p.line))
                            .overflow_hidden()
                            .child(viewport),
                    )
                    .child(self.render_player_deck("vid-modal-deck", false, cx)),
            )
    }
}
