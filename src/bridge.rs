use crate::subtitles::{Document, ResolveSnapshot};
use serde::Deserialize;
use serde_json::Value;
use std::{
    io::{Read, Write},
    path::PathBuf,
    process::{Command, Stdio},
    time::{Duration, Instant},
};

pub fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[derive(Clone, Debug, Default)]
pub struct ResolveStatus {
    pub running: bool,
    pub description: String,
    pub project: String,
    pub timeline: String,
}

#[derive(Deserialize)]
struct Envelope {
    ok: bool,
    result: Option<Value>,
    error: Option<String>,
}

pub(crate) fn decode(output: &str) -> Result<Value, String> {
    let records: Vec<_> = output
        .lines()
        .filter_map(|line| line.strip_prefix("DAVINCI_FLOW_GPUI="))
        .collect();
    if records.len() != 1 {
        return Err("El puente de Resolve no devolvió una respuesta única.".into());
    }
    let envelope: Envelope = serde_json::from_str(records[0])
        .map_err(|_| "Respuesta inválida del puente de Resolve.")?;
    if !envelope.ok {
        return Err(envelope
            .error
            .unwrap_or_else(|| "Resolve no confirmó la lectura.".into()));
    }
    envelope
        .result
        .ok_or_else(|| "Falta el resultado de Resolve.".into())
}

fn request(operation: &str, arguments: &[(&str, &str)]) -> Result<Value, String> {
    invoke("read_resolve.py", operation, arguments)
}

/// Ejecuta un adaptador de Python y devuelve su sobre JSON ya validado.
pub(crate) fn invoke(
    script: &str,
    operation: &str,
    arguments: &[(&str, &str)],
) -> Result<Value, String> {
    let arguments: serde_json::Map<String, Value> = arguments
        .iter()
        .map(|(key, value)| (key.to_string(), Value::String(value.to_string())))
        .collect();
    invoke_json(script, operation, Value::Object(arguments))
}

pub(crate) fn invoke_json(
    script: &str,
    operation: &str,
    arguments: Value,
) -> Result<Value, String> {
    if !matches!(
        script,
        "read_resolve.py" | "services.py" | "editorial.py" | "media.py"
    ) {
        return Err("Adaptador local no admitido.".into());
    }
    let input =
        serde_json::to_vec(&serde_json::json!({"operation":operation,"arguments":arguments}))
            .map_err(|e| e.to_string())?;
    if input.len() > 32 * 1024 * 1024 {
        return Err("La petición supera el límite de 32 MB.".into());
    }
    let writing = matches!(
        operation,
        "apply"
            | "undo"
            | "clean_tracks"
            | "import_media"
            | "fetch_download"
            | "voice_generate"
            | "voice_recover"
            | "insert_markers"
            | "write_subtitles"
    );
    let root = root();
    let python = std::env::var_os("DAVINCIFLOW_GPUI_PYTHON")
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            root.join(if cfg!(windows) {
                ".venv/Scripts/python.exe"
            } else {
                ".venv/bin/python"
            })
        });
    if !python.is_file() {
        return Err("Este servicio requiere el entorno de compatibilidad. Ejecútalo con mise setup o configura DAVINCIFLOW_GPUI_PYTHON.".into());
    }
    let compatibility = root.join("compat/python");
    let mut paths = vec![compatibility.join("src")];
    if let Some(existing) = std::env::var_os("PYTHONPATH") {
        paths.extend(std::env::split_paths(&existing));
    }
    let mut command = Command::new(python);
    command.arg(compatibility.join("bridge").join(script));
    command
        .env(
            "PYTHONPATH",
            std::env::join_paths(paths).map_err(|e| e.to_string())?,
        )
        .env("PYTHONUTF8", "1")
        .current_dir(&root)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000); // CREATE_NO_WINDOW
    }
    let mut child = command
        .spawn()
        .map_err(|e| format!("No se pudo iniciar el puente de Resolve: {e}"))?;
    let stdout = child.stdout.take().unwrap();
    let stderr = child.stderr.take().unwrap();
    let mut stdin = child.stdin.take().unwrap();
    let send = std::thread::spawn(move || stdin.write_all(&input));
    // Drenar ambos tubos mientras el hijo se ejecuta evita bloqueos con secuencias grandes.
    let out = std::thread::spawn(move || drain_bounded(stdout, 32 * 1024 * 1024));
    let err = std::thread::spawn(move || drain_bounded(stderr, 1024 * 1024));
    let start = Instant::now();
    let status = loop {
        match child.try_wait() {
            Ok(Some(status)) => break Ok(status),
            Ok(None) if writing || start.elapsed() < Duration::from_secs(180) => {
                std::thread::sleep(Duration::from_millis(50))
            }
            Ok(None) => {
                let _ = child.kill();
                let _ = child.wait();
                break Err(
                    "El servicio no respondió en 180 segundos. No se ha reintentado la operación."
                        .to_string(),
                );
            }
            Err(e) => {
                let _ = child.kill();
                let _ = child.wait();
                break Err(format!("Falló el proceso de lectura: {e}"));
            }
        }
    };
    let bytes = out
        .join()
        .map_err(|_| "Falló la lectura de la respuesta de Resolve.")?
        .map_err(|e| e.to_string())?;
    let _ = err.join();
    let sent = send
        .join()
        .map_err(|_| "Falló el envío al servicio local.")?;
    let status = status?;
    sent.map_err(|_| "No se pudo enviar la petición al servicio local.")?;
    if !status.success() {
        return Err(format!(
            "El puente terminó sin completar la lectura ({}).",
            status
        ));
    }
    let result =
        decode(&String::from_utf8(bytes).map_err(|_| "El puente devolvió texto que no es UTF-8.")?);
    result.map_err(|error| if writing {format!("{error} No se ha reintentado. Comprueba el resultado o recupera la operación pendiente antes de repetirla.")}else{error})
}

// Seguir drenando incluso al superar el presupuesto evita bloquear o cortar al hijo
// durante una escritura. Solo se conserva una cantidad acotada de salida.
pub(crate) fn drain_bounded(mut stream: impl Read, limit: usize) -> std::io::Result<Vec<u8>> {
    let mut retained = Vec::new();
    let mut buffer = [0u8; 8192];
    loop {
        let count = stream.read(&mut buffer)?;
        if count == 0 {
            break;
        }
        let keep = count.min(limit.saturating_sub(retained.len()));
        retained.extend_from_slice(&buffer[..keep]);
    }
    Ok(retained)
}

pub fn status() -> Result<ResolveStatus, String> {
    let value = crate::resolve_mcp::status()?;
    let running = value
        .get("running")
        .and_then(Value::as_bool)
        .ok_or("Resolve no confirmó su disponibilidad.")?;
    let description = if running {
        "Resolve está abierto y responde al MCP oficial.".into()
    } else {
        value
            .get("message")
            .and_then(Value::as_str)
            .unwrap_or("Resolve no está abierto. Ábrelo con un proyecto para capturar subtítulos.")
            .to_string()
    };
    let text = |key: &str| {
        value
            .get(key)
            .and_then(Value::as_str)
            .unwrap_or_default()
            .to_string()
    };
    Ok(ResolveStatus {
        running,
        description,
        project: text("project"),
        timeline: text("timeline"),
    })
}

/// Lee la pista indicada de Resolve dentro del rango de subtítulos pedido.
pub fn subtitles(track: u32, first: u32, last: u32) -> Result<Document, String> {
    capture(track, first, last).map(|(document, _)| document)
}

pub fn capture(track: u32, first: u32, last: u32) -> Result<(Document, Value), String> {
    let value = match crate::resolve_mcp::capture(track, first, last)? {
        Some(snapshot) => snapshot,
        None => capture_legacy(track, first, last)?,
    };
    let snapshot: ResolveSnapshot = serde_json::from_value(value.clone())
        .map_err(|_| "Resolve devolvió una captura de subtítulos inválida.")?;
    Ok((snapshot.try_into()?, value))
}

fn capture_legacy(track: u32, first: u32, last: u32) -> Result<Value, String> {
    let track = track.to_string();
    let first = first.to_string();
    let last = last.to_string();
    request(
        "subtitles",
        &[("track", &track), ("first", &first), ("last", &last)],
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn protocol_rejects_missing_duplicate_and_error_results() {
        assert!(decode("unrelated output").is_err());
        assert!(
            decode("DAVINCI_FLOW_GPUI={\"ok\":true}\nDAVINCI_FLOW_GPUI={\"ok\":true}").is_err()
        );
        assert_eq!(
            decode("DAVINCI_FLOW_GPUI={\"ok\":false,\"error\":\"Resolve cerrado\"}").unwrap_err(),
            "Resolve cerrado"
        );
        assert!(decode("DAVINCI_FLOW_GPUI={\"ok\":true}").is_err());
    }
}
