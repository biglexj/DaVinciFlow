//! Contratos tipados de descarga, vistas previas y voz.
use crate::bridge;
use serde::Deserialize;
use serde_json::{Value, json};
use std::path::{Path, PathBuf};
#[derive(Clone, Debug, Deserialize)]
pub struct MediaInfo {
    pub title: String,
    pub duration_seconds: f64,
    #[serde(default)]
    pub duration_display: String,
    pub uploader: Option<String>,
    #[serde(default)]
    pub extractor: Option<String>,
    #[serde(default)]
    pub thumbnail_url: Option<String>,
    #[serde(default)]
    pub is_audio: bool,
}
#[derive(Clone, Debug, Deserialize)]
pub struct Download {
    pub path: PathBuf,
    pub title: String,
    #[serde(default)]
    pub kind: String,
    pub imported: bool,
    #[serde(default)]
    pub resolve_bin: String,
    pub message: String,
}
#[derive(Clone, Debug, Deserialize)]
pub struct Voice {
    pub id: String,
    pub name: String,
    pub provider: String,
    #[serde(default)]
    pub ready: bool,
}
#[derive(Clone, Debug, Deserialize)]
pub struct VoiceEngine {
    pub id: String,
    pub name: String,
    #[serde(default)]
    pub available: bool,
}
#[derive(Clone, Debug, Default, Deserialize)]
pub struct VoiceCatalog {
    pub authenticated: bool,
    pub user: String,
    #[serde(default)]
    pub plan: String,
    #[serde(default)]
    pub internal: bool,
    pub voices: Vec<Voice>,
    #[serde(default)]
    pub engines: Vec<VoiceEngine>,
    pub balance: Option<u64>,
    pub pending: bool,
    #[serde(default)]
    pub warnings: Vec<String>,
}
fn request<T: serde::de::DeserializeOwned>(operation: &str, args: Value) -> Result<T, String> {
    serde_json::from_value(bridge::invoke_json("media.py", operation, args)?)
        .map_err(|_| "El servicio de medios devolvió una respuesta inválida.".into())
}
pub fn analyze(url: &str) -> Result<MediaInfo, String> {
    request("fetch_analyze", json!({"url":url}))
}
pub fn download(url: &str, kind: &str, directory: &str, import: bool) -> Result<Download, String> {
    if !matches!(kind, "video" | "audio") {
        return Err("Tipo de medio desconocido.".into());
    }
    request(
        "fetch_download",
        json!({"url":url,"kind":kind,"directory":directory,"import":import}),
    )
}
fn path(operation: &str, args: Value) -> Result<PathBuf, String> {
    let value: Value = request(operation, args)?;
    let path = PathBuf::from(
        value["path"]
            .as_str()
            .ok_or("No se confirmó un archivo de salida.")?,
    );
    if !path.is_file() {
        return Err("El servicio no produjo un archivo accesible.".into());
    }
    Ok(path)
}
pub fn preview(source: &Path) -> Result<PathBuf, String> {
    path("preview", json!({"path":source}))
}
pub fn import(source: &Path) -> Result<Value, String> {
    request("import_media", json!({"path":source}))
}
pub fn import_voice(source: &Path) -> Result<Value, String> {
    request("import_media", json!({"path":source,"voice_bin":true}))
}
pub fn validate_voice(source: &Path) -> Result<PathBuf, String> {
    path("voice_validate", json!({"path":source}))
}
pub fn play_sound(source: &Path) -> Result<bool, String> {
    let value: Value = request("play_sound", json!({"path":source}))?;
    Ok(value["playing"].as_bool().unwrap_or(false))
}
pub fn stop_sound() -> Result<(), String> {
    let _: Value = request("stop_sound", json!({}))?;
    Ok(())
}
pub fn sfx(id: &str) -> Result<PathBuf, String> {
    path("sfx_file", json!({"id":id}))
}
pub fn voices() -> Result<VoiceCatalog, String> {
    request("voice_catalog", json!({}))
}
pub fn login_with(provider: &str) -> Result<String, String> {
    let value: Value = request("voice_login", json!({"provider":provider}))?;
    Ok(value["url"]
        .as_str()
        .ok_or("Aurora no devolvió una URL de acceso.")?
        .into())
}
pub fn login() -> Result<String, String> {
    login_with("google")
}
pub fn cancel_login() -> Result<(), String> {
    let _: Value = request("voice_cancel", json!({}))?;
    Ok(())
}
pub fn callback_ready() -> Result<bool, String> {
    let value: Value = request("voice_callback_ready", json!({}))?;
    Ok(value["ready"].as_bool().unwrap_or(false))
}
pub fn complete_login() -> Result<(), String> {
    let _: Value = request("voice_complete", json!({}))?;
    Ok(())
}
pub fn logout() -> Result<(), String> {
    let _: Value = request("voice_logout", json!({}))?;
    Ok(())
}
pub fn quote(text: &str, voice: &Voice) -> Result<u64, String> {
    let value: Value = request(
        "voice_quote",
        json!({"text":text,"voice":voice.id,"provider":voice.provider}),
    )?;
    value["cost"]
        .as_u64()
        .ok_or("No se pudo confirmar el consumo de voz.".into())
}
pub fn generate(text: &str, voice: &Voice, max_cost: u64) -> Result<PathBuf, String> {
    path(
        "voice_generate",
        json!({"text":text,"voice":voice.id,"provider":voice.provider,"max_cost":max_cost}),
    )
}
pub fn recover() -> Result<PathBuf, String> {
    path("voice_recover", json!({}))
}
