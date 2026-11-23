//! Alineación por lotes. La IA propone textos, los tiempos pertenecen a la fuente.
use crate::{
    services::{Alignment, Marker},
    text_provider::TextProvider,
};
use regex::{Captures, Regex};
use serde_json::{Value, json};
use std::collections::BTreeMap;

const BATCH_SIZE: usize = 50;
const SYSTEM: &str = "Eres un asistente editorial de postproducción y subtitulado en DaVinci Resolve. \
    Compara los subtítulos transcritos automáticamente con el guion original y corrige errores de \
    transcripción, homofonía, ortografía y jerga. Conserva la intención del original y la forma exacta \
    de las marcas del glosario. Conserva los índices y tiempos de cada subtítulo. Si detect_markers es \
    verdadero, propone marcadores de capítulos (Blue), puntos clave (Yellow), sonido (Green), preguntas \
    (Cyan) y llamadas a la acción (Pink). Responde exclusivamente en el formato JSON solicitado.";

fn glossary(input: &str) -> Vec<(String, String)> {
    let mut words = Vec::new();
    let mut insert = |term: &str, replacement: &str| {
        let (term, replacement) = (term.trim(), replacement.trim());
        if term.is_empty() || replacement.is_empty() {
            return;
        }
        if let Some((_, saved)) = words.iter_mut().find(|(word, _)| word == term) {
            *saved = replacement.to_owned();
        } else {
            words.push((term.to_owned(), replacement.to_owned()));
        }
    };
    if let Ok(pairs) = serde_json::from_str::<BTreeMap<String, String>>(input.trim()) {
        for (term, replacement) in pairs {
            insert(&term, &replacement);
        }
    } else {
        for item in input.split(['\n', ',']) {
            if let Some((term, replacement)) =
                item.split_once(':').or_else(|| item.split_once("->"))
            {
                insert(term, replacement);
            }
        }
    }
    words
}

fn apply_glossary(text: &str, words: &[(Regex, String)]) -> String {
    let mut result = text.to_owned();
    for (pattern, replacement) in words {
        result = pattern
            .replace_all(&result, |matched: &Captures<'_>| {
                let word = matched.get(0).expect("la coincidencia existe");
                let matched_chars = word.as_str().chars().count();
                let suffix_start = replacement
                    .char_indices()
                    .nth(matched_chars)
                    .map_or(replacement.len(), |(pos, _)| pos);
                let (prefix, suffix) = replacement.split_at(suffix_start);
                if prefix.to_lowercase() == word.as_str().to_lowercase()
                    && result[word.end()..].starts_with(suffix)
                {
                    prefix.to_owned()
                } else {
                    replacement.clone()
                }
            })
            .into_owned();
    }
    result
}

fn corrections(
    response: &Value,
    start: usize,
    originals: &[(f64, f64, String)],
    words: &[(Regex, String)],
) -> Result<Vec<String>, String> {
    let items = response["aligned_cues"]
        .as_array()
        .ok_or("La respuesta de IA no contiene subtítulos alineados.")?;
    let mut aligned = BTreeMap::new();
    for item in items {
        let Some(index) = item["index"]
            .as_u64()
            .and_then(|i| usize::try_from(i).ok())
            .or_else(|| item["index"].as_str().and_then(|i| i.trim().parse().ok()))
        else {
            continue;
        };
        if !(start..start + originals.len()).contains(&index) {
            continue;
        }
        if aligned
            .insert(
                index,
                item["corrected_text"].as_str().unwrap_or_default().trim(),
            )
            .is_some()
        {
            return Err("El proveedor devolvió índices de subtítulo duplicados.".into());
        }
    }
    Ok(originals
        .iter()
        .enumerate()
        .map(|(index, (_, _, original))| {
            let text = aligned
                .get(&(start + index))
                .filter(|text| !text.is_empty())
                .copied()
                .unwrap_or(original);
            apply_glossary(text, words)
        })
        .collect())
}

fn marker(value: &Value) -> Option<Marker> {
    let frame = value["frame"]
        .as_f64()
        .or_else(|| value["frame"].as_str()?.parse().ok())?;
    if !frame.is_finite() || frame < 0.0 {
        return None;
    }
    const COLORS: &[&str] = &[
        "Blue", "Cyan", "Green", "Yellow", "Red", "Pink", "Purple", "Fuchsia", "Rose", "Lavender",
        "Sky", "Mint",
    ];
    let color = value["color"].as_str().unwrap_or_default();
    let color = COLORS
        .iter()
        .copied()
        .find(|allowed| allowed.eq_ignore_ascii_case(color))
        .unwrap_or("Cyan");
    Some(Marker {
        frame,
        color: color.into(),
        name: value["name"].as_str().unwrap_or("Punto Clave").into(),
        note: value["note"].as_str().unwrap_or_default().into(),
    })
}

pub(crate) fn align(
    cues: &[(f64, f64, String)],
    script: &str,
    input_glossary: &str,
    detect_markers: bool,
) -> Result<Alignment, String> {
    if cues.is_empty() {
        return Err("No hay subtítulos para procesar con IA.".into());
    }
    if cues
        .iter()
        .any(|(start, end, _)| !start.is_finite() || !end.is_finite() || *end <= *start)
    {
        return Err("La transcripción contiene tiempos de subtítulo inválidos.".into());
    }
    let pairs = glossary(input_glossary);
    let words = pairs
        .iter()
        .map(|(term, replacement)| {
            Regex::new(&format!(r"(?i)\b{}\b", regex::escape(term)))
                .map(|pattern| (pattern, replacement.clone()))
                .map_err(|_| "Un término del glosario es demasiado grande.")
        })
        .collect::<Result<Vec<_>, _>>()?;
    let glossary: BTreeMap<_, _> = pairs.iter().map(|(key, value)| (key, value)).collect();
    let client = TextProvider::configured()?;
    let mut outcome = Alignment::default();
    let batch_count = cues.len().div_ceil(BATCH_SIZE);
    for (batch, entries) in cues.chunks(BATCH_SIZE).enumerate() {
        let start_index = batch * BATCH_SIZE + 1;
        let items: Vec<_> = entries.iter().enumerate().map(|(index, (start, end, text))|
            json!({"index":start_index + index,"start_frame":start,"end_frame":end,"text":text})
        ).collect();
        let payload = json!({
            "task":"align_and_correct_subtitles",
            "detect_markers":detect_markers,
            "original_script": script.trim(),
            "glossary":glossary,
            "subtitles":items,
            "expected_json_structure":{
                "aligned_cues":[{"index":start_index,"corrected_text":"Texto corregido"}],
                "markers":[{"frame":120.0,"color":"Cyan","name":"Punto clave","note":"Contexto"}],
                "summary":"Resumen de las correcciones"
            }
        });
        let prompt = format!("Analiza y corrige estos subtítulos.\n{payload}");
        let response = client.structured(&prompt, SYSTEM, 0.15)?;
        outcome
            .cues
            .extend(corrections(&response, start_index, entries, &words)?);
        if detect_markers && let Some(markers) = response["markers"].as_array() {
            outcome.markers.extend(markers.iter().filter_map(marker));
        }
        if batch_count == 1 {
            outcome.summary = response["summary"].as_str().unwrap_or_default().into();
        }
    }
    outcome.corrections = cues
        .iter()
        .zip(&outcome.cues)
        .filter(|((_, _, original), corrected)| original != *corrected)
        .count();
    if outcome.summary.is_empty() {
        outcome.summary = format!(
            "Alineación completada en {batch_count} lote(s), con {} correcciones y {} marcadores.",
            outcome.corrections,
            outcome.markers.len()
        );
    }
    Ok(outcome)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn keeps_indices_local_to_batch_and_does_not_duplicate_glossary_suffix() {
        let originals = [
            (1.0, 2.0, "davinci".to_owned()),
            (2.0, 3.0, "Segundo".to_owned()),
        ];
        let words = [(
            Regex::new(r"(?i)\bdavinci\b").unwrap(),
            "DaVinci Resolve".into(),
        )];
        let response = json!({"aligned_cues":[
            {"index":1,"corrected_text":"Fuera del lote"},
            {"index":"51","corrected_text":"davinci Resolve"}
        ]});
        assert_eq!(
            corrections(&response, 51, &originals, &words).unwrap(),
            ["DaVinci Resolve", "Segundo"]
        );
        assert!(
            corrections(
                &json!({"aligned_cues":[{"index":51},{"index":51}]}),
                51,
                &originals,
                &words
            )
            .is_err()
        );
        assert!(marker(&json!({"frame":"NaN"})).is_none());
    }
}
