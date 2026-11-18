//! Primitivas visuales compartidas con los tokens vigentes de la interfaz Flet.
use gpui_kit::component::{
    Disableable,
    button::{Button, ButtonVariants},
};
use gpui_kit::{prelude::*, *};

pub const BG: u32 = 0x121518;
pub const SIDE: u32 = 0x101214;
pub const CARD: u32 = 0x1B2024;
pub const FIELD: u32 = 0x14181C;
pub const LINE: u32 = 0x30373C;
pub const TEXT: u32 = 0xEDF2F3;
pub const MUTED: u32 = 0xACB7BD;
pub const ACCENT: u32 = 0x00C7B1;
pub const ERROR: u32 = 0xFB7793;
/// Fondo de la pestaña activa y de la fila seleccionada.
pub const ACTIVE: u32 = 0x173A35;
/// Fondo del encabezado de tabla.
pub const HEADING: u32 = 0x242C30;
/// Fondo del botón secundario y del chip en reposo.
pub const SECONDARY: u32 = 0x293136;
/// Fondo del chip de estado «Modificado».
pub const CHIP: u32 = 0x2B4A40;

pub fn column() -> Div {
    div().flex().flex_col().gap(px(10.))
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
pub fn section(value: impl Into<SharedString>) -> Div {
    div()
        .text_size(px(13.))
        .font_weight(FontWeight::SEMIBOLD)
        .child(value.into())
}
pub fn button(id: impl Into<ElementId>, text: impl Into<SharedString>, disabled: bool) -> Button {
    Button::new(id).label(text).disabled(disabled)
}
pub fn accent_button(
    id: impl Into<ElementId>,
    text: impl Into<SharedString>,
    disabled: bool,
) -> Button {
    button(id, text, disabled).primary()
}
/// Tarjeta equivalente a `shared.components.card` de la interfaz Flet.
pub fn card() -> Div {
    column()
        .bg(rgb(CARD))
        .border_1()
        .border_color(rgb(LINE))
        .rounded(px(8.))
        .p(px(12.))
}
/// Chip de estado de la tabla de subtítulos.
pub fn chip(value: impl Into<SharedString>, modified: bool) -> Div {
    div()
        .text_size(px(11.))
        .font_weight(FontWeight::SEMIBOLD)
        .text_color(rgb(if modified { 0xFFFFFF } else { MUTED }))
        .bg(rgb(if modified { CHIP } else { SECONDARY }))
        .border_1()
        .border_color(rgb(if modified { ACCENT } else { LINE }))
        .rounded(px(10.))
        .px_2()
        .py_1()
        .child(value.into())
}
/// Etiqueta de campo: la interfaz Flet las muestra dentro del control.
pub fn field_label(value: impl Into<SharedString>) -> Div {
    div()
        .text_size(px(12.))
        .text_color(rgb(MUTED))
        .child(value.into())
}
