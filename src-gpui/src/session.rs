//! Ciclo de edición independiente de GPUI, sin I/O implícita ni acceso a Resolve.
//!
//! La sesión conserva tres estados distintos: texto original, texto guardado en
//! memoria y último estado cargado/exportado. Un borrador no sustituye al bloque
//! hasta que se confirma; las operaciones por lote son transaccionales.
use crate::subtitles::{self, Document};
use std::{
    collections::VecDeque,
    path::{Path, PathBuf},
    sync::atomic::{AtomicU64, Ordering},
};

const HISTORY_LIMIT: usize = 32;
static NEXT_ID: AtomicU64 = AtomicU64::new(1);

#[derive(Debug)]
struct TextChange {
    index: usize,
    before: String,
    after: String,
}
type ChangeSet = Vec<TextChange>;

#[derive(Debug)]
pub struct SubtitleSession {
    document: Document,
    selected: Option<usize>,
    draft: String,
    saved_texts: Vec<String>,
    dirty: bool,
    undo: VecDeque<ChangeSet>,
    redo: Vec<ChangeSet>,
    document_id: u64,
    revision: u64,
    export_revision: u64,
}

impl Default for SubtitleSession {
    fn default() -> Self {
        Self {
            document: Document::default(),
            selected: None,
            draft: String::new(),
            saved_texts: vec![],
            dirty: false,
            undo: VecDeque::new(),
            redo: vec![],
            document_id: NEXT_ID.fetch_add(1, Ordering::Relaxed),
            revision: 0,
            export_revision: 0,
        }
    }
}

impl SubtitleSession {
    pub fn document(&self) -> &Document {
        &self.document
    }
    pub fn selected(&self) -> Option<usize> {
        self.selected
    }
    pub fn draft(&self) -> &str {
        &self.draft
    }
    pub fn has_draft(&self) -> bool {
        self.selected
            .is_some_and(|i| self.draft != self.document.cues[i].text)
    }
    pub fn is_dirty(&self) -> bool {
        self.dirty
    }
    pub fn can_undo(&self) -> bool {
        !self.undo.is_empty() && !self.has_draft()
    }
    pub fn can_redo(&self) -> bool {
        !self.redo.is_empty() && !self.has_draft()
    }

    pub fn filtered_indices(&self, query: &str) -> Vec<usize> {
        let query = query.to_lowercase();
        self.document
            .cues
            .iter()
            .enumerate()
            .filter(|(_, cue)| {
                query.is_empty()
                    || cue.text.to_lowercase().contains(&query)
                    || cue.original.to_lowercase().contains(&query)
            })
            .map(|(index, _)| index)
            .collect()
    }

    pub fn load(&mut self, document: Document) -> Result<(), String> {
        if self.is_dirty() || self.has_draft() {
            return Err("Exporta o restaura los cambios y guarda o descarta el borrador antes de abrir otra fuente.".into());
        }
        validate_document(&document)?;
        let saved_texts = document.cues.iter().map(|c| c.text.clone()).collect();
        *self = Self {
            selected: Some(0),
            draft: document.cues[0].text.clone(),
            document,
            saved_texts,
            ..Default::default()
        };
        Ok(())
    }

    pub fn select(&mut self, index: usize) -> Result<(), String> {
        if index >= self.document.cues.len() {
            return Err("Ese bloque de subtítulos ya no está disponible.".into());
        }
        if self.selected == Some(index) {
            return Ok(());
        }
        self.require_saved_draft()?;
        self.selected = Some(index);
        self.sync_draft();
        Ok(())
    }

    pub fn set_draft(&mut self, text: String) {
        if self.selected.is_some() {
            self.draft = text;
        }
    }

    pub fn discard_draft(&mut self) {
        self.sync_draft();
    }

    pub fn save_draft(&mut self) -> Result<usize, String> {
        let index = self
            .selected
            .ok_or("Selecciona un subtítulo para editarlo.")?;
        let text = self
            .draft
            .replace("\r\n", "\n")
            .replace('\r', "\n")
            .lines()
            .map(str::trim)
            .filter(|line| !line.is_empty())
            .collect::<Vec<_>>()
            .join("\n");
        if text.is_empty() {
            return Err("El subtítulo no puede quedar vacío.".into());
        }
        let mut texts = self.texts();
        texts[index] = text;
        Ok(self.apply_texts(texts))
    }

    pub fn normalize(&mut self) -> Result<usize, String> {
        self.require_document()?;
        self.require_saved_draft()?;
        let texts = self
            .document
            .cues
            .iter()
            .map(|c| subtitles::normalize(&c.text))
            .collect::<Result<Vec<_>, _>>()?;
        Ok(self.apply_texts(texts))
    }

    pub fn replace(
        &mut self,
        find: &str,
        replacement: &str,
        case_sensitive: bool,
    ) -> Result<usize, String> {
        self.require_document()?;
        self.require_saved_draft()?;
        let mut candidate = self.document.clone();
        candidate.replace(find, replacement, case_sensitive)?;
        validate_export_texts(&candidate)?;
        Ok(self.apply_texts(candidate.cues.into_iter().map(|c| c.text).collect()))
    }

    pub fn restore_all(&mut self) -> Result<usize, String> {
        self.require_document()?;
        self.require_saved_draft()?;
        let texts = self
            .document
            .cues
            .iter()
            .map(|c| c.original.clone())
            .collect();
        Ok(self.apply_texts(texts))
    }

    pub fn undo(&mut self) -> Result<(), String> {
        self.require_saved_draft()?;
        let changes = self
            .undo
            .pop_back()
            .ok_or("No hay cambios para deshacer.")?;
        for change in &changes {
            self.document.cues[change.index].text = change.before.clone();
        }
        self.redo.push(changes);
        self.changed();
        Ok(())
    }

    pub fn redo(&mut self) -> Result<(), String> {
        self.require_saved_draft()?;
        let changes = self.redo.pop().ok_or("No hay cambios para rehacer.")?;
        for change in &changes {
            self.document.cues[change.index].text = change.after.clone();
        }
        self.undo.push_back(changes);
        self.changed();
        Ok(())
    }

    pub fn export_snapshot(&self) -> Result<ExportSnapshot, String> {
        self.require_document()?;
        self.require_saved_draft()?;
        validate_export_texts(&self.document)?;
        Ok(ExportSnapshot {
            document_id: self.document_id,
            revision: self.revision,
            texts: self.texts(),
            content: self.document.export(),
        })
    }

    pub fn accept_export(&mut self, receipt: ExportReceipt) -> Result<(), String> {
        if receipt.document_id != self.document_id {
            return Err("El archivo se exportó, pero pertenece a otra carga de subtítulos. La fuente actual se ha conservado.".into());
        }
        if receipt.revision < self.export_revision {
            return Err("El archivo se exportó, pero ya se registró una exportación más reciente. Los cambios actuales se han conservado.".into());
        }
        self.saved_texts = receipt.texts;
        self.export_revision = receipt.revision;
        self.refresh_dirty();
        Ok(())
    }

    fn require_document(&self) -> Result<(), String> {
        if self.document.cues.is_empty() {
            Err("Carga subtítulos antes de continuar.".into())
        } else {
            Ok(())
        }
    }
    fn require_saved_draft(&self) -> Result<(), String> {
        if self.has_draft() {
            Err("Guarda o descarta la edición del bloque antes de continuar.".into())
        } else {
            Ok(())
        }
    }
    fn sync_draft(&mut self) {
        self.draft = self
            .selected
            .map(|i| self.document.cues[i].text.clone())
            .unwrap_or_default();
    }
    fn texts(&self) -> Vec<String> {
        self.document.cues.iter().map(|c| c.text.clone()).collect()
    }
    fn refresh_dirty(&mut self) {
        self.dirty = self
            .document
            .cues
            .iter()
            .map(|c| &c.text)
            .ne(self.saved_texts.iter());
    }
    fn changed(&mut self) {
        self.revision += 1;
        self.refresh_dirty();
        self.sync_draft();
    }
    fn apply_texts(&mut self, texts: Vec<String>) -> usize {
        debug_assert_eq!(texts.len(), self.document.cues.len());
        let changes: ChangeSet = self
            .document
            .cues
            .iter()
            .zip(texts)
            .enumerate()
            .filter(|(_, (cue, text))| cue.text != *text)
            .map(|(index, (cue, after))| TextChange {
                index,
                before: cue.text.clone(),
                after,
            })
            .collect();
        let count = changes.len();
        if count > 0 {
            for change in &changes {
                self.document.cues[change.index].text = change.after.clone();
            }
            self.undo.push_back(changes);
            if self.undo.len() > HISTORY_LIMIT {
                self.undo.pop_front();
            }
            self.redo.clear();
            self.changed();
        } else {
            self.sync_draft();
        }
        count
    }
}

fn validate_document(document: &Document) -> Result<(), String> {
    if document.cues.is_empty() {
        return Err("La fuente no contiene subtítulos válidos.".into());
    }
    if document
        .cues
        .iter()
        .any(|c| c.end_ms <= c.start_ms || c.text.trim().is_empty() || c.original.trim().is_empty())
    {
        return Err("La fuente contiene un bloque vacío o sin duración positiva.".into());
    }
    if document
        .cues
        .windows(2)
        .any(|pair| pair[1].start_ms < pair[0].start_ms)
    {
        return Err("La fuente contiene subtítulos desordenados.".into());
    }
    Ok(())
}

fn validate_export_texts(document: &Document) -> Result<(), String> {
    for (index, cue) in document.cues.iter().enumerate() {
        if cue.text.trim().is_empty() {
            return Err(format!("El bloque {} está vacío.", index + 1));
        }
        if cue.text.contains('\r') || cue.text.lines().any(|line| line.trim().is_empty()) {
            return Err(format!(
                "El bloque {} contiene saltos de línea que romperían el SRT. Normalízalo o guarda una edición sin líneas vacías.",
                index + 1
            ));
        }
    }
    Ok(())
}

/// Copia transferible al executor; no contiene una referencia mutable a la sesión.
#[derive(Debug)]
pub struct ExportSnapshot {
    document_id: u64,
    revision: u64,
    texts: Vec<String>,
    content: String,
}
impl ExportSnapshot {
    pub fn save_new(self, path: &Path) -> Result<ExportReceipt, String> {
        subtitles::save_new(path, &self.content)?;
        Ok(ExportReceipt {
            document_id: self.document_id,
            revision: self.revision,
            texts: self.texts,
            path: path.to_owned(),
        })
    }
}

/// Solo se puede obtener tras una escritura confirmada; no se construye desde la UI.
#[derive(Debug)]
pub struct ExportReceipt {
    document_id: u64,
    revision: u64,
    texts: Vec<String>,
    path: PathBuf,
}
impl ExportReceipt {
    pub fn path(&self) -> &Path {
        &self.path
    }
}

#[cfg(test)]
#[path = "session_tests.rs"]
mod tests;
