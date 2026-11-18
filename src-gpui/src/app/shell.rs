//! Barra lateral, encabezado y pie: la estructura de ventana de la interfaz vigente.
use super::*;
use gpui_kit::component::Icon;

impl FlowApp {
    /// Identidad de la secuencia; la interfaz vigente la muestra bajo la marca.
    fn identity(&self) -> Div {
        let (project, timeline) = match &self.resolve {
            Some(status) if !status.project.is_empty() => {
                (status.project.clone(), status.timeline.clone())
            }
            _ => (String::new(), String::new()),
        };
        if project.is_empty() && timeline.is_empty() {
            return div()
                .text_size(px(12.))
                .text_color(rgb(MUTED))
                .text_ellipsis()
                .child("Sin secuencia capturada");
        }
        column()
            .gap(px(1.))
            .text_size(px(12.))
            .text_color(rgb(MUTED))
            .child(div().text_ellipsis().child(project))
            .child(div().text_ellipsis().child(timeline))
    }

    fn nav_item(&self, tab: Tab, cx: &mut Context<Self>) -> Stateful<Div> {
        let active = self.tab == tab;
        let available = tab.migrated();
        let on_click = tab;
        let on_key = tab;
        row()
            .id(("nav", tab as usize))
            .role(Role::Tab)
            .aria_label(tab.label())
            .aria_selected(active)
            .focusable()
            .tab_index(0)
            .w_full()
            .px(px(10.))
            .py(px(8.))
            .rounded(px(9.))
            .gap(px(9.))
            .cursor_pointer()
            .when(active, |item| item.bg(rgb(ACTIVE)))
            .child(
                Icon::new(tab.icon())
                    .size(px(18.))
                    .text_color(rgb(if active { ACCENT } else { MUTED })),
            )
            .child(
                div()
                    .text_size(px(12.5))
                    .font_weight(FontWeight::MEDIUM)
                    .text_color(rgb(if available { TEXT } else { MUTED }))
                    .child(tab.label()),
            )
            .on_click(cx.listener(move |this, _, window, cx| {
                this.load_for_tab(on_click, window, cx);
            }))
            .on_key_down(cx.listener(move |this, event: &KeyDownEvent, window, cx| {
                if matches!(event.keystroke.key.as_str(), "enter" | "space") {
                    this.load_for_tab(on_key, window, cx);
                }
            }))
    }

    fn about_button(&self, cx: &mut Context<Self>) -> Stateful<Div> {
        row()
            .id("about")
            .role(Role::Button)
            .aria_label("Acerca de DaVinci Flow")
            .focusable()
            .tab_index(0)
            .w_full()
            .px(px(12.))
            .py(px(10.))
            .rounded(px(9.))
            .gap(px(10.))
            .cursor_pointer()
            .hover(|item| item.bg(rgb(ACTIVE)))
            .child(
                Icon::new(IconName::Info)
                    .size(px(18.))
                    .text_color(rgb(MUTED)),
            )
            .child(
                div()
                    .text_size(px(13.))
                    .font_weight(FontWeight::MEDIUM)
                    .text_color(rgb(MUTED))
                    .child("Acerca de"),
            )
            .on_click(cx.listener(|this, _, _, cx| {
                this.about_open = true;
                cx.notify();
            }))
    }

    pub fn sidebar(&self, cx: &mut Context<Self>) -> Div {
        column()
            .w(px(174.))
            .h_full()
            .flex_shrink_0()
            .bg(rgb(SIDE))
            .px(px(10.))
            .py(px(16.))
            .gap(px(4.))
            .child(
                column()
                    .gap(px(2.))
                    .child(
                        row()
                            .gap(px(5.))
                            .child(img("branding/icon-transparent.png").size(px(28.)))
                            .child(
                                div()
                                    .text_size(px(14.))
                                    .font_weight(FontWeight::BOLD)
                                    .child("DaVinci Flow"),
                            ),
                    )
                    .child(
                        div()
                            .text_size(px(11.))
                            .text_color(rgb(MUTED))
                            .child("Tu espacio creativo"),
                    ),
            )
            .child(div().h(px(5.)))
            .child(self.identity())
            .child(
                div()
                    .h(px(18.))
                    .w_full()
                    .flex()
                    .items_center()
                    .child(div().w_full().h(px(1.)).bg(rgb(LINE))),
            )
            .child(
                column()
                    .id("nav-scroll")
                    .flex_1()
                    .min_h_0()
                    .overflow_y_scroll()
                    .gap(px(4.))
                    .children(Tab::MAIN.iter().map(|tab| self.nav_item(*tab, cx))),
            )
            .children(Tab::FOOT.iter().map(|tab| self.nav_item(*tab, cx)))
            .child(self.about_button(cx))
    }

    pub fn header(&self) -> Div {
        div().h(px(28.)).flex().items_center().child(
            div()
                .text_size(px(17.))
                .font_weight(FontWeight::SEMIBOLD)
                .child(self.tab.label()),
        )
    }

    pub fn footer(&self) -> Div {
        let spinner = Icon::new(IconName::Loader)
            .size(px(16.))
            .text_color(rgb(ACCENT))
            .with_animation(
                "footer-spinner",
                Animation::new(std::time::Duration::from_millis(800)).repeat(),
                |icon, delta| icon.transform(Transformation::rotate(percentage(delta))),
            );
        column()
            .flex_shrink_0()
            .child(div().w_full().h(px(1.)).bg(rgb(LINE)))
            .child(
                row()
                    .w_full()
                    .px(px(18.))
                    .py(px(9.))
                    .gap(px(10.))
                    .when(self.busy, |footer| footer.child(spinner))
                    .child(
                        div()
                            .id("status-message")
                            .role(Role::Status)
                            .aria_label(self.message.clone())
                            .flex_1()
                            .min_w_0()
                            .text_ellipsis()
                            .text_size(px(12.))
                            .text_color(rgb(if self.error { ERROR } else { MUTED }))
                            .child(self.message.clone()),
                    ),
            )
    }
}
