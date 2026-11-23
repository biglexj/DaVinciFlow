//! Síntesis en PCM de los efectos originales de DaVinci Flow, bajo licencia MIT.
use crate::services::SfxAsset;
use std::{
    f64::consts::{PI, TAU},
    fs::{self, File},
    io::{Read, Write},
    path::{Path, PathBuf},
};

const SAMPLE_RATE: u32 = 44_100;

#[derive(Clone, Copy)]
enum Sound {
    Whoosh,
    Pop,
    Bell,
    Click,
    Riser,
    Glitch,
    Thud,
    Chime,
}

struct Asset {
    id: &'static str,
    name: &'static str,
    category: &'static str,
    path: &'static str,
    seconds: f64,
    gain: f64,
    sound: Sound,
}

const ASSETS: &[Asset] = &[
    Asset {
        id: "sfx_whoosh_clean_01",
        name: "Whoosh Limpio",
        category: "whoosh",
        path: "whooshes/whoosh_clean_01.wav",
        seconds: 0.45,
        gain: -14.0,
        sound: Sound::Whoosh,
    },
    Asset {
        id: "sfx_pop_subtle_01",
        name: "Pop Sutil",
        category: "pop",
        path: "pops/pop_subtle_01.wav",
        seconds: 0.18,
        gain: -16.0,
        sound: Sound::Pop,
    },
    Asset {
        id: "sfx_bell_chime_01",
        name: "Campana Reflexiva",
        category: "bell",
        path: "bells/bell_chime_01.wav",
        seconds: 1.20,
        gain: -18.0,
        sound: Sound::Bell,
    },
    Asset {
        id: "sfx_click_tech_01",
        name: "Clic Tecnológico",
        category: "click",
        path: "clicks/click_tech_01.wav",
        seconds: 0.08,
        gain: -15.0,
        sound: Sound::Click,
    },
    Asset {
        id: "sfx_riser_tension_01",
        name: "Riser de Tensión",
        category: "riser",
        path: "risers/riser_tension_01.wav",
        seconds: 0.65,
        gain: -16.0,
        sound: Sound::Riser,
    },
    Asset {
        id: "sfx_glitch_digital_01",
        name: "Glitch Digital",
        category: "glitch",
        path: "glitches/glitch_digital_01.wav",
        seconds: 0.14,
        gain: -15.0,
        sound: Sound::Glitch,
    },
    Asset {
        id: "sfx_thud_subtle_01",
        name: "Impacto Subgrave",
        category: "impact",
        path: "impacts/thud_subtle_01.wav",
        seconds: 0.50,
        gain: -14.0,
        sound: Sound::Thud,
    },
    Asset {
        id: "sfx_chime_success_01",
        name: "Chime Armónico de Éxito",
        category: "bell",
        path: "bells/chime_success_01.wav",
        seconds: 0.85,
        gain: -16.0,
        sound: Sound::Chime,
    },
];

pub(crate) fn catalog() -> Vec<SfxAsset> {
    ASSETS
        .iter()
        .map(|asset| SfxAsset {
            id: asset.id.into(),
            name: asset.name.into(),
            category: asset.category.into(),
            duration_seconds: asset.seconds,
            recommended_gain_db: asset.gain,
        })
        .collect()
}

pub(crate) fn file(id: &str) -> Result<PathBuf, String> {
    let asset = ASSETS
        .iter()
        .find(|asset| asset.id == id)
        .ok_or("Efecto de sonido no disponible.")?;
    let base = std::env::var_os("APPDATA")
        .map(PathBuf::from)
        .or_else(|| std::env::home_dir().map(|home| home.join(".davinci-flow")))
        .ok_or("No se encontró la carpeta de datos de audio.")?;
    materialize(asset, &base.join("DaVinciFlow/assets/sfx"))
        .map_err(|error| format!("No se pudo preparar el efecto de sonido: {error}"))
}

fn materialize(asset: &Asset, root: &Path) -> std::io::Result<PathBuf> {
    let path = root.join(asset.path);
    let frames = (asset.seconds * f64::from(SAMPLE_RATE)).round() as u32;
    let data_len = frames * 2;
    let mut header = Vec::with_capacity(44);
    header.extend_from_slice(b"RIFF");
    header.extend_from_slice(&(36 + data_len).to_le_bytes());
    header.extend_from_slice(b"WAVEfmt ");
    header.extend_from_slice(&16u32.to_le_bytes()); // PCM
    header.extend_from_slice(&[1, 0, 1, 0]); // PCM mono
    header.extend_from_slice(&SAMPLE_RATE.to_le_bytes());
    header.extend_from_slice(&(SAMPLE_RATE * 2).to_le_bytes());
    header.extend_from_slice(&[2, 0, 16, 0]); // bloque de dos bytes y 16 bits por muestra
    header.extend_from_slice(b"data");
    header.extend_from_slice(&data_len.to_le_bytes());

    if let Ok(mut file) = File::open(&path)
        && file.metadata()?.len() == u64::from(data_len) + 44
    {
        let mut existing = [0; 44];
        if file.read_exact(&mut existing).is_ok() && existing == header.as_slice() {
            return Ok(path);
        }
    }

    let directory = path.parent().expect("el efecto tiene carpeta");
    fs::create_dir_all(directory)?;
    let mut pending = tempfile::NamedTempFile::new_in(directory)?;
    let mut bytes = header;
    let mut noise = match asset.sound {
        Sound::Whoosh => 21,
        Sound::Click => 7,
        _ => 42,
    };
    let mut filtered = 0.0;
    for frame in 0..frames {
        let time = f64::from(frame) / f64::from(SAMPLE_RATE);
        let phase = time / asset.seconds;
        let value = sample(asset.sound, time, phase, &mut noise, &mut filtered);
        let pcm = (value.clamp(-1.0, 1.0) * f64::from(i16::MAX)).round() as i16;
        bytes.extend_from_slice(&pcm.to_le_bytes());
    }
    pending.write_all(&bytes)?;
    pending.persist(&path)?;
    Ok(path)
}

fn white_noise(state: &mut u32) -> f64 {
    // Xorshift32 con una semilla fija por efecto para que la síntesis sea reproducible.
    *state ^= *state << 13;
    *state ^= *state >> 17;
    *state ^= *state << 5;
    f64::from(*state) * (2.0 / f64::from(u32::MAX)) - 1.0
}

fn sample(sound: Sound, time: f64, phase: f64, noise: &mut u32, filtered: &mut f64) -> f64 {
    let tone = |frequency: f64| (TAU * frequency * time).sin();
    match sound {
        Sound::Whoosh => {
            let envelope = (PI * phase).sin().powf(1.7);
            *filtered += (white_noise(noise) - *filtered) * (0.04 + 0.16 * phase);
            (*filtered * 0.48 + tone(280.0 + 520.0 * phase) * 0.08) * envelope
        }
        Sound::Pop => tone(330.0 - 170.0 * phase) * (-15.0 * phase).exp() * 0.62,
        Sound::Bell => {
            (tone(880.0) * 0.38 + tone(1320.0) * 0.19 + tone(2112.0) * 0.08) * (-4.8 * phase).exp()
        }
        Sound::Click => (white_noise(noise) * 0.35 + tone(1800.0) * 0.20) * (-28.0 * phase).exp(),
        Sound::Riser => {
            let frequency = 140.0 + 620.0 * phase.powf(2.2);
            let noise = white_noise(noise) * 0.12 * phase.powf(1.8);
            (tone(frequency) + noise) * phase.powf(1.6) * 0.52
        }
        Sound::Glitch => {
            let step = (time * 50.0) as u32;
            tone(1100.0 + f64::from((step * 389) % 1700)) * (-14.0 * phase).exp() * 0.48
        }
        Sound::Thud => tone(75.0 * (-6.0 * phase).exp() + 36.0) * (-8.5 * phase).exp() * 0.72,
        Sound::Chime => {
            (tone(1046.5) * 0.30 + tone(1318.5) * 0.22 + tone(1567.98) * 0.18 + tone(2093.0) * 0.10)
                * (-3.6 * phase).exp()
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn generates_eight_pcm_files_and_repairs_a_partial_output() {
        let directory = tempfile::tempdir().unwrap();
        assert_eq!(catalog().len(), 8);
        for asset in ASSETS {
            let path = materialize(asset, directory.path()).unwrap();
            let bytes = fs::read(&path).unwrap();
            assert_eq!(&bytes[0..4], b"RIFF");
            assert!(bytes[44..].iter().any(|&byte| byte != 0));
            fs::write(&path, &bytes[..44]).unwrap();
            materialize(asset, directory.path()).unwrap();
            assert_eq!(fs::read(&path).unwrap(), bytes);
        }
    }
}
