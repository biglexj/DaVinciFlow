//! Adaptador WinMM MCI y caché WAV temporal vía FFmpeg para el reproductor integrado.
#[cfg(windows)]
use crate::preferences::user_data_dir;
#[cfg(windows)]
use std::collections::hash_map::DefaultHasher;
#[cfg(windows)]
use std::hash::{Hash, Hasher};
#[cfg(windows)]
use std::path::{Path, PathBuf};
#[cfg(windows)]
use std::process::Command;
#[cfg(windows)]
use std::time::UNIX_EPOCH;

#[cfg(windows)]
pub(crate) const MCI_ALIAS: &str = "dvf_audio_player";

#[cfg(windows)]
fn short_windows_path(path: &Path) -> String {
    use std::ffi::OsStr;
    use std::os::windows::ffi::{OsStrExt, OsStringExt};
    #[link(name = "kernel32")]
    unsafe extern "system" {
        fn GetShortPathNameW(lpsz_short: *const u16, lpsz_long: *mut u16, cch_buffer: u32) -> u32;
    }
    let wide: Vec<u16> = OsStr::new(path)
        .encode_wide()
        .chain(std::iter::once(0))
        .collect();
    let mut buffer = vec![0u16; 1024];
    let len = unsafe { GetShortPathNameW(wide.as_ptr(), buffer.as_mut_ptr(), buffer.len() as u32) };
    if len > 0 && (len as usize) < buffer.len() {
        let os = std::ffi::OsString::from_wide(&buffer[..len as usize]);
        let s = os.to_string_lossy().into_owned();
        if !s.is_empty() {
            return s;
        }
    }
    path.to_string_lossy().into_owned()
}

#[cfg(windows)]
pub(crate) fn mci_cmd(command: &str) -> Result<String, String> {
    use std::ffi::OsStr;
    use std::os::windows::ffi::{OsStrExt, OsStringExt};
    #[link(name = "winmm")]
    unsafe extern "system" {
        fn mciSendStringW(
            lpsz_command: *const u16,
            lpsz_return_string: *mut u16,
            cch_return: u32,
            hwnd_callback: isize,
        ) -> u32;
        fn mciGetErrorStringW(
            fdw_error: u32,
            lpsz_error_text: *mut u16,
            cch_error_text: u32,
        ) -> i32;
    }
    let wide: Vec<u16> = OsStr::new(command)
        .encode_wide()
        .chain(std::iter::once(0))
        .collect();
    let mut ret = vec![0u16; 512];
    let code = unsafe { mciSendStringW(wide.as_ptr(), ret.as_mut_ptr(), ret.len() as u32, 0) };
    if code == 0 {
        let nul = ret.iter().position(|&c| c == 0).unwrap_or(ret.len());
        return Ok(std::ffi::OsString::from_wide(&ret[..nul])
            .to_string_lossy()
            .into_owned());
    }
    let mut err_buf = vec![0u16; 512];
    let ok = unsafe { mciGetErrorStringW(code, err_buf.as_mut_ptr(), err_buf.len() as u32) };
    if ok != 0 {
        let nul = err_buf
            .iter()
            .position(|&c| c == 0)
            .unwrap_or(err_buf.len());
        let msg = std::ffi::OsString::from_wide(&err_buf[..nul])
            .to_string_lossy()
            .into_owned();
        return Err(format!("No se pudo reproducir el medio: {msg}"));
    }
    Err(format!("No se pudo reproducir el medio (MCI {code})."))
}

#[cfg(windows)]
pub(crate) fn open_mci_direct(path: &Path) -> Result<(), String> {
    let target = short_windows_path(path);
    let _ = mci_cmd(&format!("close {MCI_ALIAS}"));
    let quoted = target.replace('"', "");
    if mci_cmd(&format!(
        "open \"{quoted}\" type mpegvideo alias {MCI_ALIAS}"
    ))
    .is_ok()
    {
        return Ok(());
    }
    mci_cmd(&format!("open \"{quoted}\" alias {MCI_ALIAS}")).map(|_| ())
}

#[cfg(windows)]
pub(crate) fn transcode_to_wav_cache(path: &Path) -> Result<PathBuf, String> {
    use std::os::windows::process::CommandExt;
    let meta = std::fs::metadata(path)
        .map_err(|_| "No se pudo leer el archivo multimedia.".to_string())?;
    let mtime = meta
        .modified()
        .ok()
        .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    let mut hasher = DefaultHasher::new();
    path.canonicalize()
        .unwrap_or_else(|_| path.to_path_buf())
        .hash(&mut hasher);
    mtime.hash(&mut hasher);
    meta.len().hash(&mut hasher);
    let cache_dir = user_data_dir().join("gpui").join("audio_cache");
    std::fs::create_dir_all(&cache_dir)
        .map_err(|_| "No se pudo preparar la caché temporal de audio.".to_string())?;
    let key = format!("{:016x}", hasher.finish());
    let final_wav = cache_dir.join(format!("{key}.wav"));
    if final_wav.is_file() && final_wav.metadata().map(|m| m.len() > 44).unwrap_or(false) {
        return Ok(final_wav);
    }
    let temp_wav = cache_dir.join(format!("{key}.part.wav"));
    let _ = std::fs::remove_file(&temp_wav);
    let mut cmd = Command::new("ffmpeg");
    cmd.args(["-hide_banner", "-loglevel", "error", "-i"])
        .arg(path)
        .args(["-vn", "-acodec", "pcm_s16le", "-y"])
        .arg(&temp_wav)
        .creation_flags(0x08000000);
    let status = cmd.status().map_err(|_| {
        "Este formato requiere FFmpeg instalado para decodificarlo internamente.".to_string()
    })?;
    if !status.success() || !temp_wav.is_file() {
        let _ = std::fs::remove_file(&temp_wav);
        return Err("FFmpeg no pudo extraer el audio de este archivo.".into());
    }
    std::fs::rename(&temp_wav, &final_wav)
        .map_err(|_| "No se pudo guardar el audio temporal.".to_string())?;
    Ok(final_wav)
}
