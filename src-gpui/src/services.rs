//! Servicios del proyecto vistos desde la ventana nativa: ajustes, IA, actualizaciones
//! y catálogos.
use crate::{
    bridge, editorial_config, release_check, sfx, templates as native_templates, text_provider,
};
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

/// Confirmación de escritura de subtítulos nativos en Resolve.
#[derive(Clone, Debug, Default, Deserialize)]
pub struct SubtitleWriteReceipt {
    pub track_index: usize,
    pub cue_count: usize,
    pub srt_path: String,
    #[serde(default)]
    pub confirmed: bool,
    #[serde(default)]
    pub method: String,
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
    #[serde(default, skip_serializing)]
    pub preview_kind: String,
}

#[derive(Clone, Debug, Default, Deserialize)]
pub struct TemplateCatalog {
    pub templates: Vec<TemplateInfo>,
    #[serde(default)]
    pub diagnostics: Vec<String>,
    #[serde(default)]
    pub presets: Vec<String>,
    #[serde(default)]
    pub selected_ids: Vec<String>,
}

#[derive(Clone, Debug, Default, Deserialize)]
pub struct TemplatePreview {
    #[serde(default)]
    pub image: String,
    #[serde(default)]
    pub video: String,
}

fn default_text_input() -> String {
    "StyledText".into()
}
fn default_category() -> String {
    "general".into()
}

#[derive(Deserialize)]
struct TemplatesEnvelope {
    templates: Vec<TemplateInfo>,
}

/// Estado actual del proveedor de IA, sus modelos y las preferencias editoriales.
pub fn settings() -> Result<Settings, String> {
    editorial_config::settings(None)
}

pub fn settings_for(provider: &str) -> Result<Settings, String> {
    editorial_config::settings(Some(provider))
}

/// Catálogo de modelos de Gemini disponible con la credencial configurada.
pub fn scan_models() -> Result<Vec<String>, String> {
    text_provider::scan_models()
}

/// Consulta al asistente con el proveedor de IA configurado.
pub fn assistant(prompt: &str) -> Result<String, String> {
    text_provider::assistant(prompt)
}

/// Última versión publicada en el canal oficial.
pub fn release() -> Result<Option<Release>, String> {
    release_check::latest()
}

/// Catálogo oficial de efectos de sonido.
pub fn sfx_catalog() -> Result<Vec<SfxAsset>, String> {
    Ok(sfx::catalog())
}

/// Plantillas instaladas y básicas disponibles para las propuestas.
pub fn templates() -> Result<(Vec<TemplateInfo>, Vec<String>), String> {
    let parsed = template_catalog()?;
    Ok((parsed.templates, parsed.diagnostics))
}

/// Catálogo completo de plantillas junto con presets y selección activa.
pub fn template_catalog() -> Result<TemplateCatalog, String> {
    native_templates::catalog()
}

/// Lee los títulos disponibles en el Media Pool del proyecto activo de Resolve.
pub fn project_templates() -> Result<Vec<TemplateInfo>, String> {
    if let Some(templates) = crate::resolve_mcp::project_templates()? {
        return Ok(templates);
    }
    let value = bridge::invoke("services.py", "project_templates", &[])?;
    let parsed = serde_json::from_value::<TemplatesEnvelope>(serde_json::json!({
        "templates": value.get("templates").cloned().unwrap_or(Value::Array(vec![]))
    }))
    .map_err(|_| "Los títulos del proyecto no se pudieron leer.".to_string())?;
    Ok(parsed.templates)
}

/// Obtiene la imagen o animación de vista previa de una plantilla.
pub fn template_preview(template: &TemplateInfo) -> Result<TemplatePreview, String> {
    let preview = native_templates::preview(template)?;
    if !preview.image.is_empty() || !preview.video.is_empty() {
        return Ok(preview);
    }
    let value = bridge::invoke_json(
        "services.py",
        "template_preview",
        serde_json::json!({"template": template}),
    )?;
    serde_json::from_value::<TemplatePreview>(value)
        .map_err(|_| "No se pudo leer la vista previa de la plantilla.".to_string())
}

/// Guarda un preset de selección de plantillas.
pub fn save_preset(name: &str, ids: &[String]) -> Result<(usize, Vec<String>), String> {
    native_templates::save_preset(name, ids)
}

/// Activa un preset de plantillas guardado.
pub fn use_preset(name: &str) -> Result<(usize, Vec<String>), String> {
    native_templates::use_preset(name)
}

/// Aplica un pack rápido de plantillas por categoría.
pub fn choose_pack(pack: &str) -> Result<(usize, Vec<String>), String> {
    native_templates::choose_pack(pack)
}

/// Asigna el nodo Text+ y su entrada de texto a las plantillas elegidas.
pub fn assign_node(ids: &[String], text_tool: &str, text_input: &str) -> Result<usize, String> {
    native_templates::assign_node(ids, text_tool, text_input)
}

/// Guarda la clave API del proveedor indicado en la credencial estándar del usuario.
pub fn save_key(provider: &str, key: &str) -> Result<(), String> {
    editorial_config::save_key(provider, key)
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
    crate::alignment::align(cues, script, glossary, detect_markers)
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
    editorial_config::save_settings(provider, model, preferences)
}

/// Sincroniza las carpetas y selecciones de la biblioteca con el motor editorial.
pub fn sync_library(
    folders: &std::collections::BTreeMap<String, Vec<String>>,
    selected: &[String],
) -> Result<(), String> {
    editorial_config::sync_library(folders, selected)
}

/// Escribe los subtítulos en la pista nativa de subtítulos de DaVinci Resolve.
pub fn write_subtitles(
    cues: &[(f64, f64, String)],
    track_index: Option<u32>,
    file_name: &str,
) -> Result<SubtitleWriteReceipt, String> {
    let payload: Vec<Value> = cues
        .iter()
        .map(|(start, end, text)| {
            serde_json::json!({
                "text": text,
                "start_frame": start,
                "end_frame": end,
                "track_index": track_index.unwrap_or(1),
            })
        })
        .collect();
    let value = bridge::invoke_json(
        "services.py",
        "write_subtitles",
        serde_json::json!({
            "cues": payload,
            "track_index": track_index,
            "file_name": file_name,
        }),
    )?;
    serde_json::from_value::<SubtitleWriteReceipt>(value)
        .map_err(|_| "Resolve no devolvió una confirmación válida de subtítulos.".into())
}
