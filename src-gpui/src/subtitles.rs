//! Dominio nativo: tiempos en milisegundos para no redondear SRT según los FPS.
use regex::Regex;
use serde::Deserialize;
use std::{path::Path, sync::LazyLock};
use unicode_general_category::{GeneralCategory, get_general_category};
use unicode_normalization::UnicodeNormalization;

/// Exporta una copia nueva: nunca reemplaza la fuente ni un archivo existente.
pub fn save_new(path: &Path, content: &str) -> Result<(), String> {
    use std::io::Write;
    let mut file = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .map_err(|e| {
            if e.kind() == std::io::ErrorKind::AlreadyExists {
                "El archivo ya existe. Elige otro nombre para conservar el original.".to_string()
            } else {
                format!("No se pudo crear el SRT: {e}")
            }
        })?;
    let result = file
        .write_all(content.as_bytes())
        .and_then(|_| file.sync_all());
    drop(file);
    if let Err(e) = result {
        let _ = std::fs::remove_file(path);
        return Err(format!("No se pudo completar la exportación: {e}"));
    }
    Ok(())
}

static TIMING: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
    r"^(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*$"
).unwrap()
});
static TAGS: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"<[^>]+>").unwrap());
static BLOCKS: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\n[\t ]*\n").unwrap());
static BEFORE_CLOSE: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\s+([,.:;?!»\)])").unwrap());
static AFTER_OPEN: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"([¿¡«\(])\s+").unwrap());

#[derive(Clone, Debug, PartialEq)]
pub struct Cue {
    pub start_ms: u64,
    pub end_ms: u64,
    pub original: String,
    pub text: String,
}

impl Cue {
    pub fn changed(&self) -> bool {
        self.text != self.original
    }
}

#[derive(Clone, Debug, Default)]
pub struct Document {
    pub source: String,
    pub cues: Vec<Cue>,
    pub warnings: Vec<String>,
}

impl Document {
    pub fn changed(&self) -> usize {
        self.cues.iter().filter(|c| c.changed()).count()
    }

    // Mutaciones por lote transaccionales: un error nunca deja una edición parcial.
    pub fn normalize(&mut self) -> Result<usize, String> {
        let texts = self
            .cues
            .iter()
            .map(|c| normalize(&c.text))
            .collect::<Result<Vec<_>, _>>()?;
        Ok(self.set_texts(texts))
    }

    pub fn replace(
        &mut self,
        find: &str,
        replacement: &str,
        case_sensitive: bool,
    ) -> Result<usize, String> {
        if find.is_empty() {
            return Err("Escribe el texto que quieres buscar.".into());
        }
        let pattern = regex::RegexBuilder::new(&regex::escape(find))
            .case_insensitive(!case_sensitive)
            .build()
            .map_err(|e| e.to_string())?;
        let texts = self
            .cues
            .iter()
            .map(|cue| {
                let value = pattern
                    .replace_all(&cue.text, regex::NoExpand(replacement))
                    .into_owned();
                if value.trim().is_empty() {
                    Err("El reemplazo dejaría un subtítulo vacío.".into())
                } else {
                    Ok(value)
                }
            })
            .collect::<Result<Vec<_>, String>>()?;
        Ok(self.set_texts(texts))
    }

    fn set_texts(&mut self, texts: Vec<String>) -> usize {
        let mut count = 0;
        for (cue, text) in self.cues.iter_mut().zip(texts) {
            if cue.text != text {
                cue.text = text;
                count += 1;
            }
        }
        count
    }

    pub fn export(&self) -> String {
        self.cues
            .iter()
            .enumerate()
            .map(|(i, c)| {
                format!(
                    "{}\n{} --> {}\n{}\n",
                    i + 1,
                    timecode(c.start_ms),
                    timecode(c.end_ms),
                    c.text.trim()
                )
            })
            .collect::<Vec<_>>()
            .join("\n")
    }
}

pub fn normalize(text: &str) -> Result<String, String> {
    let cleaned: String = text
        .nfc()
        .filter(|ch| {
            !matches!(
                get_general_category(*ch),
                GeneralCategory::Control
                    | GeneralCategory::Format
                    | GeneralCategory::Surrogate
                    | GeneralCategory::PrivateUse
                    | GeneralCategory::Unassigned
            ) || matches!(ch, '\n' | '\r' | '\t')
        })
        .collect();
    let collapsed = cleaned.split_whitespace().collect::<Vec<_>>().join(" ");
    if collapsed.is_empty() {
        return Err("El subtítulo quedó vacío tras la normalización.".into());
    }
    let closed = BEFORE_CLOSE.replace_all(&collapsed, "$1");
    Ok(AFTER_OPEN.replace_all(&closed, "$1").into_owned())
}

pub fn timecode(ms: u64) -> String {
    format!(
        "{:02}:{:02}:{:02},{:03}",
        ms / 3_600_000,
        ms / 60_000 % 60,
        ms / 1000 % 60,
        ms % 1000
    )
}

pub fn load(path: &Path) -> Result<Document, String> {
    if !path
        .extension()
        .is_some_and(|s| s.eq_ignore_ascii_case("srt"))
    {
        return Err("Selecciona un archivo .srt.".into());
    }
    let metadata = path
        .metadata()
        .map_err(|e| format!("No se pudo leer el SRT: {e}"))?;
    if metadata.len() > 20 * 1024 * 1024 {
        return Err("El SRT supera el límite de 20 MB.".into());
    }
    let bytes = std::fs::read(path).map_err(|e| format!("No se pudo leer el SRT: {e}"))?;
    let (text, legacy) = match String::from_utf8(bytes.clone()) {
        Ok(s) => (s, false),
        Err(_) => (bytes.iter().map(|b| char::from(*b)).collect(), true),
    };
    let mut doc = parse(&text, path.display().to_string())?;
    if legacy {
        doc.warnings
            .push("El archivo se ha leído como Latin-1; la exportación será UTF-8.".into());
    }
    Ok(doc)
}

pub fn parse(text: &str, source: String) -> Result<Document, String> {
    let normalized = text
        .trim_start_matches('\u{feff}')
        .replace("\r\n", "\n")
        .replace('\r', "\n");
    let mut doc = Document {
        source,
        ..Default::default()
    };
    for (index, block) in BLOCKS.split(normalized.trim()).enumerate() {
        if block.trim().is_empty() {
            continue;
        }
        let lines: Vec<_> = block
            .lines()
            .map(str::trim)
            .filter(|s| !s.is_empty())
            .collect();
        let time_index = usize::from(
            lines
                .first()
                .is_some_and(|s| s.chars().all(|c| c.is_ascii_digit())),
        );
        let captures = lines
            .get(time_index)
            .and_then(|line| TIMING.captures(line))
            .ok_or_else(|| {
                format!(
                    "Bloque {}: código de tiempo inválido. No se ha cargado el archivo.",
                    index + 1
                )
            })?;
        let read_time = |offset: usize| -> Result<u64, String> {
            let number = |i: usize| {
                captures[i]
                    .parse::<u64>()
                    .map_err(|_| "Tiempo SRT inválido.".to_string())
            };
            let (h, m, s) = (number(offset)?, number(offset + 1)?, number(offset + 2)?);
            if m >= 60 || s >= 60 {
                return Err(format!(
                    "Bloque {}: minutos o segundos fuera de rango.",
                    index + 1
                ));
            }
            let decimal = &captures[offset + 3];
            let ms = decimal.parse::<u64>().map_err(|e| e.to_string())?
                * 10_u64.pow(3 - decimal.len() as u32);
            Ok((h * 3600 + m * 60 + s) * 1000 + ms)
        };
        let (start_ms, end_ms) = (read_time(1)?, read_time(5)?);
        if end_ms <= start_ms {
            return Err(format!(
                "Bloque {}: la duración debe ser positiva.",
                index + 1
            ));
        }
        let raw = lines.get(time_index + 1..).unwrap_or_default().join(" ");
        let text = TAGS.replace_all(&raw, "").trim().to_string();
        if text.is_empty() {
            return Err(format!("Bloque {}: el texto está vacío.", index + 1));
        }
        doc.cues.push(Cue {
            start_ms,
            end_ms,
            original: text.clone(),
            text,
        });
    }
    if doc.cues.is_empty() {
        return Err("El archivo no contiene subtítulos válidos.".into());
    }
    doc.cues.sort_by_key(|c| (c.start_ms, c.end_ms));
    if doc.cues.windows(2).any(|w| w[1].start_ms < w[0].end_ms) {
        doc.warnings
            .push("Hay subtítulos solapados. Sus tiempos se han conservado.".into());
    }
    Ok(doc)
}

#[derive(Deserialize)]
pub struct ResolveSnapshot {
    pub project: String,
    pub timeline: String,
    pub fps: f64,
    pub origin: f64,
    pub cues: Vec<ResolveCue>,
}

#[derive(Deserialize)]
pub struct ResolveCue {
    pub text: String,
    pub start_frame: f64,
    pub end_frame: f64,
}

impl TryFrom<ResolveSnapshot> for Document {
    type Error = String;
    fn try_from(value: ResolveSnapshot) -> Result<Self, String> {
        if !value.fps.is_finite() || value.fps <= 0. || !value.origin.is_finite() {
            return Err("Resolve devolvió FPS u origen inválidos.".into());
        }
        let mut doc = Document {
            source: format!("{} / {} · {} fps", value.project, value.timeline, value.fps),
            ..Default::default()
        };
        for cue in value.cues {
            if !cue.start_frame.is_finite()
                || !cue.end_frame.is_finite()
                || cue.start_frame < value.origin
                || cue.end_frame <= cue.start_frame
                || cue.text.trim().is_empty()
            {
                return Err("Resolve devolvió un subtítulo inválido.".into());
            }
            doc.cues.push(Cue {
                start_ms: ((cue.start_frame - value.origin) / value.fps * 1000.).round() as u64,
                end_ms: ((cue.end_frame - value.origin) / value.fps * 1000.).round() as u64,
                original: cue.text.clone(),
                text: cue.text,
            });
        }
        if doc.cues.is_empty() {
            return Err("La pista 1 no contiene subtítulos.".into());
        }
        Ok(doc)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn resolve_origin_is_removed_without_changing_relative_duration() {
        let doc = Document::try_from(ResolveSnapshot {
            project: "test".into(),
            timeline: "test".into(),
            fps: 24.,
            origin: 86400.,
            cues: vec![ResolveCue {
                text: "Ely".into(),
                start_frame: 86424.,
                end_frame: 86472.,
            }],
        })
        .unwrap();
        assert_eq!(doc.cues[0].start_ms, 1000);
        assert_eq!(doc.cues[0].end_ms, 3000);
        assert_eq!(timecode(60000), "00:01:00,000");
        assert_eq!(timecode(3599999), "00:59:59,999");
    }
    #[test]
    fn export_writes_utf8_and_never_overwrites_an_existing_file() {
        let path = std::env::temp_dir().join(format!("df-gpui-export-{}.srt", std::process::id()));
        let content = "1\n00:00:01,000 --> 00:00:02,000\n¡Qué tal, Ely!\n";
        save_new(&path, content).unwrap();
        assert!(save_new(&path, "overwrite").is_err());
        assert_eq!(std::fs::read_to_string(&path).unwrap(), content);
        assert_eq!(load(&path).unwrap().cues[0].text, "¡Qué tal, Ely!");
        std::fs::remove_file(path).unwrap();
    }
    #[test]
    fn normalization_failure_preserves_every_cue() {
        let mut doc = Document {
            cues: vec![
                Cue {
                    start_ms: 0,
                    end_ms: 1,
                    original: " ¿ Hola ? ".into(),
                    text: " ¿ Hola ? ".into(),
                },
                Cue {
                    start_ms: 2,
                    end_ms: 3,
                    original: "\u{200b}".into(),
                    text: "\u{200b}".into(),
                },
            ],
            ..Default::default()
        };
        let before = doc.cues.clone();
        assert!(doc.normalize().is_err());
        assert_eq!(doc.cues, before);
    }
    #[test]
    fn srt_bom_crlf_tags_and_milliseconds_roundtrip() {
        let doc = parse(
            "\u{feff}1\r\n00:00:01,001 --> 00:00:02.009\r\n<i>¿Qué tal?</i>\r\nEly\r\n",
            "test".into(),
        )
        .unwrap();
        assert_eq!(doc.cues[0].text, "¿Qué tal? Ely");
        assert_eq!(doc.cues[0].start_ms, 1001);
        assert_eq!(parse(&doc.export(), "again".into()).unwrap().cues, doc.cues);
    }
    #[test]
    fn invalid_block_is_never_silently_discarded() {
        assert!(
            parse(
                "1\n00:00:00,000 --> 00:00:01,000\nHola\n\n2\nincorrecto\nAdiós",
                "test".into()
            )
            .is_err()
        );
        assert!(parse("1\n00:61:00,000 --> 00:62:00,000\nHola", "test".into()).is_err());
        assert!(parse("1\n00:00:02,000 --> 00:00:01,000\nHola", "test".into()).is_err());
    }
    #[test]
    fn spanish_unicode_matches_existing_normalization_contract() {
        assert_eq!(
            normalize("  ¿  Que\u{301}   tal ,\nEly ?\u{200b}  ").unwrap(),
            "¿Qué tal, Ely?"
        );
        assert!(normalize("\u{200b}\u{e000}").is_err());
        assert_eq!(normalize("¡ Hola !  12,5 %").unwrap(), "¡Hola! 12,5 %");
    }
    #[test]
    fn replacements_are_literal_and_transactional() {
        let mut doc = parse(
            "1\n00:00:00,000 --> 00:00:01,000\nEly\n\n2\n00:00:02,000 --> 00:00:03,000\nELY",
            "t".into(),
        )
        .unwrap();
        assert!(doc.replace("Ely", "", false).is_err());
        assert_eq!(doc.changed(), 0);
        assert_eq!(doc.replace("ely", "$1", false).unwrap(), 2);
        assert_eq!(doc.cues[0].text, "$1");
        assert_eq!(doc.cues[0].start_ms, 0);
    }
}
