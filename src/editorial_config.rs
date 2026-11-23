//! Preferencias y claves del motor editorial durante la transición a Rust.
use crate::{
    bridge, library,
    services::{EditorialPreferences, Settings},
};
use serde_json::{Map, Value, json};
use sha2::{Digest, Sha256};
use std::{
    collections::BTreeMap,
    fs,
    io::Write,
    path::{Path, PathBuf},
    sync::Mutex,
};

const GEMINI_DEFAULT: &str = "gemini-3.5-flash";
const MINIMAX_MODELS: &[&str] = &[
    "MiniMax-M3.1-Flash",
    "MiniMax-M3",
    "MiniMax-M2.7",
    "MiniMax-M2.5",
    "MiniMax-M2.1",
    "MiniMax-M2",
    "MiniMax-Text-01",
];
static WRITE_LOCK: Mutex<()> = Mutex::new(());

/// El puente restante lee estos mismos archivos de desarrollo. La rama Flet usa otro checkout.
pub(crate) fn data_dir() -> PathBuf {
    let home = std::env::var_os(if cfg!(windows) { "USERPROFILE" } else { "HOME" })
        .or_else(|| std::env::var_os(if cfg!(windows) { "HOME" } else { "USERPROFILE" }))
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("."));
    let base = home.join(".davinci_flow");
    let root = bridge::root();
    if !root.join("Cargo.toml").is_file() {
        return base;
    }
    let path = resolved_path(&root);
    let hash = format!(
        "{:x}",
        Sha256::digest(path.to_string_lossy().to_lowercase().as_bytes())
    );
    base.join("development").join(&hash[..16])
}

pub(crate) fn resolved_path(path: &Path) -> PathBuf {
    let resolved = path.canonicalize().unwrap_or_else(|_| path.to_owned());
    let display = resolved.to_string_lossy();
    if let Some(network) = display.strip_prefix(r"\\?\UNC\") {
        PathBuf::from(format!("\\\\{network}"))
    } else if let Some(path) = display.strip_prefix(r"\\?\") {
        PathBuf::from(path)
    } else {
        resolved
    }
}

const PREFS: &str = "editorial_preferences.json";
const KEYS: &str = "config.json";

pub(crate) fn load_preferences() -> Result<Map<String, Value>, String> {
    load(&data_dir().join(PREFS))
}

pub(crate) fn update_preferences(
    edit: impl FnOnce(&mut Map<String, Value>) -> Result<(), String>,
) -> Result<(), String> {
    update(&data_dir().join(PREFS), edit)
}

fn load(path: &Path) -> Result<Map<String, Value>, String> {
    match fs::read(path) {
        Ok(bytes) => serde_json::from_slice(&bytes).map_err(|_| {
            format!(
                "El archivo {} no contiene una configuración válida.",
                path.display()
            )
        }),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(Map::new()),
        Err(error) => Err(format!("No se pudo leer {}: {error}", path.display())),
    }
}

fn update(
    path: &Path,
    edit: impl FnOnce(&mut Map<String, Value>) -> Result<(), String>,
) -> Result<(), String> {
    let _guard = WRITE_LOCK
        .lock()
        .map_err(|_| "La configuración está ocupada.")?;
    let mut current = load(path)?;
    edit(&mut current)?;
    let parent = path
        .parent()
        .ok_or("La configuración carece de carpeta de datos.")?;
    fs::create_dir_all(parent)
        .map_err(|error| format!("No se pudo crear la carpeta de datos: {error}"))?;
    let mut pending = tempfile::NamedTempFile::new_in(parent)
        .map_err(|error| format!("No se pudo preparar la configuración: {error}"))?;
    serde_json::to_writer_pretty(&mut pending, &current)
        .map_err(|_| "No se pudo serializar la configuración.")?;
    pending
        .flush()
        .and_then(|()| pending.as_file().sync_all())
        .map_err(|error| format!("No se pudo guardar la configuración: {error}"))?;
    pending
        .persist(path)
        .map_err(|error| format!("No se pudo sustituir la configuración: {}", error.error))?;
    Ok(())
}

fn provider_profile(provider: &str) -> Result<(&'static str, &'static str, &'static str), String> {
    match provider {
        "gemini" => Ok(("GEMINI_API_KEY", "gemini_api_key", GEMINI_DEFAULT)),
        "minimax" => Ok(("MINIMAX_API_KEY", "minimax_api_key", MINIMAX_MODELS[0])),
        _ => Err("Proveedor de IA desconocido.".into()),
    }
}

fn string<'a>(map: &'a Map<String, Value>, key: &str, default: &'a str) -> &'a str {
    map.get(key).and_then(Value::as_str).unwrap_or(default)
}

pub(crate) fn api_key(provider: &str) -> Result<Option<String>, String> {
    let (variable, field, _) = provider_profile(provider)?;
    if let Ok(value) = std::env::var(variable)
        && !value.trim().is_empty()
    {
        return Ok(Some(value.trim().into()));
    }
    Ok(load(&data_dir().join(KEYS))?
        .get(field)
        .and_then(Value::as_str)
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(str::to_owned))
}

pub(crate) fn save_key(provider: &str, key: &str) -> Result<(), String> {
    let (_, field, _) = provider_profile(provider)?;
    let key = key.trim();
    if key.is_empty() {
        return Err("La clave API no puede quedar vacía.".into());
    }
    update(&data_dir().join(KEYS), |data| {
        data.insert(field.into(), json!(key));
        Ok(())
    })
}

fn read_preferences(data: &Map<String, Value>) -> EditorialPreferences {
    EditorialPreferences {
        mode: string(data, "mode", "highlights").into(),
        format: string(data, "format", "auto").into(),
        density: string(data, "density", "balanced").into(),
        direction: string(data, "direction", "").into(),
        track_mode: string(data, "track_mode", "triple").into(),
        batch_size: string(data, "batch_size", "20").into(),
    }
}

fn validate(p: &EditorialPreferences) -> Result<(), String> {
    if !matches!(p.mode.as_str(), "highlights" | "captions")
        || !matches!(p.format.as_str(), "auto" | "horizontal" | "vertical")
        || !matches!(p.density.as_str(), "sparse" | "balanced" | "dense")
        || !matches!(p.track_mode.as_str(), "single" | "dual" | "triple")
        || !matches!(p.batch_size.as_str(), "20" | "50" | "100" | "500" | "all")
        || p.direction.chars().count() > 4000
    {
        return Err("Las preferencias editoriales contienen valores inválidos.".into());
    }
    Ok(())
}

pub(crate) fn settings(override_provider: Option<&str>) -> Result<Settings, String> {
    let data = load(&data_dir().join(PREFS))?;
    let saved_provider = string(&data, "provider", "gemini");
    let provider = override_provider.unwrap_or(saved_provider);
    let (_, _, default_model) = provider_profile(provider)?;
    let model = if provider == saved_provider {
        string(&data, "model", default_model).trim()
    } else {
        default_model
    };
    let model = if model.is_empty() || (provider == "minimax" && !MINIMAX_MODELS.contains(&model)) {
        default_model
    } else {
        model
    };
    let preferences = read_preferences(&data);
    validate(&preferences)?;
    Ok(Settings {
        provider: provider.into(),
        model: model.into(),
        has_key: api_key(provider)?.is_some(),
        providers: vec!["gemini".into(), "minimax".into()],
        models: if provider == "minimax" {
            MINIMAX_MODELS.iter().map(|s| (*s).to_owned()).collect()
        } else {
            vec![]
        },
        preferences,
    })
}

pub(crate) fn save_settings(
    provider: &str,
    model: &str,
    p: &EditorialPreferences,
) -> Result<(), String> {
    provider_profile(provider)?;
    validate(p)?;
    let model = model.trim();
    if model.is_empty() || (provider == "minimax" && !MINIMAX_MODELS.contains(&model)) {
        return Err("Selecciona un modelo válido para el proveedor.".into());
    }
    update(&data_dir().join(PREFS), |data| {
        for (key, value) in [
            ("provider", provider),
            ("model", model),
            ("mode", &p.mode),
            ("format", &p.format),
            ("density", &p.density),
            ("direction", &p.direction),
            ("track_mode", &p.track_mode),
            ("batch_size", &p.batch_size),
        ] {
            data.insert(key.into(), json!(value));
        }
        Ok(())
    })
}

pub(crate) fn sync_library(
    folders: &BTreeMap<String, Vec<String>>,
    selected: &[String],
) -> Result<(), String> {
    let paths: BTreeMap<_, _> = folders
        .iter()
        .filter(|(category, _)| library::CATEGORIES.iter().any(|(key, _)| key == category))
        .filter_map(|(category, list)| {
            let joined = list
                .iter()
                .map(|path| path.trim())
                .filter(|path| !path.is_empty())
                .collect::<Vec<_>>()
                .join("; ");
            (!joined.is_empty()).then_some((category, joined))
        })
        .collect();
    let ids: Vec<_> = selected
        .iter()
        .filter(|item| !item.trim().is_empty())
        .take(80)
        .collect();
    update(&data_dir().join(PREFS), |data| {
        data.insert("paths".into(), json!(paths));
        data.insert("resource_ids".into(), json!(ids));
        Ok(())
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn config_write_preserves_preset_and_refuses_to_replace_corrupt_file() {
        let folder = tempfile::tempdir().unwrap();
        let path = folder.path().join(PREFS);
        fs::write(
            &path,
            r#"{"title_presets":{"Compacto":[{"id":"title_1"}]}}"#,
        )
        .unwrap();
        update(&path, |data| {
            data.insert("model".into(), json!("changed"));
            Ok(())
        })
        .unwrap();
        assert_eq!(
            load(&path).unwrap()["title_presets"]["Compacto"][0]["id"],
            "title_1"
        );
        fs::write(&path, b"{").unwrap();
        assert!(update(&path, |_| Ok(())).is_err());
        assert_eq!(fs::read(&path).unwrap(), b"{");
    }
}
