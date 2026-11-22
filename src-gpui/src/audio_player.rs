//! Motor integrado de reproducción multimedia (música, audio, SFX, voz y vídeo con o sin audio).
#[cfg(windows)]
use crate::audio_mci::{MCI_ALIAS, mci_cmd, open_mci_direct, transcode_to_wav_cache};
use crate::video_player;
use std::path::{Path, PathBuf};
use std::sync::{
    Arc, Mutex,
    mpsc::{self, RecvTimeoutError, Sender},
};
use std::time::{Duration, Instant};

const AUDIO_EXTENSIONS: &[&str] = &[
    "wav", "mp3", "m4a", "aac", "flac", "ogg", "opus", "wma", "aiff", "aif", "alac",
];

#[derive(Clone, Copy, PartialEq, Eq, Debug, Default)]
pub enum PlaybackStatus {
    #[default]
    Stopped,
    Loading,
    Playing,
    Paused,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AudioTrack {
    pub path: PathBuf,
    pub title: String,
    pub kind: String,
    pub is_video: bool,
}

#[derive(Clone, Debug)]
pub struct PlayerSnapshot {
    pub current: Option<AudioTrack>,
    pub queue: Vec<AudioTrack>,
    pub queue_index: Option<usize>,
    pub status: PlaybackStatus,
    pub position_ms: u64,
    pub duration_ms: u64,
    pub volume: u8,
    pub muted: bool,
    pub loop_track: bool,
    pub has_audio: bool,
    pub stream_epoch: u64,
    pub error: Option<String>,
}

impl Default for PlayerSnapshot {
    fn default() -> Self {
        Self {
            current: None,
            queue: Vec::new(),
            queue_index: None,
            status: PlaybackStatus::Stopped,
            position_ms: 0,
            duration_ms: 0,
            volume: 85,
            muted: false,
            loop_track: false,
            has_audio: true,
            stream_epoch: 0,
            error: None,
        }
    }
}

enum PlayerCommand {
    Play {
        track: AudioTrack,
        queue: Vec<AudioTrack>,
        queue_index: Option<usize>,
    },
    TogglePause,
    Stop {
        keep_track: bool,
    },
    SeekMs(u64),
    SeekDeltaMs(i64),
    SetVolume(u8),
    ToggleMute,
    ToggleLoop,
    NextTrack,
    PrevTrack,
    Shutdown,
}

pub fn is_audio_path(path: &Path) -> bool {
    path.extension()
        .and_then(|ext| ext.to_str())
        .map(|ext| AUDIO_EXTENSIONS.contains(&ext.to_ascii_lowercase().as_str()))
        .unwrap_or(false)
}

pub fn format_ms(ms: u64) -> String {
    let total_secs = ms / 1000;
    let hours = total_secs / 3600;
    let mins = (total_secs % 3600) / 60;
    let secs = total_secs % 60;
    if hours > 0 {
        format!("{hours:02}:{mins:02}:{secs:02}")
    } else {
        format!("{mins:02}:{secs:02}")
    }
}

pub struct AudioPlayer {
    tx: Sender<PlayerCommand>,
    state: Arc<Mutex<PlayerSnapshot>>,
    handle: Option<std::thread::JoinHandle<()>>,
}

impl Default for AudioPlayer {
    fn default() -> Self {
        Self::new()
    }
}

impl AudioPlayer {
    pub fn new() -> Self {
        let (tx, rx) = mpsc::channel::<PlayerCommand>();
        let state = Arc::new(Mutex::new(PlayerSnapshot::default()));
        let worker_state = Arc::clone(&state);
        let handle = std::thread::Builder::new()
            .name("dvf-media-player".into())
            .spawn(move || worker_loop(rx, worker_state))
            .ok();
        Self { tx, state, handle }
    }

    pub fn snapshot(&self) -> PlayerSnapshot {
        self.state
            .lock()
            .map(|guard| guard.clone())
            .unwrap_or_default()
    }

    pub fn play(&self, track: AudioTrack, queue: Vec<AudioTrack>, queue_index: Option<usize>) {
        let _ = self.tx.send(PlayerCommand::Play {
            track,
            queue,
            queue_index,
        });
    }

    pub fn toggle_pause(&self) {
        let _ = self.tx.send(PlayerCommand::TogglePause);
    }

    pub fn stop(&self, keep_track: bool) {
        let _ = self.tx.send(PlayerCommand::Stop { keep_track });
    }

    pub fn seek_ms(&self, ms: u64) {
        let _ = self.tx.send(PlayerCommand::SeekMs(ms));
    }

    pub fn seek_delta_ms(&self, delta_ms: i64) {
        let _ = self.tx.send(PlayerCommand::SeekDeltaMs(delta_ms));
    }

    pub fn set_volume(&self, volume: u8) {
        let _ = self.tx.send(PlayerCommand::SetVolume(volume.min(100)));
    }

    pub fn toggle_mute(&self) {
        let _ = self.tx.send(PlayerCommand::ToggleMute);
    }

    pub fn toggle_loop(&self) {
        let _ = self.tx.send(PlayerCommand::ToggleLoop);
    }

    pub fn next_track(&self) {
        let _ = self.tx.send(PlayerCommand::NextTrack);
    }

    pub fn prev_track(&self) {
        let _ = self.tx.send(PlayerCommand::PrevTrack);
    }
}

impl Drop for AudioPlayer {
    fn drop(&mut self) {
        let _ = self.tx.send(PlayerCommand::Shutdown);
        if let Some(handle) = self.handle.take() {
            let _ = handle.join();
        }
    }
}

enum ClockMode {
    Closed,
    MciAudio,
    SilentClock {
        duration_ms: u64,
        base_ms: u64,
        started_at: Option<Instant>,
    },
}

struct Backend {
    mode: ClockMode,
}

impl Backend {
    fn new() -> Self {
        Self {
            mode: ClockMode::Closed,
        }
    }

    fn effective_mci_volume(volume: u8, muted: bool) -> u32 {
        if muted {
            0
        } else {
            u32::from(volume.min(100)) * 10
        }
    }

    fn is_open(&self) -> bool {
        !matches!(self.mode, ClockMode::Closed)
    }

    fn open_track(
        &mut self,
        track: &AudioTrack,
        volume: u8,
        muted: bool,
    ) -> Result<(u64, bool), String> {
        self.close();
        if track.is_video {
            let probe = video_player::probe_video(&track.path);
            if probe.has_audio
                && let Ok(audio_dur) = self.open_mci_audio(&track.path, volume, muted, true)
            {
                return Ok((audio_dur.max(probe.duration_ms), true));
            }
            self.mode = ClockMode::SilentClock {
                duration_ms: probe.duration_ms,
                base_ms: 0,
                started_at: Some(Instant::now()),
            };
            return Ok((probe.duration_ms, false));
        }
        let duration_ms = self.open_mci_audio(&track.path, volume, muted, false)?;
        Ok((duration_ms, true))
    }

    #[cfg(windows)]
    fn open_mci_audio(
        &mut self,
        path: &Path,
        volume: u8,
        muted: bool,
        prefer_transcode: bool,
    ) -> Result<u64, String> {
        let opened_path = if prefer_transcode {
            transcode_to_wav_cache(path)?
        } else {
            match open_mci_direct(path) {
                Ok(()) => {
                    self.mode = ClockMode::MciAudio;
                    return self.finish_mci_open(volume, muted);
                }
                Err(first_err) => match transcode_to_wav_cache(path) {
                    Ok(cached) => cached,
                    Err(conv_err) => return Err(format!("{first_err}. {conv_err}")),
                },
            }
        };
        open_mci_direct(&opened_path)?;
        self.mode = ClockMode::MciAudio;
        self.finish_mci_open(volume, muted)
    }

    #[cfg(windows)]
    fn finish_mci_open(&mut self, volume: u8, muted: bool) -> Result<u64, String> {
        let _ = mci_cmd(&format!("set {MCI_ALIAS} time format milliseconds"));
        let duration_ms = mci_cmd(&format!("status {MCI_ALIAS} length"))
            .ok()
            .and_then(|raw| raw.trim().parse::<u64>().ok())
            .unwrap_or(0);
        let vol = Self::effective_mci_volume(volume, muted);
        let _ = mci_cmd(&format!("setaudio {MCI_ALIAS} volume to {vol}"));
        mci_cmd(&format!("play {MCI_ALIAS} from 0"))?;
        Ok(duration_ms)
    }

    #[cfg(not(windows))]
    fn open_mci_audio(
        &mut self,
        _path: &Path,
        _volume: u8,
        _muted: bool,
        _prefer_transcode: bool,
    ) -> Result<u64, String> {
        Err("La reproducción integrada en esta compilación requiere Windows.".into())
    }

    fn play_from(&mut self, pos_ms: u64) -> Result<(), String> {
        match &mut self.mode {
            ClockMode::Closed => Err("No hay medio cargado.".into()),
            ClockMode::MciAudio => {
                #[cfg(windows)]
                {
                    mci_cmd(&format!("play {MCI_ALIAS} from {pos_ms}"))?;
                }
                Ok(())
            }
            ClockMode::SilentClock {
                duration_ms,
                base_ms,
                started_at,
            } => {
                *base_ms = if *duration_ms > 0 {
                    pos_ms.min(*duration_ms)
                } else {
                    pos_ms
                };
                *started_at = Some(Instant::now());
                Ok(())
            }
        }
    }

    fn pause(&mut self) -> Option<u64> {
        match &mut self.mode {
            ClockMode::Closed => None,
            ClockMode::MciAudio => {
                #[cfg(windows)]
                {
                    let pos = self.position_ms();
                    let _ = mci_cmd(&format!("pause {MCI_ALIAS}"));
                    Some(pos)
                }
                #[cfg(not(windows))]
                None
            }
            ClockMode::SilentClock {
                duration_ms,
                base_ms,
                started_at,
            } => {
                if let Some(t0) = started_at.take() {
                    let elapsed = t0.elapsed().as_millis() as u64;
                    let next = base_ms.saturating_add(elapsed);
                    *base_ms = if *duration_ms > 0 {
                        next.min(*duration_ms)
                    } else {
                        next
                    };
                }
                Some(*base_ms)
            }
        }
    }

    fn seek(&mut self, pos_ms: u64, playing: bool) {
        match &mut self.mode {
            ClockMode::Closed => {}
            ClockMode::MciAudio => {
                #[cfg(windows)]
                {
                    if playing {
                        let _ = mci_cmd(&format!("play {MCI_ALIAS} from {pos_ms}"));
                    } else {
                        let _ = mci_cmd(&format!("seek {MCI_ALIAS} to {pos_ms}"));
                    }
                }
            }
            ClockMode::SilentClock {
                duration_ms,
                base_ms,
                started_at,
            } => {
                *base_ms = if *duration_ms > 0 {
                    pos_ms.min(*duration_ms)
                } else {
                    pos_ms
                };
                *started_at = playing.then(Instant::now);
            }
        }
    }

    fn apply_volume(&self, volume: u8, muted: bool) {
        if matches!(self.mode, ClockMode::MciAudio) {
            #[cfg(windows)]
            {
                let vol = Self::effective_mci_volume(volume, muted);
                let _ = mci_cmd(&format!("setaudio {MCI_ALIAS} volume to {vol}"));
            }
        }
    }

    fn position_ms(&self) -> u64 {
        match &self.mode {
            ClockMode::Closed => 0,
            ClockMode::MciAudio => {
                #[cfg(windows)]
                {
                    mci_cmd(&format!("status {MCI_ALIAS} position"))
                        .ok()
                        .and_then(|raw| raw.trim().parse::<u64>().ok())
                        .unwrap_or(0)
                }
                #[cfg(not(windows))]
                0
            }
            ClockMode::SilentClock {
                duration_ms,
                base_ms,
                started_at,
            } => {
                let raw = match started_at {
                    Some(t0) => base_ms.saturating_add(t0.elapsed().as_millis() as u64),
                    None => *base_ms,
                };
                if *duration_ms > 0 {
                    raw.min(*duration_ms)
                } else {
                    raw
                }
            }
        }
    }

    fn length_ms(&self) -> Option<u64> {
        match &self.mode {
            ClockMode::Closed => None,
            ClockMode::MciAudio => {
                #[cfg(windows)]
                {
                    mci_cmd(&format!("status {MCI_ALIAS} length"))
                        .ok()
                        .and_then(|raw| raw.trim().parse::<u64>().ok())
                }
                #[cfg(not(windows))]
                None
            }
            ClockMode::SilentClock { duration_ms, .. } => {
                (*duration_ms > 0).then_some(*duration_ms)
            }
        }
    }

    fn mode_status(&self) -> String {
        match &self.mode {
            ClockMode::Closed => "stopped".into(),
            ClockMode::MciAudio => {
                #[cfg(windows)]
                {
                    mci_cmd(&format!("status {MCI_ALIAS} mode"))
                        .unwrap_or_else(|_| "stopped".into())
                        .trim()
                        .to_ascii_lowercase()
                }
                #[cfg(not(windows))]
                "stopped".into()
            }
            ClockMode::SilentClock {
                duration_ms,
                started_at,
                ..
            } => {
                if started_at.is_none() {
                    return "paused".into();
                }
                if *duration_ms > 0 && self.position_ms() >= *duration_ms {
                    "stopped".into()
                } else {
                    "playing".into()
                }
            }
        }
    }

    fn stop(&mut self) {
        match &mut self.mode {
            ClockMode::Closed => {}
            ClockMode::MciAudio => {
                #[cfg(windows)]
                {
                    let _ = mci_cmd(&format!("stop {MCI_ALIAS}"));
                    let _ = mci_cmd(&format!("seek {MCI_ALIAS} to start"));
                }
            }
            ClockMode::SilentClock {
                base_ms,
                started_at,
                ..
            } => {
                *base_ms = 0;
                *started_at = None;
            }
        }
    }

    fn close(&mut self) {
        if matches!(self.mode, ClockMode::MciAudio) {
            #[cfg(windows)]
            {
                let _ = mci_cmd(&format!("stop {MCI_ALIAS}"));
                let _ = mci_cmd(&format!("close {MCI_ALIAS}"));
            }
        }
        self.mode = ClockMode::Closed;
    }
}

impl Drop for Backend {
    fn drop(&mut self) {
        self.close();
    }
}

fn worker_loop(rx: mpsc::Receiver<PlayerCommand>, shared: Arc<Mutex<PlayerSnapshot>>) {
    let mut backend = Backend::new();
    loop {
        let (is_playing, is_video) = shared
            .lock()
            .map(|s| {
                (
                    s.status == PlaybackStatus::Playing,
                    s.current.as_ref().is_some_and(|t| t.is_video),
                )
            })
            .unwrap_or((false, false));
        let cmd = if is_playing {
            let poll = if is_video { 40 } else { 120 };
            match rx.recv_timeout(Duration::from_millis(poll)) {
                Ok(cmd) => Some(cmd),
                Err(RecvTimeoutError::Timeout) => None,
                Err(RecvTimeoutError::Disconnected) => break,
            }
        } else {
            match rx.recv() {
                Ok(cmd) => Some(cmd),
                Err(_) => break,
            }
        };

        if let Some(cmd) = cmd {
            match cmd {
                PlayerCommand::Shutdown => {
                    backend.close();
                    break;
                }
                PlayerCommand::Play {
                    track,
                    queue,
                    queue_index,
                } => start_track(&mut backend, &shared, track, queue, queue_index),
                PlayerCommand::TogglePause => {
                    let (status, pos, dur, current, vol, muted) = {
                        let s = shared.lock().unwrap();
                        (
                            s.status,
                            s.position_ms,
                            s.duration_ms,
                            s.current.clone(),
                            s.volume,
                            s.muted,
                        )
                    };
                    match status {
                        PlaybackStatus::Playing => {
                            let actual_pos = backend.pause().unwrap_or(pos);
                            if let Ok(mut s) = shared.lock() {
                                s.status = PlaybackStatus::Paused;
                                s.position_ms = actual_pos;
                            }
                        }
                        PlaybackStatus::Paused | PlaybackStatus::Stopped => {
                            if let Some(track) = current {
                                let start_at = if dur > 0 && pos >= dur { 0 } else { pos };
                                if backend.is_open() && backend.play_from(start_at).is_ok() {
                                    if let Ok(mut s) = shared.lock() {
                                        s.status = PlaybackStatus::Playing;
                                        s.position_ms = start_at;
                                        if status == PlaybackStatus::Stopped || start_at == 0 {
                                            s.stream_epoch = s.stream_epoch.wrapping_add(1);
                                        }
                                        s.error = None;
                                    }
                                } else {
                                    reopen_existing(
                                        &mut backend,
                                        &shared,
                                        &track,
                                        start_at,
                                        vol,
                                        muted,
                                    );
                                }
                            }
                        }
                        PlaybackStatus::Loading => {}
                    }
                }
                PlayerCommand::Stop { keep_track } => {
                    if keep_track {
                        backend.stop();
                        if let Ok(mut s) = shared.lock() {
                            s.status = PlaybackStatus::Stopped;
                            s.position_ms = 0;
                            s.stream_epoch = s.stream_epoch.wrapping_add(1);
                        }
                    } else {
                        backend.close();
                        if let Ok(mut s) = shared.lock() {
                            s.current = None;
                            s.queue.clear();
                            s.queue_index = None;
                            s.status = PlaybackStatus::Stopped;
                            s.position_ms = 0;
                            s.duration_ms = 0;
                            s.has_audio = true;
                            s.stream_epoch = s.stream_epoch.wrapping_add(1);
                            s.error = None;
                        }
                    }
                }
                PlayerCommand::SeekMs(target) => {
                    let (dur, playing) = {
                        let s = shared.lock().unwrap();
                        (s.duration_ms, s.status == PlaybackStatus::Playing)
                    };
                    let clamped = if dur > 0 { target.min(dur) } else { target };
                    backend.seek(clamped, playing);
                    if let Ok(mut s) = shared.lock() {
                        s.position_ms = clamped;
                        s.stream_epoch = s.stream_epoch.wrapping_add(1);
                    }
                }
                PlayerCommand::SeekDeltaMs(delta) => {
                    let (pos, dur, playing) = {
                        let s = shared.lock().unwrap();
                        (
                            if s.status == PlaybackStatus::Playing {
                                backend.position_ms()
                            } else {
                                s.position_ms
                            },
                            s.duration_ms,
                            s.status == PlaybackStatus::Playing,
                        )
                    };
                    let target = if delta < 0 {
                        pos.saturating_sub(delta.unsigned_abs())
                    } else {
                        pos.saturating_add(delta as u64)
                    };
                    let clamped = if dur > 0 { target.min(dur) } else { target };
                    backend.seek(clamped, playing);
                    if let Ok(mut s) = shared.lock() {
                        s.position_ms = clamped;
                        s.stream_epoch = s.stream_epoch.wrapping_add(1);
                    }
                }
                PlayerCommand::SetVolume(vol) => {
                    let vol = vol.min(100);
                    let muted = if let Ok(mut s) = shared.lock() {
                        s.volume = vol;
                        if vol > 0 {
                            s.muted = false;
                        }
                        s.muted
                    } else {
                        false
                    };
                    backend.apply_volume(vol, muted);
                }
                PlayerCommand::ToggleMute => {
                    let (vol, muted) = if let Ok(mut s) = shared.lock() {
                        s.muted = !s.muted;
                        (s.volume, s.muted)
                    } else {
                        (85, false)
                    };
                    backend.apply_volume(vol, muted);
                }
                PlayerCommand::ToggleLoop => {
                    if let Ok(mut s) = shared.lock() {
                        s.loop_track = !s.loop_track;
                    }
                }
                PlayerCommand::NextTrack => step_queue(&mut backend, &shared, 1),
                PlayerCommand::PrevTrack => step_queue(&mut backend, &shared, -1),
            }
            continue;
        }

        let mode = backend.mode_status();
        if mode == "stopped" {
            let (loop_track, next_item) = {
                let s = shared.lock().unwrap();
                let next = s
                    .queue_index
                    .and_then(|idx| idx.checked_add(1))
                    .and_then(|next_idx| {
                        s.queue
                            .get(next_idx)
                            .cloned()
                            .map(|t| (t, s.queue.clone(), next_idx))
                    });
                (s.loop_track, next)
            };
            if loop_track {
                if backend.play_from(0).is_ok()
                    && let Ok(mut s) = shared.lock()
                {
                    s.position_ms = 0;
                    s.stream_epoch = s.stream_epoch.wrapping_add(1);
                }
            } else if let Some((track, queue, next_idx)) = next_item {
                start_track(&mut backend, &shared, track, queue, Some(next_idx));
            } else {
                backend.stop();
                if let Ok(mut s) = shared.lock() {
                    s.status = PlaybackStatus::Stopped;
                    s.position_ms = 0;
                    s.stream_epoch = s.stream_epoch.wrapping_add(1);
                }
            }
        } else {
            let pos = backend.position_ms();
            let len = backend.length_ms();
            if let Ok(mut s) = shared.lock() {
                s.position_ms = pos;
                if let Some(d) = len
                    && d > 0
                {
                    s.duration_ms = d;
                }
                if mode == "paused" {
                    s.status = PlaybackStatus::Paused;
                }
            }
        }
    }
}

fn step_queue(backend: &mut Backend, shared: &Arc<Mutex<PlayerSnapshot>>, delta: isize) {
    let target = {
        let s = shared.lock().unwrap();
        if s.queue.is_empty() {
            None
        } else {
            let len = s.queue.len() as isize;
            let cur = s.queue_index.unwrap_or(0) as isize;
            let next_idx = (cur + delta).rem_euclid(len) as usize;
            Some((s.queue[next_idx].clone(), s.queue.clone(), next_idx))
        }
    };
    if let Some((track, queue, idx)) = target {
        start_track(backend, shared, track, queue, Some(idx));
    }
}

fn start_track(
    backend: &mut Backend,
    shared: &Arc<Mutex<PlayerSnapshot>>,
    track: AudioTrack,
    queue: Vec<AudioTrack>,
    queue_index: Option<usize>,
) {
    let (vol, muted) = {
        let mut s = shared.lock().unwrap();
        s.current = Some(track.clone());
        s.queue = queue;
        s.queue_index = queue_index;
        s.status = PlaybackStatus::Loading;
        s.position_ms = 0;
        s.duration_ms = 0;
        s.has_audio = !track.is_video;
        s.error = None;
        (s.volume, s.muted)
    };

    if !track.path.is_file() {
        backend.close();
        if let Ok(mut s) = shared.lock() {
            s.status = PlaybackStatus::Stopped;
            s.error = Some("El archivo multimedia ya no existe en disco.".into());
        }
        return;
    }

    match backend.open_track(&track, vol, muted) {
        Ok((duration_ms, has_audio)) => {
            if let Ok(mut s) = shared.lock() {
                s.status = PlaybackStatus::Playing;
                s.duration_ms = duration_ms;
                s.position_ms = 0;
                s.has_audio = has_audio;
                s.stream_epoch = s.stream_epoch.wrapping_add(1);
                s.error = None;
            }
        }
        Err(err) => {
            backend.close();
            if let Ok(mut s) = shared.lock() {
                s.status = PlaybackStatus::Stopped;
                s.error = Some(err);
            }
        }
    }
}

fn reopen_existing(
    backend: &mut Backend,
    shared: &Arc<Mutex<PlayerSnapshot>>,
    track: &AudioTrack,
    start_at: u64,
    vol: u8,
    muted: bool,
) {
    match backend.open_track(track, vol, muted) {
        Ok((duration_ms, has_audio)) => {
            if start_at > 0 {
                backend.seek(start_at, true);
            }
            if let Ok(mut s) = shared.lock() {
                s.status = PlaybackStatus::Playing;
                s.duration_ms = duration_ms;
                s.position_ms = start_at;
                s.has_audio = has_audio;
                s.stream_epoch = s.stream_epoch.wrapping_add(1);
                s.error = None;
            }
        }
        Err(err) => {
            if let Ok(mut s) = shared.lock() {
                s.status = PlaybackStatus::Stopped;
                s.error = Some(err);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn recognizes_music_and_audio_extensions_case_insensitively() {
        assert!(is_audio_path(Path::new("tema.MP3")));
        assert!(is_audio_path(Path::new("locucion.wav")));
        assert!(is_audio_path(Path::new("banda_sonora.M4A")));
        assert!(is_audio_path(Path::new("master.flac")));
        assert!(is_audio_path(Path::new("fx.ogg")));
        assert!(!is_audio_path(Path::new("clip.mp4")));
        assert!(!is_audio_path(Path::new("guion.srt")));
    }

    #[test]
    fn formats_timestamps_consistently() {
        assert_eq!(format_ms(0), "00:00");
        assert_eq!(format_ms(65_000), "01:05");
        assert_eq!(format_ms(3_661_000), "01:01:01");
    }

    #[test]
    fn volume_scale_maps_zero_and_mute_cleanly() {
        assert_eq!(Backend::effective_mci_volume(85, false), 850);
        assert_eq!(Backend::effective_mci_volume(85, true), 0);
        assert_eq!(Backend::effective_mci_volume(150, false), 1000);
    }
}
