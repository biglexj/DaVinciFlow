//! Inventario local por categorías, sin decodificar medios ni modificar archivos.
use std::{
    collections::hash_map::DefaultHasher,
    hash::{Hash, Hasher},
    path::{Path, PathBuf},
};
use walkdir::WalkDir;

/// Categorías y rótulos vigentes de la biblioteca Flet.
pub const CATEGORIES: [(&str, &str); 5] = [
    ("visuals", "B-rolls"),
    ("sfx", "Efectos (SFX)"),
    ("music", "Música"),
    ("titles", "Títulos y Fusion"),
    ("documents", "Textos y documentos"),
];

const VIDEO_EXTENSIONS: [&str; 11] = [
    "mp4", "mov", "mkv", "avi", "webm", "m4v", "mxf", "png", "jpg", "jpeg", "webp",
];
const AUDIO_EXTENSIONS: [&str; 6] = ["wav", "mp3", "aac", "flac", "ogg", "m4a"];
const TITLE_EXTENSIONS: [&str; 3] = ["setting", "comp", "drfx"];
const DOCUMENT_EXTENSIONS: [&str; 5] = ["txt", "md", "srt", "pdf", "docx"];

/// Extensiones que la biblioteca vigente admite en cada categoría.
pub fn extensions(category: &str) -> &'static [&'static str] {
    match category {
        "visuals" => &VIDEO_EXTENSIONS,
        "sfx" | "music" => &AUDIO_EXTENSIONS,
        "titles" => &TITLE_EXTENSIONS,
        _ => &DOCUMENT_EXTENSIONS,
    }
}

/// Identificador estable de un recurso dentro de la ventana nativa.
pub fn resource_id(category: &str, path: &Path) -> String {
    let mut hasher = DefaultHasher::new();
    category.hash(&mut hasher);
    path.to_string_lossy().to_lowercase().hash(&mut hasher);
    format!("{category}-{:016x}", hasher.finish())
}

#[derive(Clone, Debug)]
pub struct Resource {
    pub id: String,
    pub name: String,
    pub category: &'static str,
    pub path: PathBuf,
    pub bytes: u64,
}

#[derive(Clone, Debug, Default)]
pub struct Inventory {
    pub category: &'static str,
    pub folders: Vec<PathBuf>,
    pub resources: Vec<Resource>,
    pub warnings: Vec<String>,
}

/// Categoría estática a la que pertenece una extensión.
pub fn category_for(category: &str, extension: &str) -> bool {
    let extension = extension.to_ascii_lowercase();
    extensions(category).contains(&extension.as_str())
}

/// Indexa las carpetas de una categoría; las carpetas inexistentes se informan.
pub fn scan_category(category: &str, folders: &[PathBuf], limit: usize) -> Inventory {
    let mut result = Inventory {
        category: category_of(category),
        folders: folders.to_vec(),
        ..Default::default()
    };
    if folders.is_empty() {
        return result;
    }
    let mut seen = std::collections::HashSet::new();
    for root in folders {
        if !root.is_dir() {
            result
                .warnings
                .push(format!("{}: la carpeta no existe.", label(category)));
            continue;
        }
        let entries = WalkDir::new(root)
            .follow_links(false)
            .sort_by_file_name()
            .into_iter()
            .filter_entry(|e| e.depth() == 0 || !e.file_name().to_string_lossy().starts_with('.'));
        for entry in entries {
            let entry = match entry {
                Ok(e) => e,
                Err(e) => {
                    result.warnings.push(format!(
                        "{}: no se pudo leer una subcarpeta.",
                        label(category)
                    ));
                    let _ = e;
                    continue;
                }
            };
            if !entry.file_type().is_file() {
                continue;
            }
            let Some(extension) = entry.path().extension().and_then(|s| s.to_str()) else {
                continue;
            };
            if !category_for(category, extension) {
                continue;
            }
            if result.resources.len() >= limit {
                result.warnings.push(format!(
                    "Inventario limitado a {limit} archivos. Elige una carpeta más concreta."
                ));
                break;
            }
            let path = entry.path().to_path_buf();
            let id = resource_id(category, &path);
            if !seen.insert(id.clone()) {
                continue;
            }
            let bytes = entry.metadata().map(|m| m.len()).unwrap_or(0);
            result.resources.push(Resource {
                id,
                name: path
                    .strip_prefix(root)
                    .unwrap_or(&path)
                    .to_string_lossy()
                    .into_owned(),
                category: result.category,
                path,
                bytes,
            });
        }
    }
    result
}

/// Etiqueta visible de una categoría.
pub fn label(category: &str) -> &'static str {
    CATEGORIES
        .iter()
        .find(|(key, _)| *key == category)
        .map(|(_, label)| *label)
        .unwrap_or("Recursos")
}

/// Categoría estática equivalente a una clave conocida.
pub fn category_of(category: &str) -> &'static str {
    CATEGORIES
        .iter()
        .find(|(key, _)| *key == category)
        .map(|(key, _)| *key)
        .unwrap_or("documents")
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn actual_folder_filters_hidden_files_and_reports_truncation() {
        let root = std::env::temp_dir().join(format!("df-gpui-test-{}", std::process::id()));
        std::fs::create_dir_all(root.join(".hidden")).unwrap();
        std::fs::write(root.join("a.mp4"), b"video").unwrap();
        std::fs::write(root.join("b.txt"), b"texto").unwrap();
        std::fs::write(root.join("ignore.exe"), b"ignored").unwrap();
        std::fs::write(root.join(".hidden/private.mp4"), b"ignored").unwrap();
        let all = scan_category("visuals", std::slice::from_ref(&root), 100);
        assert_eq!(all.resources.len(), 1);
        assert_eq!(all.resources[0].name, "a.mp4");
        assert_eq!(all.resources[0].category, "visuals");
        let limited = scan_category("visuals", std::slice::from_ref(&root), 0);
        assert_eq!(limited.resources.len(), 0);
        assert_eq!(limited.warnings.len(), 1);
        let missing = scan_category("music", &[PathBuf::from("/no-existe/df-gpui")], 10);
        assert_eq!(missing.resources.len(), 0);
        assert_eq!(missing.warnings.len(), 1);
        std::fs::remove_dir_all(root).unwrap();
    }
    #[test]
    fn categories_follow_the_current_library_contract() {
        assert_eq!(CATEGORIES.len(), 5);
        assert!(category_for("visuals", "MP4"));
        assert!(!category_for("visuals", "wav"));
        assert!(category_for("music", "wav"));
        assert!(category_for("documents", "srt"));
        assert_eq!(label("sfx"), "Efectos (SFX)");
    }
}
