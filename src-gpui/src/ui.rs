//! Primitivas visuales compartidas con los tokens vigentes de la interfaz Flet.
use gpui_kit::component::{
    Disableable,
    button::{Button, ButtonVariants},
};
use gpui_kit::{prelude::*, *};

pub const BG: u32 = 0x121518;
pub const SIDE: u32 = 0x101214;
pub const CARD: u32 = 0x1B2024;
pub const LINE: u32 = 0x30373C;
pub const TEXT: u32 = 0xEDF2F3;
pub const MUTED: u32 = 0xACB7BD;
pub const ACCENT: u32 = 0x00C7B1;
pub const ERROR: u32 = 0xFB7793;

pub fn column() -> Div {
    div().flex().flex_col().gap_3()
}
pub fn row() -> Div {
    div().flex().items_center().gap_2()
}
pub fn label(value: impl Into<SharedString>) -> Div {
    div()
        .text_size(px(12.))
        .text_color(rgb(MUTED))
        .child(value.into())
}
pub fn heading(value: impl Into<SharedString>) -> Div {
    div()
        .text_size(px(24.))
        .font_weight(FontWeight::SEMIBOLD)
        .child(value.into())
}
pub fn button(id: &'static str, text: &'static str, disabled: bool) -> Button {
    Button::new(id).label(text).disabled(disabled)
}
pub fn accent_button(id: &'static str, text: &'static str, disabled: bool) -> Button {
    button(id, text, disabled).primary()
}
pub fn empty(title: &'static str, detail: &'static str) -> Div {
    column()
        .flex_1()
        .min_h_0()
        .justify_center()
        .items_center()
        .gap_3()
        .child(
            div()
                .text_size(px(19.))
                .font_weight(FontWeight::MEDIUM)
                .child(title),
        )
        .child(label(detail))
}
pub fn panel() -> Div {
    column()
        .bg(rgb(CARD))
        .border_1()
        .border_color(rgb(LINE))
        .rounded_lg()
        .p_4()
}
