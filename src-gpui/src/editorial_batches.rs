//! Avance reanudable de la planificación por tandas, ligado a una revisión del montaje.
use super::{BatchProgress, Decision, Proposal, planner};
use crate::{editorial_config, text_provider::TextProvider};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    ops::Range,
    path::Path,
};

const MAX_FILE: u64 = 32 * 1024 * 1024;

#[derive(Serialize, Deserialize)]
struct Run {
    schema_version: u32,
    snapshot: Value,
    templates: Value,
    options: Value,
    decisions: Vec<Option<Decision>>,
    #[serde(default)]
    model: String,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    history: Vec<Value>,
}

impl Run {
    fn new(working: &Proposal) -> Self {
        Self {
            schema_version: 1,
            snapshot: working.snapshot.clone(),
            templates: json!(working.templates),
            options: json!(working.options),
            decisions: vec![None; working.decisions.len()],
            model: String::new(),
            history: Vec::new(),
        }
    }

    fn same_input(&self, working: &Proposal) -> bool {
        self.schema_version == 1
            && self.templates == json!(working.templates)
            && self.options == json!(working.options)
            && [
                "source",
                "project_id",
                "fps",
                "width",
                "height",
                "origin",
                "track",
                "first",
            ]
            .iter()
            .all(|key| self.snapshot[*key] == working.snapshot[*key])
            && if self.snapshot["source"] == "srt" {
                self.snapshot["timeline"] == working.snapshot["timeline"]
            } else {
                self.snapshot["project_id"]
                    .as_str()
                    .is_some_and(|id| !id.is_empty())
            }
    }

    fn compatible_prefix(&self, working: &Proposal) -> bool {
        self.same_input(working)
            && self.snapshot["cues"].as_array().is_some_and(|saved| {
                !saved.is_empty()
                    && saved.len() == self.decisions.len()
                    && working.snapshot["cues"]
                        .as_array()
                        .is_some_and(|current| current.starts_with(saved))
                    && match (
                        cut_signature(&self.snapshot, saved),
                        cut_signature(&working.snapshot, saved),
                    ) {
                        (Some(a), Some(b)) => a == b,
                        _ => {
                            self.snapshot["timeline_id"] == working.snapshot["timeline_id"]
                                && self.snapshot["cuts"] == working.snapshot["cuts"]
                                && self.snapshot["cut_source_refs"]
                                    == working.snapshot["cut_source_refs"]
                        }
                    }
            })
    }

    fn range(&self, limit: usize) -> Option<Range<usize>> {
        let start = self.decisions.iter().position(Option::is_none)?;
        let count = self.decisions[start..]
            .iter()
            .take(limit)
            .take_while(|d| d.is_none())
            .count();
        Some(start..start + count)
    }

    fn processed(&self) -> usize {
        self.decisions
            .iter()
            .filter(|entry| entry.is_some())
            .count()
    }

    fn model(&self) -> String {
        if !self.model.is_empty() {
            return self.model.clone();
        }
        self.history
            .last()
            .and_then(|entry| {
                Some(format!(
                    "{}/{}",
                    entry["provider"].as_str()?,
                    entry["model"].as_str()?
                ))
            })
            .unwrap_or_else(|| "manual-direct".into())
    }
}

fn cut_signature(snapshot: &Value, cues: &[Value]) -> Option<Vec<String>> {
    let cuts = snapshot["cuts"].as_array()?;
    if cuts.is_empty() {
        return Some(Vec::new());
    }
    let references = snapshot["cut_source_refs"].as_array()?;
    if references.len() != cuts.len() {
        return None;
    }
    let first = cues.first()?["start_frame"].as_f64()?;
    let last = cues.last()?["end_frame"].as_f64()?;
    let mut signature = Vec::new();
    for (cut, reference) in cuts.iter().zip(references) {
        let start = cut[3].as_f64()?;
        let end = cut[4].as_f64()?;
        if start >= last || end <= first {
            continue;
        }
        if reference.as_str().is_none_or(str::is_empty) {
            return None;
        }
        let fields = cut.as_array()?;
        let mut item = vec![cut[0].clone()];
        // Los clips de audio pueden pasar a otra pista en un duplicado del montaje.
        if cut[0] != "audio" {
            item.push(cut[1].clone());
        }
        item.extend_from_slice(&fields[3..]);
        item.push(reference.clone());
        signature.push(Value::Array(item).to_string());
    }
    signature.sort_unstable();
    Some(signature)
}

fn read(path: &Path) -> Result<Option<Run>, String> {
    match File::open(path) {
        Ok(file) => {
            let mut bytes = Vec::new();
            file.take(MAX_FILE + 1)
                .read_to_end(&mut bytes)
                .map_err(|_| "No se pudo leer el avance guardado.")?;
            if bytes.len() as u64 > MAX_FILE {
                return Err("El avance guardado supera 32 MB.".into());
            }
            serde_json::from_slice(&bytes)
                .map(Some)
                .map_err(|_| "El avance guardado no es válido. Se conservó el archivo.".into())
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(error) => Err(format!("No se pudo abrir el avance guardado: {error}")),
    }
}

fn checkpoint(root: &Path, working: &Proposal) -> (Run, String) {
    let mut best: Option<Run> = None;
    for directory in [
        root.join("editorial_runs"),
        root.join("editorial_runs_rust"),
    ] {
        let Ok(paths) = fs::read_dir(directory) else {
            continue;
        };
        for path in paths
            .flatten()
            .map(|item| item.path())
            .filter(|p| p.extension().is_some_and(|e| e == "json"))
        {
            if let Ok(Some(existing)) = read(&path)
                && existing.compatible_prefix(working)
                && best
                    .as_ref()
                    .is_none_or(|current| existing.processed() > current.processed())
            {
                best = Some(existing);
            }
        }
    }
    let mut run = Run::new(working);
    let mut message = String::new();
    if let Some(previous) = best {
        run.model = previous.model();
        for (index, decision) in previous.decisions.into_iter().enumerate() {
            run.decisions[index] = decision;
        }
        message = format!(
            "Se recuperó el avance guardado ({}/{}).",
            run.processed(),
            run.decisions.len()
        );
    }
    (run, message)
}

fn key(run: &Run) -> Result<String, String> {
    // El rango final es informativo. Los subtítulos y tiempos forman parte de la identidad.
    let mut snapshot = run.snapshot.clone();
    if let Some(object) = snapshot.as_object_mut() {
        object.remove("last");
    }
    if run.snapshot["source"] == "resolve"
        && let Some(snapshot) = snapshot.as_object_mut()
    {
        snapshot.remove("project");
        snapshot.remove("timeline");
        if let Some(cuts) = run.snapshot["cues"]
            .as_array()
            .and_then(|cues| cut_signature(&run.snapshot, cues))
        {
            snapshot.remove("timeline_id");
            snapshot.remove("cut_source_refs");
            snapshot.insert("cuts".into(), json!(cuts));
        }
    }
    let data = serde_json::to_vec(
        &json!({"snapshot":snapshot,"templates":run.templates,"options":run.options}),
    )
    .map_err(|_| "No se pudo identificar la revisión del montaje.")?;
    Ok(format!("{:x}", Sha256::digest(&data)))
}

fn reviewed(proposal: &Proposal, visible: Option<&Proposal>, run: &mut Run) {
    let Some(visible) = visible.filter(|existing| {
        existing.snapshot == proposal.snapshot
            && json!(existing.templates) == json!(proposal.templates)
            && json!(existing.options) == json!(proposal.options)
    }) else {
        return;
    };
    for (index, (state, candidate)) in run.decisions.iter_mut().zip(&visible.decisions).enumerate()
    {
        if state.is_some()
            && candidate.reviewed
            && proposal.validate_decision(index, candidate, true).is_ok()
        {
            *state = Some(candidate.clone());
        }
    }
}

pub(super) fn next(
    proposal: &Proposal,
    choice: &str,
    visible: Option<&Proposal>,
) -> Result<BatchProgress, String> {
    proposal.validate(false)?;
    let limit = match choice {
        "all" => usize::MAX,
        "20" | "50" | "100" | "500" => choice.parse().expect("tamaño validado"),
        _ => return Err("Elige una tanda de 20, 50, 100, 500 o todos los subtítulos.".into()),
    };
    let working = planner::corrected_source(proposal)?;
    let root = editorial_config::data_dir();
    let folder = root.join("editorial_runs_rust");
    fs::create_dir_all(&folder).map_err(|error| error.to_string())?;
    let key = key(&Run::new(&working))?;
    let target = folder.join(format!("{key}.json"));
    let lease = OpenOptions::new()
        .create(true)
        .truncate(false)
        .read(true)
        .write(true)
        .open(folder.join(format!("{key}.lock")))
        .map_err(|error| error.to_string())?;
    lease
        .try_lock()
        .map_err(|_| "Otra ventana está generando una tanda para esta secuencia.")?;
    let (mut run, message) = match read(&target)? {
        Some(saved)
            if saved.compatible_prefix(&working)
                && saved.decisions.len() == working.decisions.len() =>
        {
            (
                saved,
                "Se encontró un avance guardado para esta secuencia.".into(),
            )
        }
        Some(_) => {
            return Err("El avance guardado no corresponde a la revisión del montaje.".into());
        }
        None => checkpoint(&root, &working),
    };
    reviewed(proposal, visible, &mut run);
    let range = run.range(limit).unwrap_or(0..0);
    if !range.is_empty() {
        let previous: Vec<_> = run.decisions[..range.start]
            .iter()
            .rev()
            .flatten()
            .take(2)
            .cloned()
            .collect();
        let previous: Vec<_> = previous.into_iter().rev().collect();
        let provider = TextProvider::configured()?;
        let long_context = editorial_config::load_preferences()?
            .get("long_context_enabled")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        let batch =
            planner::generate_batch(&working, range.clone(), &previous, &provider, long_context)?;
        for (slot, decision) in run.decisions[range.clone()].iter_mut().zip(batch) {
            *slot = Some(decision);
        }
        run.model = format!("{}/{}", provider.name(), provider.model());
    }
    let merged = Proposal {
        model: run.model(),
        decisions: proposal
            .decisions
            .iter()
            .zip(&run.decisions)
            .map(|(base, decision)| decision.as_ref().unwrap_or(base).clone())
            .collect(),
        ..proposal.clone()
    };
    merged.validate(false)?;
    let mut pending =
        tempfile::NamedTempFile::new_in(&folder).map_err(|error| error.to_string())?;
    serde_json::to_writer(&mut pending, &run).map_err(|error| error.to_string())?;
    pending.flush().map_err(|error| error.to_string())?;
    if pending
        .as_file()
        .metadata()
        .map_err(|error| error.to_string())?
        .len()
        > MAX_FILE
    {
        return Err("El avance generado supera 32 MB.".into());
    }
    pending
        .persist(&target)
        .map_err(|error| format!("No se pudo guardar la tanda: {}", error.error))?;
    let first = proposal.snapshot["first"]
        .as_u64()
        .and_then(|i| usize::try_from(i).ok())
        .unwrap_or(1);
    Ok(BatchProgress {
        proposal: merged,
        processed: run.processed(),
        total: run.decisions.len(),
        complete: run.range(1).is_none(),
        next_number: run.range(1).map(|r| first + r.start),
        start: range.start,
        end: range.end,
        message,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn next_range_preserves_approved_work_and_skips_filled_gaps() {
        let mut run = Run {
            schema_version: 1,
            snapshot: Value::Null,
            templates: Value::Null,
            options: Value::Null,
            decisions: vec![None; 6],
            model: String::new(),
            history: Vec::new(),
        };
        let saved: Decision = serde_json::from_value(json!({"cue_index":2,"context":"","main":"texto",
            "accent":"","templates":{"main":"title_1"},"reason":"revisión","enabled":true,"reviewed":true})).unwrap();
        run.decisions[2] = Some(saved);
        assert_eq!(run.range(50), Some(0..2));
        let old = run.decisions[2].clone();
        run.decisions[0] = old.clone();
        run.decisions[1] = old;
        assert_eq!(run.range(50), Some(3..6));
        assert!(run.decisions[2].as_ref().unwrap().reviewed);
    }

    #[test]
    fn an_identical_duplicate_can_resume_but_a_changed_cut_cannot() {
        let base = Proposal {
            snapshot: json!({
                "source":"resolve","project_id":"p","timeline_id":"t1","timeline":"Original",
                "fps":24,"width":1920,"height":1080,"origin":0,"track":1,"first":1,"last":1,
                "cues":[{"text":"texto","start_frame":0,"end_frame":24,"track_index":1}],
                "cuts":[["video",1,"id1",0,24,0,0]], "cut_source_refs":["media:same"]
            }),
            templates: vec![], options:None, model:"fixture".into(), version:"1.0.0".into(),
            decisions: vec![serde_json::from_value(json!({"cue_index":0,"context":"","main":"texto",
                "accent":"","templates":{"main":"title_1"},"reason":"revisión","enabled":true,"reviewed":false})).unwrap()],
        };
        let saved = Run::new(&base);
        let mut duplicate = base.clone();
        duplicate.snapshot["timeline_id"] = json!("t2");
        duplicate.snapshot["timeline"] = json!("Duplicado");
        duplicate.snapshot["cuts"][0][2] = json!("id2");
        assert_eq!(key(&saved).unwrap(), key(&Run::new(&duplicate)).unwrap());
        assert!(saved.compatible_prefix(&duplicate));
        duplicate.snapshot["cuts"][0][5] = json!(1);
        assert!(!saved.compatible_prefix(&duplicate));
    }
}
