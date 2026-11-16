#![windows_subsystem = "windows"]

mod app;
mod ui;

use davinci_flow_gpui::{bridge, library, subtitles};

use gpui_kit::component::{Theme, ThemeMode};
use gpui_kit::*;

fn main() {
    gpui_kit::application().run(|cx| {
        gpui_kit::init(cx);
        Theme::change(ThemeMode::Dark, None, cx);
        Theme::update(cx, |theme| {
            theme.font_family = "Segoe UI".into();
            theme.primary = rgb(ui::ACCENT).into();
            theme.primary_hover = rgb(0x19DBC3).into();
            theme.primary_active = rgb(0x00AC99).into();
            theme.primary_foreground = rgb(ui::SIDE).into();
            theme.button_primary = rgb(ui::ACCENT).into();
            theme.button_primary_hover = rgb(0x19DBC3).into();
            theme.button_primary_active = rgb(0x00AC99).into();
            theme.button_primary_foreground = rgb(ui::SIDE).into();
            theme.background = rgb(ui::BG).into();
            theme.foreground = rgb(ui::TEXT).into();
            theme.border = rgb(ui::LINE).into();
            theme.input = rgb(ui::LINE).into();
            theme.ring = rgb(ui::ACCENT).into();
        });
        cx.on_window_closed(|cx, _| {
            if cx.windows().is_empty() {
                cx.quit();
            }
        })
        .detach();
        let options = WindowOptions {
            titlebar: Some(TitlebarOptions {
                title: Some("DaVinci Flow · Demo Rust + GPUI".into()),
                ..Default::default()
            }),
            window_bounds: Some(WindowBounds::Windowed(Bounds::centered(
                None,
                size(px(1280.), px(820.)),
                cx,
            ))),
            window_min_size: Some(size(px(1024.), px(680.))),
            ..Default::default()
        };
        gpui_kit::open_window(options, cx, |window, cx| {
            cx.new(|cx| app::FlowApp::new(window, cx))
        })
        .expect("No se pudo abrir la ventana de DaVinci Flow");
        cx.activate(true);
    });
}
