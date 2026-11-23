//! Decodificador y transmisor de fotogramas de vídeo integrado sobre FFmpeg.
use std::collections::VecDeque;
use std::io::{BufReader, Read};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::{
    Arc, Mutex,
    atomic::{AtomicU64, Ordering},
};
use std::time::Duration;

const VIDEO_EXTENSIONS: &[&str] = &[
    "mp4", "mov", "mkv", "webm", "avi", "m4v", "wmv", "flv", "mpg", "mpeg", "ts",
];

pub const VIDEO_FPS: u64 = 20;
const MAX_BUFFERED_FRAMES: usize = 30;

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct VideoProbe {
    pub duration_ms: u64,
    pub has_audio: bool,
}

pub fn is_video_path(path: &Path) -> bool {
    path.extension()
        .and_then(|ext| ext.to_str())
        .map(|ext| VIDEO_EXTENSIONS.contains(&ext.to_ascii_lowercase().as_str()))
        .unwrap_or(false)
}

pub fn probe_video(path: &Path) -> VideoProbe {
    if let Some(probed) = probe_with_ffprobe(path) {
        return probed;
    }
    probe_with_ffmpeg_stderr(path).unwrap_or_default()
}

fn probe_with_ffprobe(path: &Path) -> Option<VideoProbe> {
    let mut cmd = Command::new("ffprobe");
    cmd.args([
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=codec_type",
        "-of",
        "default=noprint_wrappers=1",
    ])
    .arg(path)
    .stdout(Stdio::piped())
    .stderr(Stdio::null());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x08000000);
    }
    let output = cmd.output().ok()?;
    if !output.status.success() {
        return None;
    }
    let text = String::from_utf8_lossy(&output.stdout);
    let mut duration_ms = 0u64;
    let mut has_audio = false;
    for line in text.lines() {
        let trimmed = line.trim();
        if let Some(val) = trimmed.strip_prefix("duration=")
            && let Ok(secs) = val.parse::<f64>()
            && secs.is_finite()
            && secs > 0.0
        {
            duration_ms = (secs * 1000.0).round() as u64;
        } else if trimmed == "codec_type=audio" {
            has_audio = true;
        }
    }
    Some(VideoProbe {
        duration_ms,
        has_audio,
    })
}

fn probe_with_ffmpeg_stderr(path: &Path) -> Option<VideoProbe> {
    let mut cmd = Command::new("ffmpeg");
    cmd.args(["-hide_banner", "-i"])
        .arg(path)
        .stdout(Stdio::null())
        .stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x08000000);
    }
    let output = cmd.output().ok()?;
    let stderr = String::from_utf8_lossy(&output.stderr);
    let mut duration_ms = 0u64;
    let mut has_audio = false;
    for line in stderr.lines() {
        if let Some(idx) = line.find("Duration:") {
            let rest = line[idx + "Duration:".len()..].trim();
            if let Some(raw) = rest.split(',').next()
                && let Some(ms) = parse_ffmpeg_duration(raw.trim())
            {
                duration_ms = ms;
            }
        }
        if line.contains("Audio:") {
            has_audio = true;
        }
    }
    Some(VideoProbe {
        duration_ms,
        has_audio,
    })
}

pub fn parse_ffmpeg_duration(raw: &str) -> Option<u64> {
    let mut parts = raw.split(':');
    let hours: u64 = parts.next()?.parse().ok()?;
    let mins: u64 = parts.next()?.parse().ok()?;
    let secs: f64 = parts.next()?.parse().ok()?;
    if !secs.is_finite() || secs < 0.0 {
        return None;
    }
    let total = (hours * 3600 + mins * 60) as f64 + secs;
    Some((total * 1000.0).round() as u64)
}

#[derive(Default)]
struct StreamBuffer {
    frames: VecDeque<(u64, Vec<u8>)>,
    child: Option<Child>,
    error: Option<String>,
}

pub struct VideoStreamer {
    generation: Arc<AtomicU64>,
    buffer: Arc<Mutex<StreamBuffer>>,
}

impl Default for VideoStreamer {
    fn default() -> Self {
        Self::new()
    }
}

impl VideoStreamer {
    pub fn new() -> Self {
        Self {
            generation: Arc::new(AtomicU64::new(0)),
            buffer: Arc::new(Mutex::new(StreamBuffer::default())),
        }
    }

    pub fn stop(&self) {
        self.generation.fetch_add(1, Ordering::SeqCst);
        if let Ok(mut guard) = self.buffer.lock() {
            if let Some(mut child) = guard.child.take() {
                let _ = child.kill();
                let _ = child.wait();
            }
            guard.frames.clear();
            guard.error = None;
        }
    }

    pub fn start(&self, path: PathBuf, start_ms: u64) {
        let epoch = self.generation.fetch_add(1, Ordering::SeqCst) + 1;
        if let Ok(mut guard) = self.buffer.lock() {
            if let Some(mut child) = guard.child.take() {
                let _ = child.kill();
                let _ = child.wait();
            }
            guard.frames.clear();
            guard.error = None;
        }

        let gen_ref = Arc::clone(&self.generation);
        let buf_ref = Arc::clone(&self.buffer);
        let _ = std::thread::Builder::new()
            .name("dvf-video-stream".into())
            .spawn(move || stream_worker(path, start_ms, epoch, gen_ref, buf_ref));
    }

    /// Toma el fotograma más reciente cuyo PTS sea <= position_ms + margen, o el primero disponible si aún no se ha pintado ninguno.
    pub fn take_frame_for(&self, position_ms: u64, needs_initial: bool) -> Option<(u64, Vec<u8>)> {
        let mut guard = self.buffer.lock().ok()?;
        let mut chosen = None;
        while let Some(&(pts, _)) = guard.frames.front() {
            if pts <= position_ms.saturating_add(35) {
                chosen = guard.frames.pop_front();
            } else {
                break;
            }
        }
        if chosen.is_none() && needs_initial {
            chosen = guard.frames.pop_front();
        }
        chosen
    }

    pub fn error(&self) -> Option<String> {
        self.buffer.lock().ok().and_then(|g| g.error.clone())
    }
}

impl Drop for VideoStreamer {
    fn drop(&mut self) {
        self.stop();
    }
}

fn stream_worker(
    path: PathBuf,
    start_ms: u64,
    epoch: u64,
    gen_ref: Arc<AtomicU64>,
    buf_ref: Arc<Mutex<StreamBuffer>>,
) {
    let start_sec = format!("{:.3}", start_ms as f64 / 1000.0);
    let vf = format!("fps={VIDEO_FPS},scale=640:-2:flags=fast_bilinear");
    let mut cmd = Command::new("ffmpeg");
    cmd.args([
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        &start_sec,
        "-i",
    ])
    .arg(&path)
    .args([
        "-an",
        "-vf",
        &vf,
        "-f",
        "image2pipe",
        "-vcodec",
        "mjpeg",
        "-q:v",
        "6",
        "-",
    ])
    .stdin(Stdio::null())
    .stdout(Stdio::piped())
    .stderr(Stdio::null());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x08000000);
    }

    let mut child = match cmd.spawn() {
        Ok(c) => c,
        Err(_) => {
            if gen_ref.load(Ordering::SeqCst) == epoch
                && let Ok(mut g) = buf_ref.lock()
            {
                g.error =
                    Some("FFmpeg no está disponible para reproducir vídeo internamente.".into());
            }
            return;
        }
    };

    let Some(stdout) = child.stdout.take() else {
        let _ = child.kill();
        let _ = child.wait();
        return;
    };

    {
        let Ok(mut guard) = buf_ref.lock() else {
            let _ = child.kill();
            let _ = child.wait();
            return;
        };
        if gen_ref.load(Ordering::SeqCst) != epoch {
            let _ = child.kill();
            let _ = child.wait();
            return;
        }
        guard.child = Some(child);
    }

    let mut reader = BufReader::with_capacity(64 * 1024, stdout);
    let mut chunk = [0u8; 16 * 1024];
    let mut pending = Vec::<u8>::with_capacity(64 * 1024);
    let mut frame_index = 0u64;

    loop {
        if gen_ref.load(Ordering::SeqCst) != epoch {
            break;
        }
        // Contrapresión ligera para mantener acotada la memoria en vídeos largos.
        loop {
            if gen_ref.load(Ordering::SeqCst) != epoch {
                return;
            }
            let len = buf_ref.lock().map(|g| g.frames.len()).unwrap_or(0);
            if len < MAX_BUFFERED_FRAMES {
                break;
            }
            std::thread::sleep(Duration::from_millis(18));
        }

        let read = match reader.read(&mut chunk) {
            Ok(0) | Err(_) => break,
            Ok(n) => n,
        };
        pending.extend_from_slice(&chunk[..read]);

        while let Some((start, end)) = find_jpeg_frame(&pending) {
            let frame_bytes = pending[start..=end].to_vec();
            pending.drain(..=end);
            let pts_ms = start_ms.saturating_add(frame_index.saturating_mul(1000) / VIDEO_FPS);
            frame_index += 1;
            if gen_ref.load(Ordering::SeqCst) != epoch {
                return;
            }
            if let Ok(mut guard) = buf_ref.lock() {
                guard.frames.push_back((pts_ms, frame_bytes));
            }
        }
        // Evitar crecimiento indefinido si llegaran bytes corruptos sin SOI.
        if pending.len() > 2 * 1024 * 1024 {
            pending.clear();
        }
    }

    if let Ok(mut guard) = buf_ref.lock()
        && gen_ref.load(Ordering::SeqCst) == epoch
        && let Some(mut c) = guard.child.take()
    {
        let _ = c.wait();
    }
}

fn find_jpeg_frame(buf: &[u8]) -> Option<(usize, usize)> {
    let start = buf.windows(2).position(|w| w == [0xFF, 0xD8])?;
    let rel_end = buf[start + 2..]
        .windows(2)
        .position(|w| w == [0xFF, 0xD9])?;
    Some((start, start + 2 + rel_end + 1))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn recognizes_video_extensions_case_insensitively() {
        assert!(is_video_path(Path::new("broll.MP4")));
        assert!(is_video_path(Path::new("clip.mov")));
        assert!(is_video_path(Path::new("descarga.webm")));
        assert!(is_video_path(Path::new("escena.mkv")));
        assert!(!is_video_path(Path::new("musica.mp3")));
        assert!(!is_video_path(Path::new("foto.png")));
    }

    #[test]
    fn parses_ffmpeg_duration_strings() {
        assert_eq!(parse_ffmpeg_duration("00:00:12.50"), Some(12_500));
        assert_eq!(parse_ffmpeg_duration("01:02:03.25"), Some(3_723_250));
        assert_eq!(parse_ffmpeg_duration("N/A"), None);
    }

    #[test]
    fn extracts_jpeg_frames_from_stream_buffer() {
        let data = vec![0x00, 0xFF, 0xD8, 0x01, 0x02, 0xFF, 0xD9, 0xFF, 0xD8];
        assert_eq!(find_jpeg_frame(&data), Some((1, 6)));
    }
}
