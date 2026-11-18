//! Ciclo de edición independiente de GPUI, sin I/O implícita ni acceso a Resolve.
//!
//! La sesión conserva tres estados distintos: texto original, texto guardado en
//! memoria y último estado cargado/exportado. Un borrador no sustituye al bloque
//! hasta que se confirma; las operaciones por lote son transaccionales.
use crate::subtitles::{self, Document, TextEdit};
use std::{
    collections::VecDeque,
    path::{Path, PathBuf},
    sync::atomic::{AtomicU64, Ordering},
};

const HISTORY_LIMIT: usize = 32;
const HISTORY_MEMORY_LIMIT: usize = 64 * 1024 * 1024;
static NEXT_ID: AtomicU64 = AtomicU64::new(1);

#[derive(Debug)]
struct ChangeSet {
    edits: Vec<TextEdit>,
    bytes: usize,
}

impl ChangeSet {
    fn new(edits: Vec<TextEdit>) -> Self {
        let bytes = edits.capacity() * std::mem::size_of::<TextEdit>()
            + edits
                .iter()
                .map(|edit| edit.before.capacity() + edit.after.capacity())
                .sum::<usize>();
        Self { edits, bytes }
    }
}

#[derive(Debug)]
pub struct SubtitleSession {
    document: Document,
    selected: Option<usize>,
    draft: String,
    saved_texts: Vec<String>,
    unsaved_count: usize,
    undo: VecDeque<ChangeSet>,
    redo: Vec<ChangeSet>,
    document_id: u64,
    revision: u64,
    export_revision: u64,
    history_bytes: usize,
    history_memory_limit: usize,
}

impl Default for SubtitleSession {
    fn default() -> Self {
        Self {
            document: Document::default(),
            selected: None,
            draft: String::new(),
            saved_texts: vec![],
            unsaved_count: 0,
            undo: VecDeque::new(),
            redo: vec![],
            document_id: NEXT_ID.fetch_add(1, Ordering::Relaxed),
            revision: 0,
            export_revision: 0,
            history_bytes: 0,
            history_memory_limit: HISTORY_MEMORY_LIMIT,
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
        self.unsaved_count > 0
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
        let edits = if text == self.document.cues[index].text {
            vec![]
        } else {
            vec![TextEdit {
                index,
                before: self.document.cues[index].text.clone(),
                after: text,
            }]
        };
        self.apply_edits(edits)
    }

    pub fn normalize(&mut self) -> Result<usize, String> {
        self.require_document()?;
        self.require_saved_draft()?;
        self.apply_edits(self.document.plan_normalization()?)
    }

    pub fn replace(
        &mut self,
        find: &str,
        replacement: &str,
        case_sensitive: bool,
    ) -> Result<usize, String> {
        self.require_document()?;
        self.require_saved_draft()?;
        let edits = self
            .document
            .plan_replace(find, replacement, case_sensitive)?;
        // Validar la vista resultante sin clonar el documento entero.
        let mut pending = edits.iter().peekable();
        for (index, cue) in self.document.cues.iter().enumerate() {
            let text = if pending.peek().is_some_and(|edit| edit.index == index) {
                pending.next().unwrap().after.as_str()
            } else {
                cue.text.as_str()
            };
            validate_export_text(index, text)?;
        }
        self.apply_edits(edits)
    }

    /// Restaura el texto original de un bloque concreto.
    pub fn restore_cue(&mut self, index: usize) -> Result<usize, String> {
        self.require_document()?;
        self.require_saved_draft()?;
        let Some(cue) = self.document.cues.get(index) else {
            return Err("Ese bloque de subtítulos ya no está disponible.".into());
        };
        if cue.text == cue.original {
            return Ok(0);
        }
        let edit = TextEdit {
            index,
            before: cue.text.clone(),
            after: cue.original.clone(),
        };
        self.apply_edits(vec![edit])
    }

    /// Aplica un glosario de términos; la operación es transaccional.
    pub fn apply_glossary(&mut self, glossary: &str) -> Result<usize, String> {
        self.require_document()?;
        self.require_saved_draft()?;
        if glossary.trim().is_empty() {
            return Err("Ingresa términos de glosario (ej: término: Reemplazo).".into());
        }
        let terms = parse_glossary(glossary);
        if terms.is_empty() {
            return Err("Formato de glosario inválido. Usa: término: Reemplazo".into());
        }
        let mut edits = Vec::new();
        for (index, cue) in self.document.cues.iter().enumerate() {
            let mut text = cue.text.clone();
            for (term, replacement) in &terms {
                text = replace_word(&text, term, replacement)?;
            }
            if text != cue.text {
                validate_export_text(index, &text)?;
                edits.push(TextEdit {
                    index,
                    before: cue.text.clone(),
                    after: text,
                });
            }
        }
        self.apply_edits(edits)
    }

    /// Sustituye el texto de todos los bloques de forma transaccional.
    ///
    /// Los tiempos no se tocan y un texto vacío o con líneas en blanco rechaza el
    /// cambio completo, igual que el resto de operaciones por lote.
    pub fn apply_texts(&mut self, texts: Vec<String>) -> Result<usize, String> {
        self.require_document()?;
        self.require_saved_draft()?;
        if texts.len() != self.document.cues.len() {
            return Err("La corrección recibida no corresponde a los subtítulos cargados.".into());
        }
        let mut edits = Vec::new();
        for (index, text) in texts.iter().enumerate() {
            let text = text.trim();
            if text.is_empty() {
                return Err(format!(
                    "El bloque {} quedó vacío tras la corrección.",
                    index + 1
                ));
            }
            if text.contains('\r') || text.lines().any(|line| line.trim().is_empty()) {
                return Err(format!(
                    "El bloque {} contiene saltos de línea que romperían el SRT.",
                    index + 1
                ));
            }
            let cue = &self.document.cues[index];
            if cue.text != text {
                edits.push(TextEdit {
                    index,
                    before: cue.text.clone(),
                    after: text.to_owned(),
                });
            }
        }
        self.apply_edits(edits)
    }

    pub fn restore_all(&mut self) -> Result<usize, String> {
        self.require_document()?;
        self.require_saved_draft()?;
        let edits = self
            .document
            .cues
            .iter()
            .enumerate()
            .filter(|(_, cue)| cue.text != cue.original)
            .map(|(index, cue)| TextEdit {
                index,
                before: cue.text.clone(),
                after: cue.original.clone(),
            })
            .collect();
        self.apply_edits(edits)
    }

    pub fn undo(&mut self) -> Result<(), String> {
        self.require_saved_draft()?;
        let changes = self
            .undo
            .pop_back()
            .ok_or("No hay cambios para deshacer.")?;
        for change in &changes.edits {
            self.update_text(change.index, &change.before);
        }
        self.redo.push(changes);
        self.changed();
        Ok(())
    }

    pub fn redo(&mut self) -> Result<(), String> {
        self.require_saved_draft()?;
        let changes = self.redo.pop().ok_or("No hay cambios para rehacer.")?;
        for change in &changes.edits {
            self.update_text(change.index, &change.after);
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
        self.refresh_unsaved();
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
    fn refresh_unsaved(&mut self) {
        self.unsaved_count = self
            .document
            .cues
            .iter()
            .map(|c| &c.text)
            .zip(&self.saved_texts)
            .filter(|(current, saved)| current != saved)
            .count();
    }
    fn changed(&mut self) {
        self.revision += 1;
        self.sync_draft();
    }
    fn update_text(&mut self, index: usize, text: &str) {
        let cue = &mut self.document.cues[index];
        let saved = &self.saved_texts[index];
        self.unsaved_count -= usize::from(cue.text != *saved);
        self.unsaved_count += usize::from(text != saved);
        cue.text = text.to_owned();
    }
    fn apply_edits(&mut self, edits: Vec<TextEdit>) -> Result<usize, String> {
        let count = edits.len();
        if count == 0 {
            self.sync_draft();
            return Ok(0);
        }
        let changes = ChangeSet::new(edits);
        if changes.bytes > self.history_memory_limit {
            return Err("El cambio supera el presupuesto de memoria del historial. Divide la operación en cambios más pequeños; los subtítulos se han conservado.".into());
        }
        // Rechazar antes de borrar redo o tocar el documento mantiene la operación atómica.
        self.history_bytes -= self.redo.iter().map(|set| set.bytes).sum::<usize>();
        self.redo.clear();
        while self.undo.len() >= HISTORY_LIMIT
            || self.history_bytes + changes.bytes > self.history_memory_limit
        {
            if let Some(old) = self.undo.pop_front() {
                self.history_bytes -= old.bytes;
            } else {
                break;
            }
        }
        for change in &changes.edits {
            self.update_text(change.index, &change.after);
        }
        self.history_bytes += changes.bytes;
        self.undo.push_back(changes);
        self.changed();
        Ok(count)
    }
}

/// Interpreta un glosario: «término: Reemplazo» o «término -> Reemplazo».
fn parse_glossary(text: &str) -> Vec<(String, String)> {
    let mut terms = Vec::new();
    for item in text.split(['\n', ',']) {
        let item = item.trim();
        if item.is_empty() {
            continue;
        }
        let pair = if let Some((term, replacement)) = item.split_once(':') {
            Some((term, replacement))
        } else {
            item.split_once("->")
        };
        let Some((term, replacement)) = pair else {
            continue;
        };
        let term = term.trim();
        let replacement = replacement.trim();
        if term.is_empty() || replacement.is_empty() {
            continue;
        }
        terms.push((term.to_owned(), replacement.to_owned()));
    }
    terms
}

/// Sustituye un término completo sin distinguir mayúsculas, como el glosario vigente.
fn replace_word(text: &str, term: &str, replacement: &str) -> Result<String, String> {
    let escaped = regex::escape(term);
    let word = |value: char| value.is_alphanumeric() || value == '_';
    let prefix = term.starts_with(word);
    let suffix = term.ends_with(word);
    let pattern = regex::RegexBuilder::new(&format!(
        "{}{escaped}{}",
        if prefix { r"\b" } else { "" },
        if suffix { r"\b" } else { "" }
    ))
    .case_insensitive(true)
    .build()
    .map_err(|e| format!("El término del glosario no es válido: {e}"))?;
    Ok(pattern
        .replace_all(text, regex::NoExpand(replacement))
        .into_owned())
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
        validate_export_text(index, &cue.text)?;
    }
    Ok(())
}

fn validate_export_text(index: usize, text: &str) -> Result<(), String> {
    if text.trim().is_empty() {
        return Err(format!("El bloque {} está vacío.", index + 1));
    }
    if text.contains('\r') || text.lines().any(|line| line.trim().is_empty()) {
        return Err(format!(
            "El bloque {} contiene saltos de línea que romperían el SRT. Normalízalo o guarda una edición sin líneas vacías.",
            index + 1
        ));
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
