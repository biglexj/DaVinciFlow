//! Preferencias propias de la ventana nativa; no toca el archivo de Flet.
use serde::{Deserialize, Serialize};
use std::{collections::BTreeMap, path::PathBuf};

/// Carpeta de datos de la ventana nativa, separada de la instalación estable.
pub fn user_data_dir() -> PathBuf {
    let home = std::env::var_os(if cfg!(windows) { "USERPROFILE" } else { "HOME" })
        .or_else(|| std::env::var_os(if cfg!(windows) { "HOME" } else { "USERPROFILE" }))
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("."));
    home.join(".davinci_flow").join("gpui")
}

fn preferences_path() -> PathBuf {
    user_data_dir().join("library.json")
}

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct Preferences {
    /// Carpetas indexadas por categoría.
    #[serde(default)]
    pub folders: BTreeMap<String, Vec<String>>,
    /// Recursos compartidos con la IA (máximo 80, como en la interfaz vigente).
    #[serde(default)]
    pub selected: Vec<String>,
}

impl Preferences {
    /// Lee las preferencias; un archivo ausente o dañado no impide abrir la ventana.
    pub fn load() -> Self {
        Self::load_checked().unwrap_or_default()
    }

    pub fn load_checked() -> Result<Self, String> {
        Self::load_from(&preferences_path())
    }

    fn load_from(path: &std::path::Path) -> Result<Self, String> {
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
}
