//! Voces locales por SAPI. El texto se entrega como texto plano al motor de Windows.
use crate::media::Voice;
use std::path::{Path, PathBuf};

#[cfg(windows)]
mod sapi {
    use super::*;
    use sha2::{Digest, Sha256};
    use std::{ffi::c_void, os::windows::ffi::OsStrExt};
    use windows::{
        Win32::{
            Media::{
                Audio::WAVEFORMATEX,
                Speech::{
                    ISpObjectToken, ISpObjectTokenCategory, ISpStream, ISpVoice, SPCAT_VOICES,
                    SPF_IS_NOT_XML, SPFM_CREATE_ALWAYS, SpFileStream, SpObjectTokenCategory,
                    SpVoice,
                },
            },
            System::Com::{
                CLSCTX_INPROC_SERVER, COINIT_APARTMENTTHREADED, CoCreateInstance, CoInitializeEx,
                CoTaskMemFree, CoUninitialize,
            },
        },
        core::{GUID, PCWSTR, PWSTR},
    };

    struct Apartment;

    impl Apartment {
        fn new() -> windows::core::Result<Self> {
            // Las interfaces SAPI se crean, usan y liberan en el mismo hilo COM.
            unsafe {
                CoInitializeEx(None, COINIT_APARTMENTTHREADED).ok()?;
            }
            Ok(Self)
        }
    }

    impl Drop for Apartment {
        fn drop(&mut self) {
            // Solo existe Apartment si CoInitializeEx confirmó la inicialización.
            unsafe {
                CoUninitialize();
            }
        }
    }

    fn read_string(value: PWSTR) -> windows::core::Result<String> {
        use windows::Win32::Foundation::E_FAIL;
        if value.is_null() {
            return Err(windows::core::Error::from_hresult(E_FAIL));
        }
        // SAPI entrega una cadena terminada en NUL cuya memoria pertenece al llamante.
        unsafe {
            let text = value.to_string();
            CoTaskMemFree(Some(value.0.cast::<c_void>()));
            text.map_err(|_| windows::core::Error::from_hresult(E_FAIL))
        }
    }

    fn tokens() -> windows::core::Result<Vec<(Voice, ISpObjectToken)>> {
        // Se ejecuta en un hilo inicializado por Apartment y los tokens permanecen allí.
        unsafe {
            let category: ISpObjectTokenCategory =
                CoCreateInstance(&SpObjectTokenCategory, None, CLSCTX_INPROC_SERVER)?;
            category.SetId(SPCAT_VOICES, false)?;
            let tokens = category.EnumTokens(PCWSTR::null(), PCWSTR::null())?;
            let mut voices = Vec::new();
            let mut count = 0;
            tokens.GetCount(&mut count)?;
            for _ in 0..count {
                let mut token = None;
                tokens.Next(1, &mut token, None)?;
                let Some(token) = token else {
                    break;
                };
                let Ok(name) = token.GetStringValue(PCWSTR::null()).and_then(read_string) else {
                    continue;
                };
                if name.trim().is_empty() {
                    continue;
                }
                let identity = read_string(token.GetId()?)?;
                let hash = format!(
                    "{:x}",
                    Sha256::digest(format!("{identity}{name}").as_bytes())
                );
                voices.push((
                    Voice {
                        id: format!("system-{}", &hash[..20]),
                        name,
                        provider: "system".into(),
                        ready: true,
                    },
                    token,
                ));
            }
            Ok(voices)
        }
    }

    pub(super) fn voices() -> Result<Vec<Voice>, String> {
        let _apartment = Apartment::new().map_err(|error| error.to_string())?;
        tokens()
            .map(|voices| voices.into_iter().map(|(voice, _)| voice).collect())
            .map_err(|error| format!("No se pudo leer el catálogo de voces de Windows: {error}"))
    }

    pub(super) fn synthesize(text: &str, id: &str, file: &Path) -> Result<(), String> {
        let _apartment = Apartment::new().map_err(|error| error.to_string())?;
        let (_, token) = tokens()
            .map_err(|error| error.to_string())?
            .into_iter()
            .find(|(voice, _)| voice.id == id)
            .ok_or("La voz seleccionada ya no está instalada.")?;
        let filename: Vec<_> = file.as_os_str().encode_wide().chain([0]).collect();
        let speech: Vec<_> = text.encode_utf16().chain([0]).collect();
        synthesize_pcm(token, &filename, &speech)
            .map_err(|error| format!("Windows no pudo completar la síntesis de voz local: {error}"))
    }

    fn synthesize_pcm(
        token: ISpObjectToken,
        filename: &[u16],
        speech: &[u16],
    ) -> windows::core::Result<()> {
        const WAVE_FORMAT: GUID = GUID::from_u128(0xc31adbae_527f_4ff5_a230_f62bb61ff70c);
        let format = WAVEFORMATEX {
            wFormatTag: 1,
            nChannels: 1,
            nSamplesPerSec: 22_050,
            nAvgBytesPerSec: 44_100,
            nBlockAlign: 2,
            wBitsPerSample: 16,
            cbSize: 0,
        };
        // Los búferes UTF-16 terminados en NUL y el formato viven durante las llamadas.
        // La salida se cierra explícitamente para que SAPI termine de escribir la cabecera WAV.
        unsafe {
            let stream: ISpStream = CoCreateInstance(&SpFileStream, None, CLSCTX_INPROC_SERVER)?;
            let speaker: ISpVoice = CoCreateInstance(&SpVoice, None, CLSCTX_INPROC_SERVER)?;
            stream.BindToFile(
                PCWSTR(filename.as_ptr()),
                SPFM_CREATE_ALWAYS,
                Some(&WAVE_FORMAT),
                Some(&format),
                0,
            )?;
            speaker.SetVoice(&token)?;
            speaker.SetOutput(&stream, true)?;
            speaker.Speak(PCWSTR(speech.as_ptr()), SPF_IS_NOT_XML.0 as u32, None)?;
            drop(speaker);
            stream.Close()
        }
    }
}

pub(crate) fn voices() -> Result<Vec<Voice>, String> {
    #[cfg(windows)]
    return sapi::voices();
    #[cfg(not(windows))]
    Ok(Vec::new())
}

pub(crate) fn available(id: &str) -> Result<(), String> {
    if !voices()?.iter().any(|voice| voice.id == id) {
        return Err("La voz seleccionada ya no está instalada.".into());
    }
    Ok(())
}

pub(crate) fn generate(text: &str, id: &str, directory: &Path) -> Result<PathBuf, String> {
    let text = text.trim();
    if text.is_empty() || text.chars().count() > 10_000 || text.contains('\0') {
        return Err("Escribe entre 1 y 10.000 caracteres para generar voz.".into());
    }
    #[cfg(windows)]
    {
        use std::{
            fs,
            io::{Read, Seek, SeekFrom},
        };
        fs::create_dir_all(directory).map_err(|error| error.to_string())?;
        let stage = tempfile::Builder::new()
            .prefix("voice-")
            .tempdir_in(directory)
            .map_err(|error| error.to_string())?;
        let temporary = stage.path().join("speech.wav");
        sapi::synthesize(text, id, &temporary)?;
        // Verificar el bloque PCM escrito antes de exponer la ruta a la interfaz.
        let mut wav = fs::File::open(&temporary).map_err(|error| error.to_string())?;
        let mut tag = [0u8; 12];
        wav.read_exact(&mut tag)
            .map_err(|_| "La voz local no produjo un WAV válido.")?;
        if &tag[..4] != b"RIFF" || &tag[8..] != b"WAVE" {
            return Err("La voz local no produjo un WAV válido.".into());
        }
        let end = wav.metadata().map_err(|error| error.to_string())?.len();
        loop {
            let mut chunk = [0u8; 8];
            wav.read_exact(&mut chunk)
                .map_err(|_| "La voz local no produjo un WAV válido.")?;
            let bytes = u32::from_le_bytes(chunk[4..].try_into().expect("el tamaño ocupa 4 bytes"));
            let offset = wav.stream_position().map_err(|error| error.to_string())?;
            if offset + u64::from(bytes) > end {
                return Err("La voz local produjo un WAV incompleto.".into());
            }
            if &chunk[..4] == b"data" {
                if bytes < 2 {
                    return Err("La voz local no produjo audio.".into());
                }
                break;
            }
            wav.seek(SeekFrom::Current(i64::from(bytes) + i64::from(bytes % 2)))
                .map_err(|error| error.to_string())?;
        }
        drop(wav);
        let mut filename = stage
            .path()
            .file_name()
            .expect("el temporal tiene nombre")
            .to_os_string();
        filename.push(".wav");
        let output = directory.join(filename);
        fs::rename(&temporary, &output).map_err(|error| error.to_string())?;
        Ok(output)
    }
    #[cfg(not(windows))]
    {
        let _ = (id, directory);
        Err("Las voces del sistema requieren Windows.".into())
    }
}

#[cfg(all(test, windows))]
mod tests {
    use super::*;

    #[test]
    #[ignore = "requiere una voz SAPI instalada"]
    fn installed_voice_synthesizes_real_pcm() {
        let voices = voices().unwrap();
        let voice = voices.first().expect("hay una voz instalada");
        let directory = tempfile::tempdir().unwrap();
        let file = generate(
            "DaVinci Flow. Prueba de voz local.",
            &voice.id,
            directory.path(),
        )
        .unwrap();
        assert!(file.metadata().unwrap().len() > 5000);
        eprintln!(
            "{} voces instaladas, WAV de {} bytes",
            voices.len(),
            file.metadata().unwrap().len()
        );
    }
}
