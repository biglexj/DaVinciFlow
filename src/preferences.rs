//! Preferencias de la ventana nativa sincronizadas con el directorio de datos del checkout.
use serde::{Deserialize, Serialize};
use std::{
    collections::BTreeMap,
    path::{Path, PathBuf},
};

/// Raíz del repositorio cuando el ejecutable se compila o corre en desarrollo.
fn repo_root() -> Option<PathBuf> {
    let root = crate::bridge::root();
    root.join("Cargo.toml").is_file().then_some(root)
}

/// Indica si estamos en modo desarrollo (checkout con `Cargo.toml`).
pub fn is_development() -> bool {
    repo_root().is_some()
}

/// Directorio de datos del usuario; en desarrollo usa una subcarpeta aislada por checkout.
pub fn user_data_dir() -> PathBuf {
    let home = std::env::var_os(if cfg!(windows) { "USERPROFILE" } else { "HOME" })
        .or_else(|| std::env::var_os(if cfg!(windows) { "HOME" } else { "USERPROFILE" }))
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("."));
    let base = home.join(".davinci_flow");
    if let Some(root) = repo_root() {
        use std::{
            collections::hash_map::DefaultHasher,
            hash::{Hash, Hasher},
        };
        let mut hasher = DefaultHasher::new();
        root.to_string_lossy().to_lowercase().hash(&mut hasher);
        return base
            .join("development")
            .join(format!("gpui-{:016x}", hasher.finish()));
    }
    base.join("gpui")
}

fn preferences_path() -> PathBuf {
    user_data_dir().join("library.json")
}

fn default_appearance_theme() -> String {
    "aurora".into()
}

fn default_appearance_mode() -> String {
    "dark".into()
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Preferences {
    /// Carpetas indexadas por categoría.
    #[serde(default)]
    pub folders: BTreeMap<String, Vec<String>>,
    /// Recursos compartidos con la IA (máximo 80, como en la interfaz vigente).
    #[serde(default)]
    pub selected: Vec<String>,
    /// Tema de apariencia: "aurora" (predeterminado) o "classic".
    #[serde(default = "default_appearance_theme")]
    pub appearance_theme: String,
    /// Modo de apariencia: "dark" u "light".
    #[serde(default = "default_appearance_mode")]
    pub appearance_mode: String,
}

impl Default for Preferences {
    fn default() -> Self {
        Self {
            folders: BTreeMap::new(),
            selected: Vec::new(),
            appearance_theme: default_appearance_theme(),
            appearance_mode: default_appearance_mode(),
        }
    }
}

impl Preferences {
    /// Lee las preferencias; un archivo ausente o dañado no impide abrir la ventana.
    pub fn load() -> Self {
        Self::load_checked().unwrap_or_default()
    }

    pub fn load_checked() -> Result<Self, String> {
        Self::load_from(&preferences_path())
    }

    fn load_from(path: &Path) -> Result<Self, String> {
        let text = match std::fs::read_to_string(path) {
            Ok(text) => text,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
                return Ok(Self::default());
            }
            Err(error) => return Err(format!("No se pudieron leer las preferencias: {error}")),
        };
        let result: Self = serde_json::from_str(&text).map_err(|_| {
            "Las preferencias de biblioteca están dañadas. Conserva el archivo para revisarlo."
                .to_string()
        })?;
        if result.selected.len() > 80
            || result
                .selected
                .iter()
                .collect::<std::collections::HashSet<_>>()
                .len()
                != result.selected.len()
        {
            return Err("La selección guardada contiene duplicados o supera 80 recursos.".into());
        }
        Ok(result)
    }

    /// Guarda de forma atómica: el archivo anterior se conserva si algo falla.
    pub fn save(&self) -> Result<(), String> {
        let path = preferences_path();
        // Una sesión abierta con valores de emergencia nunca sobrescribe un archivo dañado.
        Self::load_from(&path)?;
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| format!("No se pudo crear la carpeta de preferencias: {e}"))?;
        }
        let content = serde_json::to_string_pretty(self)
            .map_err(|e| format!("No se pudieron preparar las preferencias: {e}"))?;
        let temporary = path.with_extension("tmp");
        std::fs::write(&temporary, content)
            .map_err(|e| format!("No se pudo escribir las preferencias: {e}"))?;
        std::fs::rename(&temporary, &path)
            .map_err(|e| format!("No se pudieron guardar las preferencias: {e}"))
    }

    pub fn folders_for(&self, category: &str) -> Vec<PathBuf> {
        self.folders
            .get(category)
            .map(|values| values.iter().map(PathBuf::from).collect())
            .unwrap_or_default()
    }

    pub fn set_folders(&mut self, category: &str, folders: Vec<PathBuf>) {
        let values = folders
            .iter()
            .map(|path| path.to_string_lossy().into_owned())
            .collect();
        self.folders.insert(category.to_owned(), values);
    }

    pub fn clear_category(&mut self, category: &str) {
        self.folders.remove(category);
    }

    pub fn clear_all(&mut self) {
        self.folders.clear();
        self.selected.clear();
    }

    /// Marca o desmarca un recurso; el límite de 80 es el vigente en Flet.
    pub fn toggle_selected(&mut self, id: &str) -> Result<bool, String> {
        if let Some(position) = self.selected.iter().position(|value| value == id) {
            self.selected.remove(position);
            return Ok(false);
        }
        if self.selected.len() >= 80 {
            return Err("Elige hasta 80 recursos relevantes para esta propuesta.".into());
        }
        self.selected.push(id.to_owned());
        Ok(true)
    }

    pub fn is_selected(&self, id: &str) -> bool {
        self.selected.iter().any(|value| value == id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn selection_respects_the_current_limit() {
        let mut preferences = Preferences::default();
        for index in 0..80 {
            assert!(preferences.toggle_selected(&format!("r{index}")).unwrap());
        }
        assert!(preferences.toggle_selected("extra").is_err());
        assert_eq!(preferences.selected.len(), 80);
        assert!(preferences.toggle_selected("r0").is_ok());
        assert_eq!(preferences.selected.len(), 79);
    }

    #[test]
    fn folders_are_stored_per_category() {
        let mut preferences = Preferences::default();
        preferences.set_folders("visuals", vec![PathBuf::from("C:/medios")]);
        assert_eq!(
            preferences.folders_for("visuals"),
            vec![PathBuf::from("C:/medios")]
        );
        assert!(preferences.folders_for("music").is_empty());
    }
    #[test]
    fn corrupted_preferences_are_reported_and_the_original_is_preserved() {
        let folder =
            std::env::temp_dir().join(format!("flow-preferences-test-{}", std::process::id()));
        std::fs::create_dir_all(&folder).unwrap();
        let path = folder.join("library.json");
        std::fs::write(&path, "{invalid").unwrap();
        assert!(Preferences::load_from(&path).is_err());
        assert_eq!(std::fs::read_to_string(&path).unwrap(), "{invalid");
        std::fs::remove_file(path).unwrap();
        std::fs::remove_dir(folder).unwrap();
    }

    #[test]
    fn new_preferences_start_empty_and_can_be_cleared() {
        let folder = std::env::temp_dir().join(format!("flow-empty-prefs-{}", std::process::id()));
        let missing = folder.join("missing-library.json");
        let loaded = Preferences::load_from(&missing).unwrap();
        assert!(loaded.folders.is_empty());
        assert!(loaded.selected.is_empty());

        let mut prefs = loaded;
        prefs.set_folders("visuals", vec![PathBuf::from("C:/brolls")]);
        prefs.set_folders("sfx", vec![PathBuf::from("C:/sfx")]);
        prefs.toggle_selected("res-1").unwrap();
        prefs.clear_category("visuals");
        assert!(prefs.folders_for("visuals").is_empty());
        assert_eq!(prefs.folders_for("sfx"), vec![PathBuf::from("C:/sfx")]);
        prefs.clear_all();
        assert!(prefs.folders.is_empty());
        assert!(prefs.selected.is_empty());
    }
}
