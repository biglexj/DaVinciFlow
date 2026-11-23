//! Transporte stdio para leer el estado y los subtítulos mediante el MCP oficial.
use serde_json::{Value, json};
use std::{
    io::{BufRead, BufReader, Read, Write},
    path::{Path, PathBuf},
    process::{Child, ChildStdin, Command, Stdio},
    sync::mpsc::{self, Receiver},
    time::{Duration, Instant},
};

const TIMEOUT: Duration = Duration::from_secs(15);
const MAX_MESSAGE: u64 = 32 * 1024 * 1024;

fn executable() -> Result<Option<PathBuf>, String> {
    if let Some(path) = std::env::var_os("DAVINCIFLOW_RESOLVE_MCP").filter(|p| !p.is_empty()) {
        let path = PathBuf::from(path);
        return path
            .is_file()
            .then_some(Some(path))
            .ok_or_else(|| "DAVINCIFLOW_RESOLVE_MCP no apunta a un ejecutable existente.".into());
    }
    #[cfg(windows)]
    {
        use winreg::{RegKey, enums::HKEY_CLASSES_ROOT};
        let installed = PathBuf::from(
            std::env::var_os("ProgramFiles").unwrap_or_else(|| "C:\\Program Files".into()),
        )
        .join("Blackmagic Design/DaVinci Resolve/ResolveMCP.exe");
        if installed.is_file() {
            return Ok(Some(installed));
        }
        let command: Option<String> = RegKey::predef(HKEY_CLASSES_ROOT)
            .open_subkey(r"ResolveDrpFile\shell\open\command")
            .and_then(|key| key.get_value(""))
            .ok();
        Ok(command
            .as_deref()
            .and_then(|line| line.strip_prefix('"')?.split_once('"'))
            .and_then(|(app, _)| {
                PathBuf::from(app)
                    .parent()
                    .map(|dir| dir.join("ResolveMCP.exe"))
            })
            .filter(|path| path.is_file()))
    }
    #[cfg(not(windows))]
    {
        let installed = PathBuf::from(if cfg!(target_os = "macos") {
            "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Applications/ResolveMCP"
        } else {
            "/opt/resolve/bin/ResolveMCP"
        });
        Ok(installed.is_file().then_some(installed))
    }
}

struct ResolveMcp {
    child: Child,
    input: ChildStdin,
    output: Receiver<Value>,
    next_id: u64,
}

impl Drop for ResolveMcp {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

impl ResolveMcp {
    fn start(path: PathBuf) -> Result<Self, String> {
        let mut command = Command::new(path);
        command
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null());
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            command.creation_flags(0x08000000); // CREATE_NO_WINDOW
        }
        let mut child = command
            .spawn()
            .map_err(|error| format!("No se pudo iniciar el MCP oficial de Resolve: {error}"))?;
        let input = child.stdin.take().expect("stdin configurado");
        let mut stdout = BufReader::new(child.stdout.take().expect("stdout configurado"));
        let (sender, output) = mpsc::sync_channel(16);
        std::thread::spawn(move || {
            let mut line = Vec::new();
            loop {
                line.clear();
                match (&mut stdout)
                    .take(MAX_MESSAGE + 1)
                    .read_until(b'\n', &mut line)
                {
                    Ok(n) if n > 0 && n as u64 <= MAX_MESSAGE => {
                        if let Ok(message) = serde_json::from_slice(&line)
                            && sender.send(message).is_err()
                        {
                            break;
                        }
                    }
                    _ => break,
                }
            }
        });
        let mut session = Self {
            child,
            input,
            output,
            next_id: 0,
        };
        let hello = session.rpc(
            "initialize",
            json!({
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "davinci-flow", "version": env!("CARGO_PKG_VERSION")},
            }),
            TIMEOUT,
        )?;
        if hello["serverInfo"]["name"] != "davinci_resolve" {
            return Err("El ejecutable no respondió como el MCP oficial de Resolve.".into());
        }
        session.send(json!({"jsonrpc":"2.0", "method":"notifications/initialized"}))?;
        Ok(session)
    }

    fn send(&mut self, message: Value) -> Result<(), String> {
        serde_json::to_writer(&mut self.input, &message)
            .map_err(|_| "Se interrumpió el canal local con Resolve.")?;
        self.input
            .write_all(b"\n")
            .and_then(|()| self.input.flush())
            .map_err(|_| "Se interrumpió el canal local con Resolve.".into())
    }

    fn rpc(&mut self, method: &str, parameters: Value, timeout: Duration) -> Result<Value, String> {
        self.next_id += 1;
        let id = self.next_id;
        self.send(json!({"jsonrpc":"2.0","id":id,"method":method,"params":parameters}))?;
        let deadline = Instant::now() + timeout;
        loop {
            let message = self
                .output
                .recv_timeout(deadline.saturating_duration_since(Instant::now()))
                .map_err(|error| match error {
                    mpsc::RecvTimeoutError::Timeout => {
                        "El MCP de Resolve agotó el tiempo de espera."
                    }
                    mpsc::RecvTimeoutError::Disconnected => {
                        "El MCP de Resolve cerró el canal sin responder."
                    }
                })?;
            if message["id"] != id {
                continue;
            }
            if message["jsonrpc"] != "2.0"
                || message.get("error").is_some()
                || !message["result"].is_object()
            {
                return Err(format!(
                    "Resolve presentó un error en la llamada MCP {method}."
                ));
            }
            return Ok(message["result"].clone());
        }
    }

    fn status(&mut self) -> Result<Value, String> {
        tool_data(self.rpc(
            "tools/call",
            json!({
                "name":"get_resolve_status", "arguments":{},
            }),
            TIMEOUT,
        )?)
    }

    fn script(&mut self, script: &str) -> Result<Value, String> {
        let data = tool_data(self.rpc(
            "tools/call",
            json!({
                "name":"run_script", "arguments":{"script":script,"timeout":60},
            }),
            Duration::from_secs(75),
        )?)?;
        data.get("result")
            .cloned()
            .ok_or("Resolve no confirmó el resultado de la operación.".into())
    }
}

fn tool_data(response: Value) -> Result<Value, String> {
    if response["isError"] == true {
        return Err("Resolve rechazó la consulta de estado.".into());
    }
    let data = match response.get("structuredContent") {
        Some(value) => value.clone(),
        None => {
            let parts: Vec<_> = response["content"]
                .as_array()
                .ok_or("El MCP de Resolve devolvió contenido inválido.")?
                .iter()
                .filter(|part| part["type"] == "text")
                .filter_map(|part| part["text"].as_str())
                .collect();
            serde_json::from_str(&parts.join("\n"))
                .map_err(|_| "El MCP de Resolve no devolvió un resultado JSON válido.")?
        }
    };
    if !data.is_object() || data.get("error").is_some() {
        return Err("El MCP de Resolve no confirmó el estado.".into());
    }
    Ok(data)
}

pub(crate) fn status() -> Result<Value, String> {
    match configured()? {
        Some(path) => ResolveMcp::start(path)?.status(),
        None => Ok(
            json!({"running":false,"message":"La comprobación de disponibilidad requiere el MCP oficial de Resolve."}),
        ),
    }
}

fn configured() -> Result<Option<PathBuf>, String> {
    let transport =
        std::env::var("DAVINCIFLOW_RESOLVE_TRANSPORT").unwrap_or_else(|_| "auto".into());
    let transport = transport.trim().to_ascii_lowercase();
    if !matches!(transport.as_str(), "auto" | "mcp" | "legacy") {
        return Err("DAVINCIFLOW_RESOLVE_TRANSPORT debe ser auto, mcp o legacy.".into());
    }
    if transport == "legacy" {
        return Ok(None);
    }
    let path = executable()?;
    if path.is_none() && transport == "mcp" {
        return Err("No se encontró el MCP oficial de DaVinci Resolve.".into());
    }
    Ok(path)
}

pub(crate) fn capture(track: u32, first: u32, last: u32) -> Result<Option<Value>, String> {
    let Some(path) = configured()? else {
        return Ok(None);
    };
    if track == 0 || first == 0 || last < first {
        return Err("La pista y el rango de subtítulos deben ser válidos.".into());
    }
    let mut session = ResolveMcp::start(path)?;
    if session.status()?["running"] != true {
        return Err("Abre DaVinci Resolve Studio con un proyecto y una secuencia.".into());
    }
    // Los únicos argumentos del código fijo son tres enteros tipados.
    let script = format!(
        "track, first, last = {track}, {first}, {last}\n{}",
        include_str!("resolve_scripts/read_subtitles.py")
    );
    let captured = session.script(&script)?;
    if captured["ok"] != true {
        return Err(captured["message"]
            .as_str()
            .unwrap_or("Resolve no confirmó la captura de la secuencia.")
            .into());
    }
    normalize_capture(&captured["snapshot"], track, first, last).map(Some)
}

pub(crate) fn import_media(file: &Path, bins: &[&str]) -> Result<Option<String>, String> {
    let Some(path) = configured()? else {
        return Ok(None);
    };
    let file = crate::editorial_config::resolved_path(file);
    if !file.is_file() {
        return Err("El recurso ya no existe.".into());
    }
    let file = file
        .to_str()
        .ok_or("La ruta del recurso no contiene texto válido.")?;
    let file = serde_json::to_string(file).map_err(|err| err.to_string())?;
    let bins = serde_json::to_string(bins).map_err(|err| err.to_string())?;
    let mut session = ResolveMcp::start(path)?;
    if session.status()?["running"] != true {
        return Err("Abre DaVinci Resolve Studio con un proyecto.".into());
    }
    // Las rutas se serializan como literales de cadena. Nunca se ejecutan como código.
    let script = format!(
        "file_path = {file}\nfolders = {bins}\n{}",
        include_str!("resolve_scripts/import_media.py")
    );
    let result = session.script(&script).map_err(|error| {
        format!("{error} Comprueba el Media Pool antes de repetir la importación.")
    })?;
    let receipt = result["bin"].as_str().filter(|bin| !bin.is_empty());
    if result["success"] == true
        && let Some(bin) = receipt
    {
        return Ok(Some(bin.into()));
    }
    Err(result["message"]
        .as_str()
        .unwrap_or("Resolve no confirmó la importación. Comprueba el Media Pool.")
        .into())
}

pub(crate) fn project_templates() -> Result<Option<Vec<crate::services::TemplateInfo>>, String> {
    let Some(path) = configured()? else {
        return Ok(None);
    };
    let mut session = ResolveMcp::start(path)?;
    if session.status()?["running"] != true {
        return Err("Abre DaVinci Resolve Studio con un proyecto.".into());
    }
    let value = session.script(include_str!("resolve_scripts/read_templates.py"))?;
    if value["ok"] != true {
        return Err("Resolve no confirmó la lectura del Media Pool.".into());
    }
    crate::templates::project_catalog(&value["clips"]).map(Some)
}

fn normalize_capture(snapshot: &Value, track: u32, first: u32, last: u32) -> Result<Value, String> {
    let source = snapshot
        .as_object()
        .ok_or("Resolve devolvió una captura inválida.")?;
    let number = |key| {
        snapshot[key]
            .as_f64()
            .or_else(|| snapshot[key].as_str()?.parse().ok())
            .filter(|value: &f64| value.is_finite())
    };
    let fps = number("fps")
        .filter(|fps| *fps > 0.0)
        .ok_or("FPS inválidos en la secuencia.")?;
    let width = number("width")
        .filter(|value| *value >= 1.0)
        .ok_or("Resolución inválida en la secuencia.")? as u64;
    let height = number("height")
        .filter(|value| *value >= 1.0)
        .ok_or("Resolución inválida en la secuencia.")? as u64;
    let origin = number("origin").ok_or("Resolve no confirmó el fotograma inicial.")? as i64;
    let valid_id = |key| {
        source
            .get(key)
            .and_then(Value::as_str)
            .is_some_and(|s| !s.trim().is_empty())
    };
    if !valid_id("project_id") || !valid_id("timeline_id") {
        return Err("Resolve no confirmó la identidad del proyecto y la secuencia.".into());
    }

    let mut cues = source
        .get("cues")
        .and_then(Value::as_array)
        .cloned()
        .ok_or("Resolve devolvió subtítulos inválidos.")?;
    let time = |cue: &Value, field: &str| cue[field].as_f64().unwrap_or(f64::NAN);
    if cues.iter().any(|cue| {
        let start = time(cue, "start_frame");
        let end = time(cue, "end_frame");
        !start.is_finite()
            || start < 0.0
            || !end.is_finite()
            || end <= start
            || cue["text"]
                .as_str()
                .is_none_or(|text| text.trim().is_empty())
    }) {
        return Err("Resolve devolvió subtítulos con tiempos o texto inválidos.".into());
    }
    cues.sort_by(|a, b| {
        time(a, "start_frame")
            .total_cmp(&time(b, "start_frame"))
            .then_with(|| time(a, "end_frame").total_cmp(&time(b, "end_frame")))
    });
    let cues: Vec<_> = cues
        .into_iter()
        .skip((first - 1) as usize)
        .take((last - first + 1) as usize)
        .map(|mut cue| {
            cue["track_index"] = json!(track);
            cue
        })
        .collect();
    if cues.is_empty() {
        return Err("La fuente debe contener subtítulos dentro del rango seleccionado.".into());
    }
    if cues
        .windows(2)
        .any(|pair| time(&pair[1], "start_frame") < time(&pair[0], "end_frame"))
    {
        return Err("Revisa los subtítulos solapados o desordenados.".into());
    }
    let mut cuts = source
        .get("cut_records")
        .and_then(Value::as_array)
        .cloned()
        .ok_or("Resolve no confirmó la revisión del montaje.")?;
    if cuts.iter().any(|cut| {
        !matches!(cut["kind"].as_str(), Some("video" | "audio"))
            || cut["track"].as_u64().is_none()
            || cut["id"].as_str().is_none_or(str::is_empty)
            || !time(cut, "start").is_finite()
            || !time(cut, "end").is_finite()
    }) {
        return Err("Resolve devolvió un corte sin identidad o tiempos válidos.".into());
    }
    cuts.sort_by(|a, b| {
        a["kind"]
            .as_str()
            .cmp(&b["kind"].as_str())
            .then(a["track"].as_u64().cmp(&b["track"].as_u64()))
            .then(a["id"].as_str().cmp(&b["id"].as_str()))
            .then_with(|| time(a, "start").total_cmp(&time(b, "start")))
            .then_with(|| time(a, "end").total_cmp(&time(b, "end")))
    });
    let mut references = Vec::with_capacity(cuts.len());
    let mut frames = Vec::with_capacity(cuts.len());
    for cut in cuts {
        let name = cut["name"].as_str().unwrap_or_default();
        let item_type = cut["type"].as_str().unwrap_or_default();
        let synthetic = matches!(
            item_type,
            "transition" | "generator" | "title" | "still" | "fusion"
        );
        let media = cut["media_id"].as_str().unwrap_or_default();
        let reference = if !media.is_empty() {
            format!("media:{media}")
        } else if synthetic {
            format!("synthetic:{item_type}:{name}")
        } else {
            String::new()
        };
        let mut row = vec![
            cut["kind"].clone(),
            cut["track"].clone(),
            cut["id"].clone(),
            json!(time(&cut, "start")),
            json!(time(&cut, "end")),
        ];
        if let (Some(left), Some(right)) = (cut["left"].as_f64(), cut["right"].as_f64()) {
            row.extend([json!(left), json!(right)]);
        } else if synthetic || cut["media"] != true {
            let item_type = if item_type.is_empty() {
                "transition"
            } else {
                item_type
            };
            row.extend([Value::Null, Value::Null, json!(item_type), json!(name)]);
        } else {
            return Err("Resolve no confirmó los offsets de un clip del montaje.".into());
        }
        frames.push(row);
        references.push(reference);
    }
    Ok(json!({
        "project":source.get("project"), "timeline":source.get("timeline"),
        "project_id":source.get("project_id"), "timeline_id":source.get("timeline_id"),
        "fps":fps,"width":width,"height":height,"origin":origin,"track":track,"cues":cues,
        "cuts":frames,"cut_source_refs":references,"source":"resolve","first":first,"last":last
    }))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reads_structured_and_text_results() {
        let result = json!({"running":true,"project":"Prueba"});
        assert_eq!(
            tool_data(json!({"structuredContent": result})).unwrap(),
            result
        );
        assert_eq!(
            tool_data(json!({"content":[{"type":"text","text":result.to_string()}]})).unwrap(),
            result
        );
        assert!(tool_data(json!({"isError":true,"structuredContent":result})).is_err());
    }

    #[test]
    fn captures_sorted_cues_and_preserves_timeline_identity_and_cut_references() {
        let raw = json!({
            "project":"Proyecto", "timeline":"Secuencia", "project_id":"p", "timeline_id":"t",
            "fps":"24", "width":"1920", "height":"1080", "origin":86400,
            "cues":[{"text":"Segundo","start_frame":86425,"end_frame":86448},
                    {"text":"Primero","start_frame":86400,"end_frame":86424}],
            "cut_records":[{"kind":"video","track":1,"id":"v","start":86400,"end":86448,
                            "left":0,"right":8,"media_id":"m","media":true},
                           {"kind":"audio","track":1,"id":"a","start":86424,"end":86448,
                            "left":null,"right":null,"type":"transition","name":"Corte","media":false}]
        });
        let captured = normalize_capture(&raw, 1, 2, 2).unwrap();
        assert_eq!(captured["timeline_id"], "t");
        assert_eq!(captured["cues"][0]["text"], "Segundo");
        assert_eq!(captured["cues"][0]["track_index"], 1);
        assert_eq!(captured["cuts"][0][0], "audio");
        assert_eq!(
            captured["cut_source_refs"],
            json!(["synthetic:transition:Corte", "media:m"])
        );
        let mut missing_id = raw;
        missing_id["project_id"] = Value::Null;
        assert!(normalize_capture(&missing_id, 1, 1, 2).is_err());
    }

    #[test]
    #[ignore = "requiere el MCP instalado, solo consulta su estado"]
    fn installed_resolve_status() {
        assert!(executable().unwrap().is_some());
        let status = crate::bridge::status().unwrap();
        eprintln!("MCP oficial respondió, Resolve abierto: {}", status.running);
        if status.running {
            let titles = project_templates().unwrap();
            eprintln!(
                "MCP confirmó el inventario del Media Pool: {} plantillas",
                titles.unwrap().len()
            );
            match capture(1, 1, 3) {
                Ok(Some(snapshot)) => {
                    assert!(snapshot["cues"].as_array().is_some_and(|c| !c.is_empty()))
                }
                Err(error)
                    if error.contains("subtítulos") || error.contains("tiempo seleccionada") =>
                {
                    eprintln!("Resolve confirmó el estado de la captura: {error}");
                }
                other => panic!("Resolve no confirmó la lectura: {other:?}"),
            }
        }
    }
}
