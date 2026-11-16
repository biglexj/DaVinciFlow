//! Inventario local sin decodificar medios ni modificar archivos.
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

#[derive(Clone, Debug)]
pub struct Resource {
    pub name: String,
    pub category: &'static str,
    pub path: PathBuf,
    pub bytes: u64,
}
#[derive(Clone, Debug, Default)]
pub struct Inventory {
    pub root: PathBuf,
    pub resources: Vec<Resource>,
    pub warnings: Vec<String>,
}

pub fn category(extension: &str) -> Option<&'static str> {
    match extension.to_ascii_lowercase().as_str() {
        "mp4" | "mov" | "mkv" | "avi" | "webm" | "mxf" | "m4v" => Some("Vídeo"),
        "wav" | "mp3" | "flac" | "ogg" | "m4a" | "aac" | "aiff" | "aif" => Some("Audio"),
        "jpg" | "jpeg" | "png" | "webp" => Some("Imagen"),
        "setting" | "comp" | "drfx" | "drb" => Some("Títulos"),
        "txt" | "md" | "srt" | "pdf" | "docx" => Some("Documento"),
        _ => None,
    }
}

pub fn scan(root: &Path, limit: usize) -> Result<Inventory, String> {
    if !root.is_dir() {
        return Err("La carpeta de biblioteca no existe o no es accesible.".into());
    }
    let mut result = Inventory {
        root: root.to_owned(),
        ..Default::default()
    };
    let entries = WalkDir::new(root)
        .follow_links(false)
        .sort_by_file_name()
        .into_iter()
        .filter_entry(|e| e.depth() == 0 || !e.file_name().to_string_lossy().starts_with('.'));
    for entry in entries {
        let entry = match entry {
            Ok(e) => e,
            Err(e) => {
                result
                    .warnings
                    .push(format!("No se pudo leer una entrada: {e}"));
                continue;
            }
        };
        if !entry.file_type().is_file() {
            continue;
        }
        let Some(kind) = entry
            .path()
            .extension()
            .and_then(|s| s.to_str())
            .and_then(category)
        else {
            continue;
        };
        if result.resources.len() >= limit {
            result.warnings.push(format!(
                "Inventario limitado a {limit} archivos. Elige una carpeta más concreta."
            ));
            break;
        }
        let bytes = match entry.metadata() {
            Ok(m) => m.len(),
            Err(e) => {
                result
                    .warnings
                    .push(format!("No se pudo leer {}: {e}", entry.path().display()));
                continue;
            }
        };
        result.resources.push(Resource {
            name: entry
                .path()
                .strip_prefix(root)
                .unwrap_or(entry.path())
                .to_string_lossy()
                .into_owned(),
            category: kind,
            path: entry.path().to_owned(),
            bytes,
        });
    }
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn actual_folder_filters_hidden_files_and_reports_truncation() {
        let root = std::env::temp_dir().join(format!("df-gpui-test-{}", std::process::id()));
        std::fs::create_dir_all(root.join(".hidden")).unwrap();
        std::fs::write(root.join("a.SRT"), b"subtitle").unwrap();
        std::fs::write(root.join("b.mp4"), b"media").unwrap();
        std::fs::write(root.join("ignore.exe"), b"ignored").unwrap();
        std::fs::write(root.join(".hidden/private.mp4"), b"ignored").unwrap();
        let all = scan(&root, 100).unwrap();
        assert_eq!(all.resources.len(), 2);
        assert_eq!(all.resources[0].category, "Documento");
        let limited = scan(&root, 1).unwrap();
        assert_eq!(limited.resources.len(), 1);
        assert_eq!(limited.warnings.len(), 1);
        std::fs::remove_dir_all(root).unwrap();
    }
    #[test]
    fn missing_folder_fails_instead_of_returning_empty_success() {
        assert!(scan(Path::new("/this-folder-does-not-exist/df-gpui"), 100).is_err());
    }
}
