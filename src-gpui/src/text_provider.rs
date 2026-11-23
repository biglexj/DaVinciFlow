//! Clientes de texto nativos de Gemini y MiniMax.
use crate::{editorial_config, native_http};
use reqwest::Url;
use reqwest::blocking::Client;
use serde_json::{Value, json};
use std::{collections::BTreeSet, time::Duration};

const GEMINI: &str = "https://generativelanguage.googleapis.com/v1beta/models";
const MINIMAX: &str = "https://api.minimax.io/v1/text/chatcompletion_v2";

pub(crate) fn scan_models() -> Result<Vec<String>, String> {
    let key = editorial_config::api_key("gemini")?
        .ok_or("Configura la clave API de Gemini para consultar sus modelos.")?;
    let client = native_http::client(Duration::from_secs(8))?;
    let mut models = BTreeSet::new();
    let mut seen = BTreeSet::new();
    let mut page = String::new();
    loop {
        let mut request = client.get(GEMINI).header("x-goog-api-key", &key);
        if !page.is_empty() {
            request = request.query(&[("pageToken", &page)]);
        }
        let value: Value =
            native_http::json(native_http::response(request.send(), "Gemini")?, "Gemini")?;
        let entries = value["models"]
            .as_array()
            .ok_or("Gemini no devolvió su catálogo de modelos.")?;
        models.extend(entries.iter().filter_map(model_name));
        let token = value["nextPageToken"].as_str().unwrap_or_default();
        if token.is_empty() || seen.len() == 20 || !seen.insert(token.to_owned()) {
            break;
        }
        page = token.into();
    }
    let mut result: Vec<_> = models.into_iter().collect();
    result.sort_by_key(|model| {
        (
            if model.contains("3.5-flash-lite") {
                0
            } else if model.contains("3.5-flash") {
                1
            } else if model.contains("3.7-flash") {
                2
            } else if model.contains("3.8-flash") {
                3
            } else if model.contains("flash") {
                4
            } else {
                5
            },
            model.clone(),
        )
    });
    Ok(result)
}

fn model_name(value: &Value) -> Option<String> {
    let name = value["name"].as_str()?.strip_prefix("models/")?;
    let low = name.to_ascii_lowercase();
    let valid = (low.starts_with("gemini-3") || low.starts_with("gemini-4"))
        && value["supportedGenerationMethods"]
            .as_array()?
            .iter()
            .any(|v| v == "generateContent")
        && ![
            "embedding",
            "aqa",
            "imagen",
            "whisper",
            "image",
            "tts",
            "preview",
            "audio",
            "custom",
            "experimental",
            "live",
        ]
        .iter()
        .any(|part| low.contains(part));
    valid.then(|| name.to_owned())
}

pub(crate) fn assistant(prompt: &str) -> Result<String, String> {
    let prompt = prompt.trim();
    if prompt.is_empty() {
        return Err("Escribe una consulta para el asistente.".into());
    }
    TextProvider::configured()?.generate(prompt, "", 0.4, false)
}

pub(crate) struct TextProvider {
    client: Client,
    provider: String,
    model: String,
    key: String,
}

impl TextProvider {
    pub(crate) fn configured() -> Result<Self, String> {
        let settings = editorial_config::settings(None)?;
        let key = editorial_config::api_key(&settings.provider)?
            .ok_or("Configura la clave API del proveedor en Ajustes.")?;
        Ok(Self {
            client: native_http::client(Duration::from_secs(60))?,
            provider: settings.provider,
            model: settings.model,
            key,
        })
    }

    pub(crate) fn model(&self) -> &str {
        &self.model
    }

    pub(crate) fn name(&self) -> &str {
        &self.provider
    }

    pub(crate) fn has_known_long_context(&self) -> bool {
        matches!(
            self.model.to_ascii_lowercase().as_str(),
            "minimax-m3" | "minimax-m3.1-flash" | "gemini-3.5-flash" | "gemini-3.5-flash-lite"
        )
    }

    pub(crate) fn structured(
        &self,
        prompt: &str,
        system: &str,
        temperature: f64,
    ) -> Result<Value, String> {
        let text = self.generate(prompt, system, temperature, true)?;
        serde_json::from_str(&text)
            .or_else(|original| {
                let start = text.find('{').ok_or(original)?;
                serde_json::Deserializer::from_str(&text[start..])
                    .into_iter()
                    .next()
                    .expect("el objeto empieza en la entrada")
            })
            .map_err(|_| format!("{} devolvió texto que no es JSON válido.", self.provider))
    }

    fn generate(
        &self,
        prompt: &str,
        system: &str,
        temperature: f64,
        structured: bool,
    ) -> Result<String, String> {
        if self.provider == "gemini" {
            self.gemini(prompt, system, temperature, structured)
        } else {
            self.minimax(prompt, system, temperature, structured)
        }
    }

    fn gemini(
        &self,
        prompt: &str,
        system: &str,
        temperature: f64,
        structured: bool,
    ) -> Result<String, String> {
        let mut url = Url::parse(&format!("{GEMINI}/")).expect("URL base de Gemini válida");
        url.path_segments_mut()
            .expect("Ruta de Gemini válida")
            .pop_if_empty()
            .push(&format!("{}:generateContent", self.model));
        let mut body = json!({
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature":temperature},
        });
        if structured {
            body["generationConfig"]["responseMimeType"] = json!("application/json");
        }
        if !system.is_empty() {
            body["systemInstruction"] = json!({"parts":[{"text":system}]});
        }
        let request = self
            .client
            .post(url)
            .header("x-goog-api-key", &self.key)
            .json(&body);
        let result: Value =
            native_http::json(native_http::response(request.send(), "Gemini")?, "Gemini")?;
        let body = result["candidates"][0]["content"]["parts"]
            .as_array()
            .map(|parts| {
                parts
                    .iter()
                    .filter(|part| part["thought"] != true)
                    .filter_map(|p| p["text"].as_str())
                    .collect::<Vec<_>>()
                    .join("\n")
            });
        body.filter(|text| !text.trim().is_empty())
            .ok_or("Gemini devolvió una respuesta sin texto.".into())
    }

    fn minimax(
        &self,
        prompt: &str,
        system: &str,
        temperature: f64,
        structured: bool,
    ) -> Result<String, String> {
        let content = if structured {
            format!(
                "{prompt}\n\nResponde exclusivamente con JSON válido, sin explicaciones ni bloques de código."
            )
        } else {
            prompt.to_owned()
        };
        let mut messages = Vec::new();
        if !system.is_empty() {
            messages.push(json!({"role":"system", "content":system}));
        }
        messages.push(json!({"role":"user", "content":content}));
        let request = self
            .client
            .post(MINIMAX)
            .bearer_auth(&self.key)
            .json(&json!({
                "model": self.model, "messages": messages,
                "temperature": temperature, "stream": false
            }));
        let result: Value =
            native_http::json(native_http::response(request.send(), "MiniMax")?, "MiniMax")?;
        if let Some(code) = result["base_resp"]["status_code"].as_i64()
            && code != 0
        {
            return Err(format!("MiniMax rechazó la consulta ({code})."));
        }
        let content = &result["choices"][0]["message"]["content"];
        let text = if let Some(text) = content.as_str() {
            text.to_owned()
        } else if let Some(parts) = content.as_array() {
            parts
                .iter()
                .filter_map(|part| part["text"].as_str().or_else(|| part.as_str()))
                .collect()
        } else {
            String::new()
        };
        if text.trim().is_empty() {
            Err("MiniMax devolvió una respuesta sin texto.".into())
        } else {
            Ok(text.trim().into())
        }
    }
}
