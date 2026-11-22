#![windows_subsystem = "windows"]

mod app;
mod ui;

use davinci_flow_gpui::{bridge, library, preferences, subtitles};

use gpui_kit::*;
use std::borrow::Cow;

/// Recursos de la ventana: el catálogo de iconos y la marca del proyecto.
struct AppAssets;

impl AssetSource for AppAssets {
    fn load(&self, path: &str) -> Result<Option<Cow<'static, [u8]>>> {
        if path == BRANDING_PATH {
            return Ok(Some(Cow::Borrowed(BRANDING)));
        }
        gpui_kit::assets::AllAssets.load(path)
    }

    fn list(&self, path: &str) -> Result<Vec<SharedString>> {
        gpui_kit::assets::AllAssets.list(path)
    }
}

const BRANDING_PATH: &str = "branding/icon-transparent.png";
static BRANDING: &[u8] = include_bytes!("../../assets/branding/icons/icon-transparent.png");
#[cfg(windows)]
static WINDOW_ICON_ICO: &[u8] = include_bytes!("../../assets/branding/icons/icon-windows.ico");

#[cfg(windows)]
fn apply_windows_window_icon() {
    use std::ffi::OsStr;
    use std::os::windows::ffi::OsStrExt;
    #[link(name = "user32")]
    unsafe extern "system" {
        fn GetActiveWindow() -> isize;
        fn GetForegroundWindow() -> isize;
        fn LoadImageW(
            hinst: isize,
            name: *const u16,
            r#type: u32,
            cx: i32,
            cy: i32,
            fuload: u32,
        ) -> isize;
        fn SendMessageW(hwnd: isize, msg: u32, wparam: usize, lparam: isize) -> isize;
    }
    const IMAGE_ICON: u32 = 1;
    const LR_LOADFROMFILE: u32 = 0x0000_0010;
    const LR_DEFAULTSIZE: u32 = 0x0000_0040;
    const WM_SETICON: u32 = 0x0080;
    const ICON_SMALL: usize = 0;
    const ICON_BIG: usize = 1;

    let icon_path = preferences::user_data_dir().join("app-icon.ico");
    if let Some(parent) = icon_path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    if !icon_path.is_file() {
        let _ = std::fs::write(&icon_path, WINDOW_ICON_ICO);
    }
    let wide: Vec<u16> = OsStr::new(&icon_path)
        .encode_wide()
        .chain(std::iter::once(0))
        .collect();
    unsafe {
        let mut hwnd = GetActiveWindow();
        if hwnd == 0 {
            hwnd = GetForegroundWindow();
        }
        if hwnd == 0 {
            return;
        }
        let hicon_big = LoadImageW(
            0,
            wide.as_ptr(),
            IMAGE_ICON,
            256,
            256,
            LR_LOADFROMFILE | LR_DEFAULTSIZE,
        );
        let hicon_small = LoadImageW(0, wide.as_ptr(), IMAGE_ICON, 32, 32, LR_LOADFROMFILE);
        if hicon_big != 0 {
            SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big);
        }
        if hicon_small != 0 {
            SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small);
        } else if hicon_big != 0 {
            SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_big);
        }
    }
}

fn main() {
    gpui_kit::application().with_assets(AppAssets).run(|cx| {
        gpui_kit::init(cx);
        let initial_prefs = preferences::Preferences::load();
        ui::apply_gpui_theme(
            &initial_prefs.appearance_theme,
            &initial_prefs.appearance_mode,
            None,
            cx,
        );
        cx.on_window_closed(|cx, _| {
            if cx.windows().is_empty() {
                cx.quit();
            }
        })
        .detach();
        let title = if preferences::is_development() {
            "DaVinci Flow (Desarrollo)"
        } else {
            "DaVinci Flow"
        };
        let options = WindowOptions {
            titlebar: Some(TitlebarOptions {
                title: Some(title.into()),
                ..Default::default()
            }),
            window_bounds: Some(WindowBounds::Windowed(Bounds::centered(
                None,
                size(px(1280.), px(900.)),
                cx,
            ))),
            window_min_size: Some(size(px(900.), px(640.))),
            app_id: Some("com.biglexj.davinciflow".into()),
            ..Default::default()
        };
        gpui_kit::open_window(options, cx, |window, cx| {
            #[cfg(windows)]
            apply_windows_window_icon();
            cx.new(|cx| app::FlowApp::new(window, cx))
        })
        .expect("No se pudo abrir la ventana de DaVinci Flow");
        cx.activate(true);
        #[cfg(windows)]
        apply_windows_window_icon();
    });
}
