//! Descarga y vistas previas mediante las herramientas multimedia del sistema.
use crate::{
    bridge, editorial_config,
    media::{Download, MediaInfo},
};
use reqwest::Url;
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::{
    fs,
    path::{Path, PathBuf},
    process::{Command, Stdio},
    time::{Duration, Instant},
};

const ANALYSIS_TIMEOUT: Duration = Duration::from_secs(120);
const PREVIEW_TIMEOUT: Duration = Duration::from_secs(30);

fn run(mut command: Command, program: &str, timeout: Option<Duration>) -> Result<Vec<u8>, String> {
    command
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null());
    #[cfg(test)]
    if std::env::var_os("DAVINCIFLOW_TEST_MEDIA_DIAGNOSTICS").is_some() {
        command.stderr(Stdio::inherit());
    }
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000); // CREATE_NO_WINDOW
    }
    let mut child = command.spawn().map_err(|error| match error.kind() {
        std::io::ErrorKind::NotFound => format!("{program} no está disponible en PATH."),
        _ => format!("No se pudo iniciar {program}: {error}"),
    })?;
    let stdout = child.stdout.take().expect("stdout configurado");
    let reader = std::thread::spawn(move || bridge::drain_bounded(stdout, 16 * 1024 * 1024 + 1));
    let start = Instant::now();
    let status = loop {
        match child.try_wait() {
            Ok(Some(status)) => break status,
            Ok(None) if timeout.is_none_or(|limit| start.elapsed() < limit) => {
                std::thread::sleep(Duration::from_millis(50));
            }
            other => {
                let _ = child.kill();
                let _ = child.wait();
                return match other {
                    Err(error) => Err(format!("Falló la ejecución de {program}: {error}")),
                    _ => Err(format!("{program} agotó el tiempo de espera.")),
                };
            }
        }
    };
    if !status.success() {
        return Err(format!("{program} terminó con un error ({status})."));
    }
    let data = reader
        .join()
        .ok()
        .and_then(Result::ok)
        .ok_or_else(|| format!("No se pudo leer la salida de {program}."))?;
    if data.len() > 16 * 1024 * 1024 {
        return Err(format!("La salida de {program} supera 16 MiB."));
    }
    Ok(data)
}

fn source_url(input: &str) -> Result<Url, String> {
    let url = Url::parse(input.trim()).map_err(|_| "Ingresa un enlace HTTP o HTTPS válido.")?;
    if !matches!(url.scheme(), "http" | "https")
        || url.host().is_none()
        || !url.username().is_empty()
        || url.password().is_some()
    {
        return Err("Ingresa un enlace HTTP o HTTPS sin credenciales.".into());
    }
    Ok(url)
}

fn yt_dlp() -> Command {
    let mut command = Command::new("yt-dlp");
    command.args([
        "--ignore-config",
        "--no-plugin-dirs",
        "--no-playlist",
        "--playlist-items",
        "1",
        "--abort-on-error",
        "--socket-timeout",
        "20",
        "--encoding",
        "utf-8",
        "--no-warnings",
    ]);
    command
}

fn metadata(url: &Url) -> Result<Value, String> {
    let mut command = yt_dlp();
    command.args(["--skip-download", "--dump-single-json", "--", url.as_str()]);
    let bytes = run(command, "yt-dlp", Some(ANALYSIS_TIMEOUT))?;
    let value: Value =
        serde_json::from_slice(&bytes).map_err(|_| "yt-dlp no devolvió metadatos válidos.")?;
    if !value.is_object()
        || value.get("entries").is_some()
        || matches!(value["_type"].as_str(), Some("playlist" | "multi_video"))
    {
        return Err("Usa el enlace de un único vídeo o audio.".into());
    }
    Ok(value)
}

fn nonempty(value: &Value) -> Option<String> {
    value
        .as_str()
        .filter(|text| !text.trim().is_empty())
        .map(str::to_owned)
}

pub(crate) fn analyze(input: &str) -> Result<MediaInfo, String> {
    let data = metadata(&source_url(input)?)?;
    let duration = data["duration"].as_f64().unwrap_or_default().max(0.0);
    let seconds = duration as u64;
    let is_audio = matches!(data["extractor"].as_str(), Some("soundcloud" | "suno"))
        || data["formats"].as_array().is_some_and(|formats| {
            let mut candidates = formats
                .iter()
                .filter(|item| item["url"].is_string())
                .peekable();
            candidates.peek().is_some() && candidates.all(|item| item["vcodec"] == "none")
        });
    Ok(MediaInfo {
        title: nonempty(&data["title"]).unwrap_or_else(|| "Sin título".into()),
        duration_seconds: duration,
        duration_display: if duration > 0.0 {
            format!("{}:{:02}", seconds / 60, seconds % 60)
        } else {
            "--:--".into()
        },
        uploader: nonempty(&data["uploader"]).or_else(|| nonempty(&data["channel"])),
        extractor: nonempty(&data["extractor"]),
        thumbnail_url: nonempty(&data["thumbnail"]),
        is_audio,
    })
}

fn destination(directory: &str, kind: &str) -> Result<PathBuf, String> {
    let base = if directory.trim().is_empty() {
        let home = std::env::home_dir().ok_or("No se encontró la carpeta del usuario.")?;
        let downloads = home.join("Downloads");
        if downloads.is_dir() { downloads } else { home }.join("LunaFetch")
    } else {
        PathBuf::from(directory.trim())
    };
    let name = base
        .file_name()
        .and_then(|s| s.to_str())
        .unwrap_or_default()
        .to_lowercase();
    let folder = if kind == "audio" {
        if matches!(name.as_str(), "música" | "musica" | "audio") {
            base
        } else {
            base.join("Música")
        }
    } else if matches!(name.as_str(), "videos" | "video") {
        base
    } else {
        base.join("Videos")
    };
    fs::create_dir_all(&folder)
        .map_err(|error| format!("No se pudo crear la carpeta de descargas: {error}"))?;
    std::path::absolute(folder).map_err(|error| format!("Ruta de descargas inválida: {error}"))
}

pub(crate) fn download(input: &str, kind: &str, directory: &str) -> Result<Download, String> {
    let url = source_url(input)?;
    let ffmpeg = run(ffmpeg_version(), "FFmpeg", Some(Duration::from_secs(10))).is_ok();
    if kind == "audio" && !ffmpeg {
        return Err("FFmpeg no está disponible para convertir el audio.".into());
    }
    let source = metadata(&url)?;
    let folder = destination(directory, kind)?;
    let mut command = yt_dlp();
    command
        .args([
            "--no-simulate",
            "--no-overwrites",
            "--no-progress",
            "--print",
            "after_move:%(.{filepath,title})j",
            "-P",
        ])
        .arg(&folder)
        .args(["-o", "%(title).180B [%(id)s].%(ext)s"]);
    if kind == "audio" {
        command.args([
            "-f",
            "bestaudio/best",
            "-x",
            "--audio-format",
            "mp3",
            "--audio-quality",
            "192",
        ]);
    } else if ffmpeg {
        command.args([
            "-f",
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format",
            "mp4",
        ]);
    } else {
        command.args(["-f", "best[ext=mp4][vcodec!=none][acodec!=none]"]);
    }
    command.args(["--", url.as_str()]);
    let bytes = run(command, "yt-dlp", None)?;
    let result: Value = serde_json::from_slice(&bytes)
        .map_err(|_| "yt-dlp no confirmó un único archivo descargado.")?;
    let path = result["filepath"]
        .as_str()
        .map(PathBuf::from)
        .ok_or("yt-dlp no confirmó la ruta del archivo descargado.")?;
    if !is_nonempty(&path)
        || !path
            .canonicalize()
            .is_ok_and(|file| folder.canonicalize().is_ok_and(|dir| file.starts_with(dir)))
    {
        return Err(
            "La descarga no produjo un archivo válido dentro de la carpeta elegida.".into(),
        );
    }
    Ok(Download {
        path,
        title: nonempty(&result["title"])
            .or_else(|| nonempty(&source["title"]))
            .unwrap_or_else(|| "Sin título".into()),
        kind: kind.into(),
        imported: false,
        resolve_bin: String::new(),
        message: String::new(),
    })
}

fn ffmpeg_version() -> Command {
    let mut command = Command::new("ffmpeg");
    command.arg("-version");
    command
}

fn is_nonempty(path: &Path) -> bool {
    path.metadata()
        .is_ok_and(|file| file.is_file() && file.len() > 0)
}

fn extension(path: &Path) -> String {
    path.extension()
        .and_then(|s| s.to_str())
        .unwrap_or_default()
        .to_ascii_lowercase()
}

pub(crate) fn validate_voice(source: &Path) -> Result<PathBuf, String> {
    if !is_nonempty(source) {
        return Err("Selecciona un archivo de audio existente y con contenido.".into());
    }
    if !matches!(
        extension(source).as_str(),
        "wav" | "mp3" | "flac" | "m4a" | "aac" | "ogg" | "aiff" | "aif"
    ) {
        return Err(
            "El formato del archivo no es un audio compatible con esta importación.".into(),
        );
    }
    std::path::absolute(source).map_err(|_| "La ruta del archivo de audio no es válida.".into())
}

pub(crate) fn preview(source: &Path) -> Result<PathBuf, String> {
    preview_in(source, &editorial_config::data_dir().join("gpui/previews"))
}

fn preview_in(source: &Path, folder: &Path) -> Result<PathBuf, String> {
    let source = std::path::absolute(source).map_err(|_| "Ruta de recurso inválida.")?;
    if !is_nonempty(&source) {
        return Err("El recurso ya no existe o está vacío.".into());
    }
    if matches!(extension(&source).as_str(), "png" | "jpg" | "jpeg" | "webp") {
        return Ok(source);
    }
    let info = source
        .metadata()
        .map_err(|_| "No se pudieron leer los datos del recurso.")?;
    let stamp = format!(
        "{}:{:?}:{}",
        source.display(),
        info.modified().ok(),
        info.len()
    );
    let hash = format!("{:x}", Sha256::digest(stamp.as_bytes()));
    fs::create_dir_all(folder).map_err(|error| format!("No se pudo crear la caché: {error}"))?;
    let output = folder.join(format!("{hash}.jpg"));
    if is_nonempty(&output) {
        return Ok(output);
    }

    let pending = tempfile::Builder::new()
        .suffix(".jpg")
        .tempfile_in(folder)
        .map_err(|error| format!("No se pudo preparar la vista previa: {error}"))?
        .into_temp_path();
    let mut command = Command::new("ffmpeg");
    command
        .args([
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-protocol_whitelist",
            "file,pipe",
            "-i",
        ])
        .arg(&source)
        .args([
            "-frames:v",
            "1",
            "-vf",
            "scale=480:-2",
            "-f",
            "image2",
            "-y",
        ])
        .arg(&pending);
    run(command, "FFmpeg", Some(PREVIEW_TIMEOUT))?;
    if !is_nonempty(&pending) {
        return Err("El recurso no contiene una imagen de previsualización disponible.".into());
    }
    pending
        .persist(&output)
        .map_err(|error| format!("No se pudo guardar la vista previa: {}", error.error))?;
    Ok(output)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_input_urls_without_a_process() {
        for unsupported in [
            "file:///C:/media.mp4",
            "https://user:pass@example.org/file",
            "--exec",
        ] {
            assert!(source_url(unsupported).is_err());
        }
        assert!(source_url("https://example.org/film.mp4").is_ok());
    }

    #[test]
    #[ignore = "requiere FFmpeg en PATH"]
    fn extracts_and_reuses_a_real_preview() {
        let directory = tempfile::tempdir().unwrap();
        let input = sample_video(directory.path());
        let cache = directory.path().join("cache");
        let thumbnail = preview_in(&input, &cache).unwrap();
        assert!(fs::read(&thumbnail).unwrap().starts_with(&[0xff, 0xd8]));
        assert_eq!(preview_in(&input, &cache).unwrap(), thumbnail);
    }

    fn sample_video(directory: &Path) -> PathBuf {
        const FRAME: usize = 160 * 120 * 3;
        let raw = directory.join("frame.rgb");
        fs::write(&raw, [24u8, 120, 80].repeat(FRAME / 3)).unwrap();
        let input = directory.join("vídeo de prueba.mp4");
        let mut command = Command::new("ffmpeg");
        command
            .args([
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "rawvideo",
                "-pixel_format",
                "rgb24",
                "-video_size",
                "160x120",
                "-i",
            ])
            .arg(raw)
            .args(["-c:v", "mpeg4"])
            .arg(&input);
        run(command, "FFmpeg", Some(PREVIEW_TIMEOUT)).unwrap();
        input
    }

    #[test]
    #[ignore = "requiere FFmpeg y yt-dlp en PATH"]
    fn inspects_and_downloads_a_fixture_over_loopback() {
        use std::{
            io::{BufRead, BufReader, Write},
            net::TcpListener,
        };

        let directory = tempfile::tempdir().unwrap();
        let fixture = fs::read(sample_video(directory.path())).unwrap();
        let size = fixture.len();
        let server = TcpListener::bind("127.0.0.1:0").unwrap();
        server.set_nonblocking(true).unwrap();
        let url = format!("http://{}/fixture.mp4", server.local_addr().unwrap());
        let (stop, stop_requested) = std::sync::mpsc::channel();
        let worker = std::thread::spawn(move || {
            while let Err(std::sync::mpsc::TryRecvError::Empty) = stop_requested.try_recv() {
                let Ok((mut stream, _)) = server.accept() else {
                    std::thread::sleep(Duration::from_millis(10));
                    continue;
                };
                stream.set_nonblocking(false).unwrap();
                stream
                    .set_read_timeout(Some(Duration::from_secs(3)))
                    .unwrap();
                let mut reader = BufReader::new(&stream);
                let mut request = String::new();
                let _ = reader.read_line(&mut request);
                loop {
                    let mut line = String::new();
                    if reader.read_line(&mut line).unwrap_or(0) == 0 || line == "\r\n" {
                        break;
                    }
                }
                let header = format!(
                    "HTTP/1.1 200 OK\r\nContent-Type: video/mp4\r\nContent-Length: {size}\r\nConnection: close\r\n\r\n"
                );
                let _ = stream.write_all(header.as_bytes());
                if request.starts_with("GET ") {
                    let _ = stream.write_all(&fixture);
                }
            }
        });
        let metadata = analyze(&url);
        let result = download(&url, "video", directory.path().to_str().unwrap());
        let _ = stop.send(());
        worker.join().unwrap();
        assert!(!metadata.unwrap().title.is_empty());
        let result = result.unwrap();
        assert_eq!(result.path.metadata().unwrap().len(), size as u64);
        assert!(result.path.starts_with(directory.path().join("Videos")));
    }
}
