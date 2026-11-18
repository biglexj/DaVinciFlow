//! Propuestas y revisión editorial nativas, compatibles con el contrato Python 1.1.
use crate::{services::TemplateInfo, subtitles::Document};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{collections::BTreeMap, io::Read, path::Path};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Decision {
    pub cue_index: usize,
    pub context: String,
    pub main: String,
    pub accent: String,
    pub templates: BTreeMap<String, String>,
    pub reason: String,
    pub enabled: bool,
    pub reviewed: bool,
    #[serde(default)]
    pub edit_note: String,
    #[serde(default)]
    pub visual_note: String,
    #[serde(default)]
    pub resource_id: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Options {
    pub mode: String,
    pub format: String,
    pub density: String,
    pub direction: String,
    #[serde(default)]
    pub resources: Vec<Value>,
    pub track_mode: String,
}
impl Default for Options {
    fn default() -> Self {
        Self {
            mode: "captions".into(),
            format: "auto".into(),
            density: "balanced".into(),
            direction: String::new(),
            resources: vec![],
            track_mode: "triple".into(),
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Proposal {
    pub snapshot: Value,
    pub templates: Vec<TemplateInfo>,
    pub decisions: Vec<Decision>,
    pub model: String,
    pub version: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub options: Option<Options>,
}

impl Proposal {
    pub fn from_value(value: Value) -> Result<Self, String> {
        let proposal: Self = serde_json::from_value(value)
            .map_err(|e| format!("La propuesta no corresponde al contrato editorial: {e}"))?;
        proposal.validate(false)?;
        Ok(proposal)
    }
    pub fn load(path: &Path) -> Result<Self, String> {
        let file =
            std::fs::File::open(path).map_err(|e| format!("No se pudo abrir la propuesta: {e}"))?;
        let mut bytes = Vec::new();
        file.take(32 * 1024 * 1024 + 1)
            .read_to_end(&mut bytes)
            .map_err(|e| format!("No se pudo leer la propuesta: {e}"))?;
        if bytes.len() > 32 * 1024 * 1024 {
            return Err("La propuesta supera el límite de 32 MB.".into());
        }
        Self::from_value(
            serde_json::from_slice(&bytes).map_err(|e| format!("JSON editorial inválido: {e}"))?,
        )
    }
    pub fn save_new(&self, path: &Path) -> Result<(), String> {
        self.validate(false)?;
        let content = serde_json::to_string_pretty(self).map_err(|e| e.to_string())?;
        crate::subtitles::save_new(path, &content)
    }
    pub fn direct(
        document: &Document,
        capture: Option<&Value>,
        templates: Vec<TemplateInfo>,
        fps: f64,
        options: Options,
    ) -> Result<Self, String> {
        if document.cues.is_empty() {
            return Err("Carga una transcripción antes de preparar la propuesta.".into());
        }
        if !fps.is_finite() || fps <= 0. {
            return Err("Los FPS deben ser positivos.".into());
        }
        let Some(template) = templates
            .iter()
            .find(|t| t.name.to_lowercase().contains("principal"))
            .or(templates.first())
        else {
            return Err("Elige al menos una plantilla real del catálogo.".into());
        };
        let template_id = template.id.clone();
        let snapshot = if let Some(capture) = capture {
            if capture.get("cues").and_then(Value::as_array).map(Vec::len)
                != Some(document.cues.len())
            {
                return Err("La transcripción corregida no coincide con la captura. Vuelve a leer la fuente.".into());
            }
            capture.clone()
        } else {
            json!({"project":"SRT offline","timeline":document.source,"timeline_id":null,
                "fps":fps,"width":1920,"height":1080,"origin":0,"track":1,"cuts":[],"source":"srt",
                "first":1,"last":document.cues.len(),"project_id":"","cut_source_refs":[],
                "cues":document.cues.iter().map(|c|json!({"text":c.original,"start_frame":(c.start_ms as f64*fps/1000.*100.).round()/100.,
                    "end_frame":(c.end_ms as f64*fps/1000.*100.).round()/100.,"track_index":1})).collect::<Vec<_>>()})
        };
        let notes = document
            .cues
            .iter()
            .enumerate()
            .map(|(i, c)| {
                if snapshot["cues"][i]["text"].as_str() != Some(c.text.as_str()) {
                    "Corrección de la transcripción guardada en la sesión nativa.".to_owned()
                } else {
                    String::new()
                }
            })
            .collect::<Vec<_>>();
        let proposal = Self {
            snapshot,
            templates,
            decisions: document
                .cues
                .iter()
                .enumerate()
                .map(|(i, c)| Decision {
                    cue_index: i,
                    context: String::new(),
                    main: c.text.clone(),
                    accent: String::new(),
                    templates: BTreeMap::from([("main".into(), template_id.clone())]),
                    reason: "Subtítulo original para revisión directa.".into(),
                    enabled: true,
                    reviewed: false,
                    edit_note: notes[i].clone(),
                    visual_note: String::new(),
                    resource_id: String::new(),
                })
                .collect(),
            model: "manual-direct".into(),
            version: "1.1.0".into(),
            options: Some(options),
        };
        proposal.validate(false)?;
        Ok(proposal)
    }
    pub fn reviewed(&self) -> usize {
        self.decisions.iter().filter(|d| d.reviewed).count()
    }
    pub fn validate(&self, require_review: bool) -> Result<(), String> {
        if !matches!(self.version.as_str(), "1.0.0" | "1.1.0") || self.model.trim().is_empty() {
            return Err("Versión o modelo editorial inválidos.".into());
        }
        if self.version == "1.1.0" && self.options.is_none() {
            return Err("Faltan las opciones editoriales.".into());
        }
        if self.version == "1.0.0" && self.options.is_some() {
            return Err("Las opciones requieren el contrato 1.1.0.".into());
        }
        if let Some(o) = &self.options {
            if !matches!(o.mode.as_str(), "captions" | "highlights")
                || !matches!(o.format.as_str(), "auto" | "horizontal" | "vertical")
                || !matches!(o.density.as_str(), "sparse" | "balanced" | "dense")
                || !matches!(o.track_mode.as_str(), "single" | "dual" | "triple")
                || o.direction.chars().count() > 4000
                || o.resources.len() > 80
            {
                return Err("Opciones editoriales inválidas.".into());
            }
            let mut resources = std::collections::BTreeSet::new();
            for resource in &o.resources {
                let Some(object) = resource.as_object() else {
                    return Err("Recurso editorial inválido.".into());
                };
                if object.len() != 3
                    || ["id", "name", "category"].iter().any(|key| {
                        !object
                            .get(*key)
                            .and_then(Value::as_str)
                            .is_some_and(|s| !s.is_empty() && s.chars().count() <= 250)
                    })
                    || !resources.insert(resource["id"].as_str().unwrap_or_default())
                {
                    return Err("Los recursos editoriales son inválidos o están duplicados.".into());
                }
            }
        }
        if !matches!(self.snapshot["source"].as_str(), Some("resolve" | "srt"))
            || ["width", "height", "track"]
                .iter()
                .any(|key| self.snapshot[*key].as_u64().is_none_or(|v| v == 0))
        {
            return Err("La resolución, pista o fuente editorial es inválida.".into());
        }
        let cues = self
            .snapshot
            .get("cues")
            .and_then(Value::as_array)
            .ok_or("Falta la transcripción de origen.")?;
        if cues.is_empty() || cues.len() != self.decisions.len() {
            return Err("La propuesta debe cubrir cada subtítulo exactamente una vez.".into());
        }
        let fps = self
            .snapshot
            .get("fps")
            .and_then(Value::as_f64)
            .ok_or("Faltan los FPS de origen.")?;
        if !fps.is_finite() || fps <= 0. {
            return Err("Los FPS de origen son inválidos.".into());
        }
        let mut previous_end = -1.;
        for cue in cues {
            let start = cue
                .get("start_frame")
                .and_then(Value::as_f64)
                .ok_or("Tiempo inicial inválido.")?;
            let end = cue
                .get("end_frame")
                .and_then(Value::as_f64)
                .ok_or("Tiempo final inválido.")?;
            if !start.is_finite()
                || !end.is_finite()
                || start < 0.
                || start < previous_end
                || end <= start
            {
                return Err(
                    "La transcripción contiene tiempos desordenados, solapados o sin duración."
                        .into(),
                );
            }
            previous_end = end;
        }
        let mut ids = std::collections::BTreeSet::new();
        for t in &self.templates {
            if t.id.is_empty()
                || t.id.len() > 128
                || !t
                    .id
                    .bytes()
                    .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'_' | b'-'))
                || t.name.trim().is_empty()
                || t.locator.trim().is_empty()
                || !ids.insert(&t.id)
                || !matches!(
                    t.source.as_str(),
                    "installed_file"
                        | "installed_archive"
                        | "installed_bin"
                        | "media_pool"
                        | "native"
                )
            {
                return Err("El catálogo tiene plantillas inválidas o duplicadas.".into());
            }
        }
        if ids.is_empty() {
            return Err("El catálogo de la propuesta está vacío.".into());
        }
        for (index, decision) in self.decisions.iter().enumerate() {
            self.validate_decision(index, decision, require_review)?;
        }
        Ok(())
    }
    fn validate_decision(
        &self,
        index: usize,
        d: &Decision,
        require_review: bool,
    ) -> Result<(), String> {
        if d.cue_index != index {
            return Err("Los índices editoriales están duplicados o fuera de orden.".into());
        }
        let selective = self
            .options
            .as_ref()
            .is_some_and(|o| o.mode == "highlights");
        if d.main.trim().is_empty() && (d.enabled || !selective) {
            return Err(format!("Bloque {}: falta el texto principal.", index + 1));
        }
        let original = self.snapshot["cues"][index]["text"]
            .as_str()
            .ok_or("Texto de origen inválido.")?;
        let text = format!("{} {} {}", d.context, d.main, d.accent)
            .split_whitespace()
            .collect::<Vec<_>>()
            .join(" ");
        let covered = if selective {
            (!d.enabled && text.is_empty()) || grounded(original, &text)
        } else {
            text == original.split_whitespace().collect::<Vec<_>>().join(" ")
        };
        if !covered && d.edit_note.trim().is_empty() {
            return Err(format!(
                "Bloque {}: registra el motivo de la edición manual del texto.",
                index + 1
            ));
        }
        for (layer, text) in [
            ("context", &d.context),
            ("main", &d.main),
            ("accent", &d.accent),
        ] {
            if text.trim().is_empty() {
                if d.templates.contains_key(layer) {
                    return Err("Una capa vacía no debe tener plantilla.".into());
                }
            } else if !d
                .templates
                .get(layer)
                .is_some_and(|id| self.templates.iter().any(|t| &t.id == id))
            {
                return Err(format!(
                    "Bloque {}: falta una plantilla válida para {layer}.",
                    index + 1
                ));
            }
        }
        if d.templates
            .keys()
            .any(|layer| !matches!(layer.as_str(), "context" | "main" | "accent"))
        {
            return Err("Capa editorial desconocida.".into());
        }
        if self.options.is_some() && d.reason.trim().is_empty() {
            return Err("Falta el motivo editorial del bloque.".into());
        }
        if require_review && !d.reviewed {
            return Err(format!("Revisa el bloque {} antes de aplicar.", index + 1));
        }
        Ok(())
    }
    pub fn review(&mut self, index: usize, mut decision: Decision) -> Result<(), String> {
        if index >= self.decisions.len() {
            return Err("Bloque editorial inexistente.".into());
        }
        decision.cue_index = index;
        decision.reviewed = true;
        self.validate_decision(index, &decision, false)?;
        self.decisions[index] = decision;
        Ok(())
    }
    pub fn approve_all(&mut self) -> Result<(), String> {
        self.validate(false)?;
        for decision in &mut self.decisions {
            decision.reviewed = true;
        }
        Ok(())
    }
}

fn grounded(original: &str, selected: &str) -> bool {
    use std::sync::LazyLock;
    static WORDS: LazyLock<regex::Regex> = LazyLock::new(|| regex::Regex::new(r"\w+").unwrap());
    let original = original.to_lowercase();
    let selected = selected.to_lowercase();
    let source: Vec<_> = WORDS.find_iter(&original).map(|m| m.as_str()).collect();
    let output: Vec<_> = WORDS.find_iter(&selected).map(|m| m.as_str()).collect();
    let mut remaining = source.iter();
    !output.is_empty()
        && output
            .iter()
            .all(|word| remaining.any(|candidate| candidate == word))
        && ["no", "nunca", "jamás", "sin", "tampoco", "ni"]
            .iter()
            .all(|neg| {
                output.iter().filter(|w| *w == neg).count()
                    >= source.iter().filter(|w| *w == neg).count()
            })
}

pub fn generate(proposal: &Proposal) -> Result<Proposal, String> {
    proposal.validate(false)?;
    let result =
        crate::bridge::invoke_json("editorial.py", "generate", json!({"proposal":proposal}))?;
    Proposal::from_value(result)
}
pub fn apply(proposal: &Proposal) -> Result<Value, String> {
    proposal.validate(true)?;
    crate::bridge::invoke_json("editorial.py", "apply", json!({"proposal":proposal}))
}
pub fn undo() -> Result<Value, String> {
    crate::bridge::invoke_json("editorial.py", "undo", json!({}))
}

/// Vincula la propuesta a los textos y tiempos efectivamente revisados en la sesión.
pub fn document_revision(document: &Document) -> Vec<(u64, u64, String)> {
    document
        .cues
        .iter()
        .map(|cue| (cue.start_ms, cue.end_ms, cue.text.clone()))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    fn proposal() -> Proposal {
        let document = crate::subtitles::parse(
            "1\n00:00:01,000 --> 00:00:02,000\nNo quiero perder esta idea.",
            "prueba.srt".into(),
        )
        .unwrap();
        Proposal::direct(
            &document,
            None,
            vec![TemplateInfo {
                id: "main".into(),
                name: "Principal".into(),
                source: "native".into(),
                locator: "Text+".into(),
                text_input: "StyledText".into(),
                ..Default::default()
            }],
            24.,
            Options::default(),
        )
        .unwrap()
    }
    #[test]
    fn manual_proposal_requires_review_and_roundtrips_the_existing_schema() {
        let mut p = proposal();
        assert!(p.validate(true).is_err());
        p.approve_all().unwrap();
        p.validate(true).unwrap();
        let q = Proposal::from_value(serde_json::to_value(&p).unwrap()).unwrap();
        assert_eq!(q.snapshot, p.snapshot);
        assert_eq!(q.reviewed(), 1);
    }
    #[test]
    fn edits_are_transactional_and_require_an_audit_note_when_changing_text() {
        let mut p = proposal();
        let mut d = p.decisions[0].clone();
        d.main = "Otra idea".into();
        assert!(p.review(0, d.clone()).is_err());
        assert!(!p.decisions[0].reviewed);
        d.edit_note = "Corrección manual".into();
        p.review(0, d).unwrap();
        assert_eq!(p.reviewed(), 1);
    }
    #[test]
    fn highlights_never_drop_negation_without_explicit_manual_edit() {
        let mut p = proposal();
        p.options.as_mut().unwrap().mode = "highlights".into();
        p.decisions[0].main = "quiero perder esta idea".into();
        assert!(p.validate(false).is_err());
        p.decisions[0].main = "No quiero perder esta idea".into();
        p.validate(false).unwrap();
    }
    #[test]
    fn duplicate_templates_missing_layers_and_invalid_timing_are_rejected() {
        let mut p = proposal();
        p.templates.push(p.templates[0].clone());
        assert!(p.validate(false).is_err());
        p.templates.pop();
        p.decisions[0].templates.clear();
        assert!(p.validate(false).is_err());
        let mut p = proposal();
        p.snapshot["cues"][0]["end_frame"] = json!(0);
        assert!(p.validate(false).is_err());
    }
    #[test]
    fn corrected_text_keeps_the_original_resolve_capture_and_is_audited() {
        let mut p = proposal();
        p.snapshot["source"] = json!("resolve");
        let mut document = crate::subtitles::parse(
            "1\n00:00:01,000 --> 00:00:02,000\nNo quiero perder esta idea.",
            "fuente".into(),
        )
        .unwrap();
        let before = document_revision(&document);
        document.cues[0].text = "No quiero olvidar esta idea.".into();
        let reviewed = Proposal::direct(
            &document,
            Some(&p.snapshot),
            p.templates.clone(),
            24.,
            Options::default(),
        )
        .unwrap();
        assert_eq!(reviewed.snapshot, p.snapshot);
        assert_eq!(reviewed.decisions[0].main, document.cues[0].text);
        assert!(!reviewed.decisions[0].edit_note.is_empty());
        assert_ne!(before, document_revision(&document));
        assert!(reviewed.validate(true).is_err());
    }
    #[test]
    fn proposal_export_roundtrips_and_never_overwrites_a_saved_review() {
        let p = proposal();
        let stamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path =
            std::env::temp_dir().join(format!("flow-review-{}-{stamp}.json", std::process::id()));
        p.save_new(&path).unwrap();
        let original = std::fs::read(&path).unwrap();
        assert!(p.save_new(&path).is_err());
        assert_eq!(std::fs::read(&path).unwrap(), original);
        let loaded = Proposal::load(&path).unwrap();
        assert_eq!(loaded.snapshot, p.snapshot);
        assert_eq!(loaded.decisions[0].main, p.decisions[0].main);
        assert!(!loaded.decisions[0].reviewed);
        std::fs::remove_file(path).unwrap();
    }
    #[test]
    #[ignore = "Requiere el entorno Python del proyecto; no llama a IA ni escribe en Resolve"]
    fn native_proposals_are_accepted_by_the_existing_python_contract() {
        let mut p = proposal();
        let result = crate::bridge::invoke_json(
            "editorial.py",
            "validate",
            json!({"proposal":p,"require_review":false}),
        )
        .unwrap();
        assert_eq!(result["valid"], true);
        assert!(
            crate::bridge::invoke_json(
                "editorial.py",
                "validate",
                json!({"proposal":p,"require_review":true})
            )
            .is_err()
        );
        p.approve_all().unwrap();
        crate::bridge::invoke_json(
            "editorial.py",
            "validate",
            json!({"proposal":p,"require_review":true}),
        )
        .unwrap();
    }
}
