//! Contratos tipados de descarga, vistas previas y voz.
use crate::bridge;
use serde::Deserialize;
use serde_json::{Value, json};
use std::path::{Path, PathBuf};
#[derive(Clone, Debug, Deserialize)]
pub struct MediaInfo {
    pub title: String,
    pub duration_seconds: f64,
    pub uploader: Option<String>,
}
#[derive(Clone, Debug, Deserialize)]
pub struct Download {
    pub path: PathBuf,
    pub title: String,
    pub imported: bool,
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
#[derive(Clone, Debug, Default, Deserialize)]
pub struct VoiceCatalog {
    pub authenticated: bool,
    pub user: String,
    pub voices: Vec<Voice>,
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
pub fn sfx(id: &str) -> Result<PathBuf, String> {
    path("sfx_file", json!({"id":id}))
}
pub fn voices() -> Result<VoiceCatalog, String> {
    request("voice_catalog", json!({}))
}
pub fn login() -> Result<String, String> {
    let value: Value = request("voice_login", json!({"provider":"google"}))?;
    Ok(value["url"]
        .as_str()
        .ok_or("Aurora no devolvió una URL de acceso.")?
        .into())
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
