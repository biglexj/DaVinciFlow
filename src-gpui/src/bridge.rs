use crate::subtitles::{Document, ResolveSnapshot};
use serde::Deserialize;
use serde_json::Value;
use std::{
    io::Read,
    path::PathBuf,
    process::{Command, Stdio},
    time::{Duration, Instant},
};

pub fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .to_owned()
}

#[derive(Clone, Debug, Default)]
pub struct ResolveStatus {
    pub running: bool,
    pub description: String,
}

#[derive(Deserialize)]
struct Envelope {
    ok: bool,
    result: Option<Value>,
    error: Option<String>,
}

fn decode(output: &str) -> Result<Value, String> {
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

fn request(operation: &str) -> Result<Value, String> {
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
        return Err("No se encontró .venv. Prepara el entorno Python del proyecto o configura DAVINCIFLOW_GPUI_PYTHON.".into());
    }
    let mut paths = vec![root.join("src")];
    if let Some(existing) = std::env::var_os("PYTHONPATH") {
        paths.extend(std::env::split_paths(&existing));
    }
    let mut command = Command::new(python);
    command
        .arg(root.join("src-gpui/bridge/read_resolve.py"))
        .arg(operation)
        .env(
            "PYTHONPATH",
            std::env::join_paths(paths).map_err(|e| e.to_string())?,
        )
        .env("PYTHONUTF8", "1")
        .current_dir(&root)
        .stdin(Stdio::null())
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
    // Drenar ambos tubos mientras el hijo se ejecuta evita bloqueos con secuencias grandes.
    let out = std::thread::spawn(move || {
        let mut value = Vec::new();
        stdout
            .take(32 * 1024 * 1024)
            .read_to_end(&mut value)
            .map(|_| value)
    });
    let err = std::thread::spawn(move || {
        let mut value = Vec::new();
        stderr
            .take(1024 * 1024)
            .read_to_end(&mut value)
            .map(|_| value)
    });
    let start = Instant::now();
    let status = loop {
        match child.try_wait() {
            Ok(Some(status)) => break Ok(status),
            Ok(None) if start.elapsed() < Duration::from_secs(110) => {
                std::thread::sleep(Duration::from_millis(50))
            }
            Ok(None) => {
                let _ = child.kill();
                let _ = child.wait();
                break Err("Resolve no respondió a la lectura en 110 segundos.".to_string());
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
    let status = status?;
    if !status.success() {
        return Err(format!(
            "El puente terminó sin completar la lectura ({}).",
            status
        ));
    }
    decode(&String::from_utf8(bytes).map_err(|_| "El puente devolvió texto que no es UTF-8.")?)
}

pub fn status() -> Result<ResolveStatus, String> {
    let value = request("status")?;
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
    Ok(ResolveStatus {
        running,
        description,
    })
}

pub fn subtitles() -> Result<Document, String> {
    let snapshot: ResolveSnapshot = serde_json::from_value(request("subtitles")?)
        .map_err(|_| "Resolve devolvió una captura de subtítulos inválida.")?;
    snapshot.try_into()
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
