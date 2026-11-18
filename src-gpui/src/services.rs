//! Servicios del proyecto vistos desde la ventana nativa: ajustes, IA, actualizaciones
//! y catálogos. El trabajo pesado ocurre en Python; aquí solo se tipan las respuestas.
use crate::bridge;
use serde::{Deserialize, Serialize};
use serde_json::Value;

/// Preferencias editoriales del usuario, compartidas con la aplicación de Flet.
#[derive(Clone, Debug, Default, Deserialize)]
pub struct EditorialPreferences {
    pub mode: String,
    pub format: String,
    pub density: String,
    pub direction: String,
    pub track_mode: String,
    pub batch_size: String,
}

/// Estado del proveedor de IA y de sus credenciales.
#[derive(Clone, Debug, Default, Deserialize)]
pub struct Settings {
    pub provider: String,
    pub model: String,
    pub has_key: bool,
    pub providers: Vec<String>,
    pub models: Vec<String>,
    pub preferences: EditorialPreferences,
}

/// Release publicada en el canal oficial, si la hay.
#[derive(Clone, Debug, Default, Deserialize)]
pub struct Release {
    pub version: String,
    pub is_newer: bool,
    pub published_at: String,
    pub notes: String,
    pub download_url: String,
    pub page_url: String,
}

/// Efecto de sonido del catálogo oficial.
#[derive(Clone, Debug, Default, Deserialize)]
pub struct SfxAsset {
    pub id: String,
    pub name: String,
    pub category: String,
    pub duration_seconds: f64,
    pub recommended_gain_db: f64,
}

/// Marcador de línea de tiempo generado por la IA.
#[derive(Clone, Debug, Default, Deserialize)]
pub struct Marker {
    pub frame: f64,
    pub color: String,
    pub name: String,
    pub note: String,
}

/// Resultado de la alineación semántica de los subtítulos.
#[derive(Clone, Debug, Default, Deserialize)]
pub struct Alignment {
    #[serde(default)]
    pub cues: Vec<String>,
    #[serde(default)]
    pub markers: Vec<Marker>,
    #[serde(default)]
    pub corrections: usize,
    #[serde(default)]
    pub summary: String,
}

/// Plantilla de títulos disponible en la instalación.
#[derive(Clone, Debug, Default, Deserialize, Serialize)]
pub struct TemplateInfo {
    pub id: String,
    pub name: String,
    #[serde(default = "default_category")]
    pub category: String,
    pub source: String,
    pub locator: String,
    #[serde(default)]
    pub fingerprint: String,
    #[serde(default)]
    pub text_tool: String,
    #[serde(default = "default_text_input")]
    pub text_input: String,
}

fn default_text_input() -> String {
    "StyledText".into()
}
fn default_category() -> String {
    "general".into()
}

#[derive(Deserialize)]
struct ReleaseEnvelope {
    release: Option<Release>,
}

#[derive(Deserialize)]
struct ModelsEnvelope {
    models: Vec<String>,
}

#[derive(Deserialize)]
struct AssistantEnvelope {
    text: String,
}

#[derive(Deserialize)]
struct SfxEnvelope {
    assets: Vec<SfxAsset>,
}

#[derive(Deserialize)]
struct TemplatesEnvelope {
    templates: Vec<TemplateInfo>,
    diagnostics: Vec<String>,
}

fn text(value: &Value, key: &str) -> String {
    value
        .get(key)
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_string()
}

fn preferences(value: &Value) -> EditorialPreferences {
    let source = value.get("preferences").cloned().unwrap_or(Value::Null);
    EditorialPreferences {
        mode: text(&source, "mode"),
        format: text(&source, "format"),
        density: text(&source, "density"),
        direction: text(&source, "direction"),
        track_mode: text(&source, "track_mode"),
        batch_size: text(&source, "batch_size"),
    }
}

/// Estado actual del proveedor de IA, sus modelos y las preferencias editoriales.
pub fn settings() -> Result<Settings, String> {
    let value = bridge::invoke("services.py", "settings", &[])?;
    let providers = value
        .get("providers")
        .and_then(Value::as_array)
        .map(|items| {
            items
                .iter()
                .filter_map(|item| item.as_str().map(str::to_owned))
                .collect()
        })
        .unwrap_or_default();
    let models = value
        .get("models")
        .and_then(Value::as_array)
        .map(|items| {
            items
                .iter()
                .filter_map(|item| item.as_str().map(str::to_owned))
                .collect()
        })
        .unwrap_or_default();
    Ok(Settings {
        provider: text(&value, "provider"),
        model: text(&value, "model"),
        has_key: value
            .get("has_key")
            .and_then(Value::as_bool)
            .unwrap_or(false),
        providers,
        models,
        preferences: preferences(&value),
    })
}
pub fn settings_for(provider: &str) -> Result<Settings, String> {
    let value = bridge::invoke("services.py", "settings", &[("provider", provider)])?;
    serde_json::from_value(value)
        .map_err(|_| "No se pudieron leer los ajustes de este proveedor.".into())
}

/// Catálogo de modelos de Gemini disponible con la credencial configurada.
pub fn scan_models() -> Result<Vec<String>, String> {
    let value = bridge::invoke("services.py", "scan_models", &[])?;
    Ok(serde_json::from_value::<ModelsEnvelope>(value)
        .map_err(|_| "El catálogo de modelos no se pudo leer.".to_string())?
        .models)
}

/// Consulta al asistente con el proveedor de IA configurado.
pub fn assistant(prompt: &str) -> Result<String, String> {
    let value = bridge::invoke("services.py", "assistant", &[("prompt", prompt)])?;
    Ok(serde_json::from_value::<AssistantEnvelope>(value)
        .map_err(|_| "La respuesta del asistente no se pudo leer.".to_string())?
        .text)
}

/// Última release publicada; `None` si no hay red o no hay versión nueva.
pub fn release() -> Result<Option<Release>, String> {
    let value = bridge::invoke("services.py", "release", &[])?;
    Ok(serde_json::from_value::<ReleaseEnvelope>(value)
        .map_err(|_| "La información de la release no se pudo leer.".to_string())?
        .release)
}

/// Catálogo oficial de efectos de sonido.
pub fn sfx_catalog() -> Result<Vec<SfxAsset>, String> {
    let value = bridge::invoke("services.py", "sfx_catalog", &[])?;
    Ok(serde_json::from_value::<SfxEnvelope>(value)
        .map_err(|_| "El catálogo de efectos no se pudo leer.".to_string())?
        .assets)
}

/// Plantillas instaladas y básicas disponibles para las propuestas.
pub fn templates() -> Result<(Vec<TemplateInfo>, Vec<String>), String> {
    let value = bridge::invoke("services.py", "templates", &[])?;
    let parsed = serde_json::from_value::<TemplatesEnvelope>(value)
        .map_err(|_| "El catálogo de plantillas no se pudo leer.".to_string())?;
    Ok((parsed.templates, parsed.diagnostics))
}

/// Guarda la clave API del proveedor indicado en la credencial estándar del usuario.
pub fn save_key(provider: &str, key: &str) -> Result<(), String> {
    bridge::invoke(
        "services.py",
        "save_key",
        &[("provider", provider), ("key", key)],
    )?;
    Ok(())
}

/// Alinea y corrige los subtítulos con el guion y el glosario indicados.
///
/// `cues` usa fotogramas relativos al origen de la fuente, como en la mesa editorial.
pub fn align(
    cues: &[(f64, f64, String)],
    script: &str,
    glossary: &str,
    detect_markers: bool,
) -> Result<Alignment, String> {
    let payload: Vec<Value> = cues
        .iter()
        .map(|(start, end, text)| {
            serde_json::json!({
                "text": text,
                "start_frame": start,
                "end_frame": end,
                "track_index": 1,
            })
        })
        .collect();
    let cues = serde_json::to_string(&payload).map_err(|e| e.to_string())?;
    let detect = if detect_markers { "true" } else { "false" };
    let value = bridge::invoke(
        "services.py",
        "align",
        &[
            ("cues", cues.as_str()),
            ("script", script),
            ("glossary", glossary),
            ("detect_markers", detect),
        ],
    )?;
    serde_json::from_value::<Alignment>(value)
        .map_err(|_| "La corrección recibida no se pudo leer.".to_string())
}

/// Inserta marcadores en la línea de tiempo activa de Resolve.
pub fn insert_markers(markers: &[Marker], snapshot: &Value) -> Result<usize, String> {
    if markers.is_empty() {
        return Err("No hay marcadores para insertar.".into());
    }
    let payload: Vec<Value> = markers
        .iter()
        .map(|marker| {
            serde_json::json!({
                "frame": marker.frame,
                "color": marker.color,
                "name": marker.name,
                "note": marker.note,
            })
        })
        .collect();
    let value = bridge::invoke_json(
        "services.py",
        "insert_markers",
        serde_json::json!({"markers":payload,"snapshot":snapshot}),
    )?;
    Ok(value
        .get("inserted")
        .and_then(Value::as_u64)
        .unwrap_or_default() as usize)
}

/// Guarda el modelo, el proveedor y las preferencias editoriales.
pub fn save_settings(
    provider: &str,
    model: &str,
    preferences: &EditorialPreferences,
) -> Result<(), String> {
    bridge::invoke(
        "services.py",
        "save_settings",
        &[
            ("provider", provider),
            ("model", model),
            ("mode", preferences.mode.as_str()),
            ("format", preferences.format.as_str()),
            ("density", preferences.density.as_str()),
            ("direction", preferences.direction.as_str()),
            ("track_mode", preferences.track_mode.as_str()),
            ("batch_size", preferences.batch_size.as_str()),
        ],
    )?;
    Ok(())
}
