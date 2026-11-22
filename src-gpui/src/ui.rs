//! Primitivas visuales y paleta unificada (Aurora y Clásico en modo oscuro y claro).
use gpui_kit::component::{
    Disableable,
    button::{Button, ButtonVariants},
};
use gpui_kit::{prelude::*, *};
use std::sync::atomic::{AtomicU8, Ordering};

// Constantes heredadas (Clásico oscuro) conservadas donde todavía se referencian directamente.
pub const CARD: u32 = 0x1B2024;
pub const FIELD: u32 = 0x14181C;
pub const LINE: u32 = 0x30373C;
pub const TEXT: u32 = 0xEDF2F3;
pub const MUTED: u32 = 0xACB7BD;
pub const ACCENT: u32 = 0x00C7B1;
pub const ERROR: u32 = 0xFB7793;
pub const ACTIVE: u32 = 0x173A35;
pub const HEADING: u32 = 0x242C30;

/// Paleta semántica activa según `Docs/global/design/app-colors.md` (v1.0.0).
#[derive(Clone, Copy, Debug)]
pub struct Palette {
    pub bg: u32,
    pub side: u32,
    pub card: u32,
    pub raised: u32,
    pub field: u32,
    pub line: u32,
    pub text: u32,
    pub muted: u32,
    pub accent: u32,
    pub accent_hover: u32,
    pub accent_fg: u32,
    pub on_accent: u32,
    pub active: u32,
    pub secondary: u32,
    pub chip: u32,
    pub error: u32,
}

const AURORA_DARK: Palette = Palette {
    bg: 0x020908,
    side: 0x040E0C,
    card: 0x071512,
    raised: 0x0B1D18,
    field: 0x040D0B,
    line: 0x28453E,
    text: 0xFFFFFF,
    muted: 0x93AAA3,
    accent: 0x00C9B9,
    accent_hover: 0x40DFD1,
    accent_fg: 0x00C9B9,
    on_accent: 0x000000,
    active: 0x12352D,
    secondary: 0x10211C,
    chip: 0x12352D,
    error: 0xFB7793,
};

const AURORA_LIGHT: Palette = Palette {
    bg: 0xFAFFFD,
    side: 0xF1F9F6,
    card: 0xF6FBF9,
    raised: 0xEAF6F1,
    field: 0xFFFFFF,
    line: 0xC3DAD3,
    text: 0x000000,
    muted: 0x51665E,
    accent: 0x00C9B9,
    accent_hover: 0x40DFD1,
    accent_fg: 0x00695F,
    on_accent: 0x000000,
    active: 0xD4EFE8,
    secondary: 0xE2EBE7,
    chip: 0xD4EFE8,
    error: 0xC81E4A,
};

const CLASSIC_DARK: Palette = Palette {
    bg: 0x121518,
    side: 0x101214,
    card: 0x1B2024,
    raised: 0x20262B,
    field: 0x14181C,
    line: 0x30373C,
    text: 0xEDF2F3,
    muted: 0xACB7BD,
    accent: 0x00C7B1,
    accent_hover: 0x1AD9C3,
    accent_fg: 0x00C7B1,
    on_accent: 0x071412,
    active: 0x173A35,
    secondary: 0x293136,
    chip: 0x2B4A40,
    error: 0xFB7793,
};

static ACTIVE_PALETTE: AtomicU8 = AtomicU8::new(0);

pub fn set_appearance(theme: &str, mode: &str) {
    let id = match (theme, mode) {
        (_, "light") => 1,
        ("classic", _) => 2,
        _ => 0,
    };
    ACTIVE_PALETTE.store(id, Ordering::Relaxed);
}

pub fn palette() -> Palette {
    match ACTIVE_PALETTE.load(Ordering::Relaxed) {
        1 => AURORA_LIGHT,
        2 => CLASSIC_DARK,
        _ => AURORA_DARK,
    }
}

/// Sincroniza la paleta local y el tema de `gpui-kit` con la preferencia de apariencia.
pub fn apply_gpui_theme(
    theme_name: &str,
    mode_name: &str,
    window: Option<&mut Window>,
    cx: &mut App,
) {
    set_appearance(theme_name, mode_name);
    let p = palette();
    let mode = if mode_name == "light" {
        gpui_kit::component::ThemeMode::Light
    } else {
        gpui_kit::component::ThemeMode::Dark
    };
    gpui_kit::component::Theme::change(mode, window, cx);
    gpui_kit::component::Theme::update(cx, |theme| {
        theme.font_family = "Segoe UI".into();
        theme.primary = rgb(p.accent).into();
        theme.primary_hover = rgb(p.accent_hover).into();
        theme.primary_active = rgb(0x00AB9D).into();
        theme.primary_foreground = rgb(p.on_accent).into();
        theme.button_primary = rgb(p.accent).into();
        theme.button_primary_hover = rgb(p.accent_hover).into();
        theme.button_primary_active = rgb(0x00AB9D).into();
        theme.button_primary_foreground = rgb(p.on_accent).into();
        theme.button_secondary = rgb(p.secondary).into();
        theme.button_secondary_hover = rgb(p.active).into();
        theme.button_secondary_active = rgb(p.raised).into();
        theme.button_secondary_foreground = rgb(p.text).into();
        theme.background = rgb(p.bg).into();
        theme.foreground = rgb(p.text).into();
        theme.border = rgb(p.line).into();
        theme.input = rgb(p.line).into();
        theme.ring = rgb(p.accent_fg).into();
    });
}

pub fn column() -> Div {
    div().flex().flex_col().gap(px(10.))
}
pub fn row() -> Div {
    div().flex().items_center().gap_2()
}
pub fn label(value: impl Into<SharedString>) -> Div {
    div()
        .text_size(px(12.))
        .text_color(rgb(palette().muted))
        .child(value.into())
}
pub fn section(value: impl Into<SharedString>) -> Div {
    div()
        .text_size(px(13.))
        .font_weight(FontWeight::SEMIBOLD)
        .text_color(rgb(palette().text))
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
/// Botón más alto y de ancho adaptable para rejillas en columnas (voces, soporte oficial, etc.).
pub fn fat_button(
    id: impl Into<ElementId>,
    text: impl Into<SharedString>,
    primary: bool,
    disabled: bool,
) -> Stateful<Div> {
    let p = palette();
    let label_text: SharedString = text.into();
    let base = div()
        .id(id)
        .role(Role::Button)
        .aria_label(label_text.clone())
        .flex_1()
        .flex_basis(px(0.))
        .min_w_0()
        .overflow_hidden()
        .h(px(42.))
        .px(px(12.))
        .rounded(px(8.))
        .flex()
        .items_center()
        .justify_center()
        .text_size(px(12.5))
        .font_weight(if primary {
            FontWeight::SEMIBOLD
        } else {
            FontWeight::MEDIUM
        })
        .bg(rgb(if primary { p.accent } else { p.raised }))
        .text_color(rgb(if primary { p.on_accent } else { p.text }))
        .when(!primary, |b| b.border_1().border_color(rgb(p.line)))
        .when(disabled, |b| b.opacity(0.45).cursor_default())
        .when(!disabled, |b| {
            b.cursor_pointer().hover(move |style| {
                if primary {
                    style.bg(rgb(p.accent_hover))
                } else {
                    style.bg(rgb(p.active)).border_color(rgb(p.accent))
                }
            })
        });
    base.child(
        div()
            .w_full()
            .min_w_0()
            .overflow_hidden()
            .whitespace_nowrap()
            .text_ellipsis()
            .text_center()
            .child(label_text),
    )
}

/// Botón de acción multimedia de ancho fijo para evitar saltos de columna al cambiar de estado.
pub fn fixed_media_button(
    id: impl Into<ElementId>,
    icon: gpui_kit::assets::IconName,
    text: impl Into<SharedString>,
    active: bool,
    disabled: bool,
    width: f32,
) -> Stateful<Div> {
    let p = palette();
    let label_text: SharedString = text.into();
    let fg = if active { p.on_accent } else { p.text };
    div()
        .id(id)
        .role(Role::Button)
        .aria_label(label_text.clone())
        .w(px(width))
        .flex_shrink_0()
        .overflow_hidden()
        .h(px(30.))
        .px(px(10.))
        .rounded(px(7.))
        .flex()
        .items_center()
        .justify_center()
        .gap(px(6.))
        .text_size(px(12.))
        .font_weight(if active {
            FontWeight::SEMIBOLD
        } else {
            FontWeight::MEDIUM
        })
        .bg(rgb(if active { p.accent } else { p.raised }))
        .text_color(rgb(fg))
        .when(!active, |b| b.border_1().border_color(rgb(p.line)))
        .when(disabled, |b| b.opacity(0.45).cursor_default())
        .when(!disabled, |b| {
            b.cursor_pointer().hover(move |style| {
                if active {
                    style.bg(rgb(p.accent_hover))
                } else {
                    style.bg(rgb(p.active)).border_color(rgb(p.accent))
                }
            })
        })
        .child(
            gpui_kit::component::Icon::new(icon)
                .size(px(13.))
                .text_color(rgb(fg)),
        )
        .child(
            div()
                .min_w_0()
                .overflow_hidden()
                .whitespace_nowrap()
                .text_ellipsis()
                .child(label_text),
        )
}

/// Tarjeta equivalente a `shared.components.card` de la interfaz Flet.
pub fn card() -> Div {
    let p = palette();
    column()
        .bg(rgb(p.card))
        .border_1()
        .border_color(rgb(p.line))
        .rounded(px(8.))
        .p(px(12.))
}
/// Chip de estado de la tabla de subtítulos.
pub fn chip(value: impl Into<SharedString>, modified: bool) -> Div {
    let p = palette();
    div()
        .text_size(px(11.))
        .font_weight(FontWeight::SEMIBOLD)
        .text_color(rgb(if modified { p.text } else { p.muted }))
        .bg(rgb(if modified { p.chip } else { p.secondary }))
        .border_1()
        .border_color(rgb(if modified { p.accent_fg } else { p.line }))
        .rounded(px(10.))
        .px_2()
        .py_1()
        .child(value.into())
}
/// Etiqueta de campo: la interfaz Flet las muestra dentro del control.
pub fn field_label(value: impl Into<SharedString>) -> Div {
    div()
        .text_size(px(12.))
        .text_color(rgb(palette().muted))
        .child(value.into())
}
