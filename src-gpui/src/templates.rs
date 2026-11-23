//! Inventario local de plantillas Fusion y persistencia de selecciones y presets.
use crate::{
    bridge, editorial_config,
    services::{TemplateCatalog, TemplateInfo, TemplatePreview},
};
use regex::Regex;
use serde_json::{Map, Value, json};
use sha2::{Digest, Sha256};
use std::{
    collections::{HashMap, HashSet},
    fs::{self, File},
    io::{Read, Write},
    path::{Path, PathBuf},
    sync::LazyLock,
};
use walkdir::WalkDir;
use zip::ZipArchive;

const MAX_SETTING_BYTES: u64 = 4 * 1024 * 1024;
const MAX_PREVIEW_BYTES: u64 = 64 * 1024 * 1024;
const IMAGES: &[&str] = &["png", "jpg", "jpeg", "gif"];
const VIDEOS: &[&str] = &["mp4", "webm", "mov"];
static PRESET_PREFIX: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"^SC-\d+-").unwrap());

fn sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn identifier(prefix: &str, locator: &str) -> String {
    let serialized = serde_json::to_string(locator).expect("una ruta es serializable");
    let hash = sha256(serialized.as_bytes());
    format!("{prefix}_{}", &hash[..20])
}

fn hidden(name: &str) -> bool {
    name.starts_with('.') || name.starts_with("__MACOSX")
}

fn category(name: &str, locator: &str) -> &'static str {
    let label = name.to_lowercase();
    let path = format!("{name} {locator}").to_lowercase();
    if label.contains("davinci flow") {
        return if label.contains("karaoke") {
            "karaoke"
        } else {
            "davinci_flow"
        };
    }
    for (category, aliases) in [
        ("native", &["templates.drfx"][..]),
        ("shorts", &["short", "tiktok", "reel", "vertical"][..]),
        ("youtube", &["youtube", "vlog", "horizontal"][..]),
        ("news", &["noticiero", "news", "titular", "reportaje"][..]),
        ("basic", &["básico", "basico", "basic_title"][..]),
    ] {
        if aliases.iter().any(|term| path.contains(term)) {
            return category;
        }
    }
    "installed"
}

fn descriptor(
    name: &str,
    source: &str,
    locator: &str,
    bytes: &[u8],
) -> Result<TemplateInfo, String> {
    static ROOT: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(
        r"Tools\s*=\s*ordered\(\)\s*\{\s*(\w+)\s*=\s*(MacroOperator|GroupOperator|TextPlus)\s*\{"
    ).unwrap()
    });
    static CONTROL: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r#"(?s)(\w+)\s*=\s*InstanceInput\s*\{[^{}]*Source\s*=\s*"StyledText"[^{}]*\}"#)
            .unwrap()
    });
    let content = std::str::from_utf8(bytes.strip_prefix(&[0xef, 0xbb, 0xbf]).unwrap_or(bytes))
        .map_err(|_| format!("La plantilla {name} no está codificada en UTF-8."))?;
    let mut template = TemplateInfo {
        id: identifier("tpl", locator),
        name: name.into(),
        source: source.into(),
        locator: locator.into(),
        category: category(name, locator).into(),
        fingerprint: sha256(bytes),
        text_input: "StyledText".into(),
        ..Default::default()
    };
    if let Some(root) = ROOT.captures(content)
        && &root[2] != "TextPlus"
    {
        let mut controls = CONTROL.captures_iter(content);
        if let Some(control) = controls.next()
            && controls.next().is_none()
        {
            template.text_tool = root[1].into();
            template.text_input = control[1].into();
        }
    }
    Ok(template)
}

fn bounded_read(stream: impl Read, limit: u64) -> Result<Vec<u8>, String> {
    let mut bytes = Vec::new();
    stream
        .take(limit + 1)
        .read_to_end(&mut bytes)
        .map_err(|error| error.to_string())?;
    if bytes.len() as u64 > limit {
        return Err("El archivo supera el tamaño permitido.".into());
    }
    Ok(bytes)
}

fn archive(path: &Path) -> Result<ZipArchive<File>, String> {
    ZipArchive::new(File::open(path).map_err(|error| error.to_string())?)
        .map_err(|error| error.to_string())
}

fn siblings(stem: &str, extensions: &[&str]) -> Vec<String> {
    ["", ".large"]
        .into_iter()
        .flat_map(|size| {
            extensions
                .iter()
                .map(move |ext| format!("{stem}{size}.{ext}"))
        })
        .collect()
}

fn extension(path: &Path) -> String {
    path.extension()
        .and_then(|name| name.to_str())
        .unwrap_or_default()
        .to_ascii_lowercase()
}

fn archive_templates(path: &Path) -> Result<Vec<TemplateInfo>, String> {
    let mut package = archive(path)?;
    let names: HashSet<String> = package
        .file_names()
        .filter_map(Result::ok)
        .map(|name| name.into_owned())
        .collect();
    let mut titles = Vec::new();
    for index in 0..package.len() {
        let entry = package
            .by_index_raw(index)
            .map_err(|error| error.to_string())?;
        let raw = entry
            .name()
            .map_err(|error| error.to_string())?
            .into_owned();
        let normalized = raw.replace('\\', "/");
        let member = Path::new(&normalized);
        if entry.is_dir()
            || normalized.split('/').any(hidden)
            || !format!("/{normalized}").to_lowercase().contains("/titles/")
            || !matches!(extension(member).as_str(), "setting" | "comp")
            || entry.size() > MAX_SETTING_BYTES
        {
            continue;
        }
        let Some(name) = member.file_stem().and_then(|s| s.to_str()) else {
            continue;
        };
        let locator = format!("{}::{raw}", path.display());
        drop(entry);
        let decoded = package.by_index(index).map_err(|error| error.to_string())?;
        let bytes = bounded_read(decoded, MAX_SETTING_BYTES)?;
        let mut title = descriptor(name, "installed_archive", &locator, &bytes)?;
        let stem = raw.rsplit_once('.').map_or(raw.as_str(), |(stem, _)| stem);
        title.preview_kind = if siblings(stem, VIDEOS).iter().any(|p| names.contains(p)) {
            "video".into()
        } else if siblings(stem, IMAGES).iter().any(|p| names.contains(p))
            || capture(&title).is_file()
        {
            "image".into()
        } else {
            String::new()
        };
        titles.push(title);
    }
    Ok(titles)
}

fn installed_template(path: &Path) -> Result<TemplateInfo, String> {
    let locator = path
        .to_str()
        .ok_or("La ruta de la plantilla no contiene texto válido.")?;
    let name = path
        .file_stem()
        .and_then(|s| s.to_str())
        .ok_or("La plantilla carece de nombre.")?;
    let mut file = File::open(path).map_err(|error| error.to_string())?;
    let mut template = if extension(path) == "drb" {
        let mut hash = Sha256::new();
        std::io::copy(&mut file, &mut hash).map_err(|error| error.to_string())?;
        TemplateInfo {
            id: identifier("bin", locator),
            locator: locator.into(),
            name: PRESET_PREFIX.replace(name, "").into_owned(),
            source: "installed_bin".into(),
            category: "animated".into(),
            fingerprint: format!("{:x}", hash.finalize()),
            text_input: "StyledText".into(),
            ..Default::default()
        }
    } else {
        descriptor(
            name,
            "installed_file",
            locator,
            &bounded_read(file, MAX_SETTING_BYTES)?,
        )?
    };
    let preview = local_preview(&template);
    template.preview_kind = if !preview.video.is_empty() {
        "video".into()
    } else if !preview.image.is_empty() {
        "image".into()
    } else {
        String::new()
    };
    Ok(template)
}

pub(crate) fn project_catalog(data: &Value) -> Result<Vec<TemplateInfo>, String> {
    const FOLDERS: &[&str] = &[
        "davinciflow",
        "davinci flow",
        "davinci_flow",
        "titles",
        "subtitles",
        "subtítulos",
        "títulos",
        "plantillas",
        "templates",
    ];
    let clips = data
        .as_array()
        .ok_or("Resolve devolvió un inventario inválido.")?;
    let mut found = Vec::new();
    let mut seen = HashSet::new();
    for row in clips {
        let name = row["name"].as_str().unwrap_or_default().trim();
        let kind = row["type"]
            .as_str()
            .unwrap_or_default()
            .trim()
            .to_lowercase();
        let title = if kind.is_empty() {
            let recognized_folder = row["folders"]
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(Value::as_str)
                .any(|folder| FOLDERS.contains(&folder.trim().to_lowercase().as_str()));
            let name = name.to_lowercase();
            recognized_folder
                || ["statement", "caption", "subtitle", "subtítulo", "plantilla"]
                    .iter()
                    .any(|word| name.contains(word))
        } else {
            !kind.contains("subtitle")
                && !kind.contains("subtítulo")
                && ["fusion", "title", "título", "text", "texto"]
                    .iter()
                    .any(|word| kind.contains(word))
        };
        if !title {
            continue;
        }
        let locator = row["id"]
            .as_str()
            .filter(|id| {
                !id.is_empty()
                    && id.len() <= 123
                    && id
                        .bytes()
                        .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-'))
            })
            .ok_or_else(|| {
                format!("Resolve no confirmó un ID estable para la plantilla {name}.")
            })?;
        if !seen.insert(locator) {
            continue;
        }
        let name = PRESET_PREFIX.replace(name, "");
        let mut template = TemplateInfo {
            id: format!("pool_{locator}"),
            name: if name.is_empty() {
                "Plantilla".into()
            } else {
                name.into_owned()
            },
            source: "media_pool".into(),
            locator: locator.into(),
            category: "general".into(),
            text_input: "StyledText".into(),
            ..Default::default()
        };
        if capture(&template).is_file() {
            template.preview_kind = "image".into();
        }
        found.push(template);
    }
    Ok(found)
}

fn scan(roots: &[(PathBuf, bool)], data: &Map<String, Value>) -> TemplateCatalog {
    let mut items = TemplateCatalog::default();
    let mut seen = HashSet::new();
    for (root, only_titles) in roots {
        if !root.is_dir() {
            continue;
        }
        for entry in WalkDir::new(root)
            .sort_by_file_name()
            .into_iter()
            .filter_entry(|entry| {
                entry.depth() == 0 || !entry.file_name().to_str().is_some_and(hidden)
            })
        {
            let Ok(entry) = entry else {
                continue;
            };
            let ext = extension(entry.path());
            if !matches!(ext.as_str(), "drb" | "drfx" | "setting" | "comp")
                || !entry.path().is_file()
            {
                continue;
            }
            if *only_titles
                && matches!(ext.as_str(), "setting" | "comp")
                && !entry
                    .path()
                    .to_string_lossy()
                    .replace('\\', "/")
                    .to_lowercase()
                    .contains("/titles/")
            {
                continue;
            }
            let path = editorial_config::resolved_path(entry.path());
            if !seen.insert(path.clone()) {
                continue;
            }
            let found = if ext == "drfx" {
                archive_templates(&path)
            } else {
                installed_template(&path).map(|template| vec![template])
            };
            match found {
                Ok(templates) => items.templates.extend(templates),
                Err(error) => items
                    .diagnostics
                    .push(format!("{}: {error}", entry.file_name().to_string_lossy())),
            }
        }
    }
    let selected = saved_selection(data);
    let configured: HashMap<_, _> = selected.iter().map(|title| (&title.id, title)).collect();
    for title in &mut items.templates {
        if let Some(saved) = configured.get(&title.id)
            && saved.fingerprint == title.fingerprint
        {
            title.text_tool.clone_from(&saved.text_tool);
            title.text_input.clone_from(&saved.text_input);
        }
    }
    items.selected_ids = selected.into_iter().map(|item| item.id).collect();
    items.presets = presets(data);
    items
}

fn saved_selection(data: &Map<String, Value>) -> Vec<TemplateInfo> {
    data.get("templates")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .filter_map(|value| serde_json::from_value(value.clone()).ok())
        .collect()
}

fn presets(data: &Map<String, Value>) -> Vec<String> {
    data.get("title_presets")
        .and_then(Value::as_object)
        .into_iter()
        .flatten()
        .map(|(name, _)| name.clone())
        .collect()
}

pub(crate) fn catalog() -> Result<TemplateCatalog, String> {
    let data = editorial_config::load_preferences()?;
    let home = std::env::home_dir().unwrap_or_default();
    let program_data = std::env::var_os("PROGRAMDATA")
        .map(PathBuf::from)
        .unwrap_or_else(|| "C:/ProgramData".into());
    let user_roaming = std::env::var_os("APPDATA")
        .map(PathBuf::from)
        .unwrap_or_else(|| home.join("AppData/Roaming"));
    let resolve = "Blackmagic Design/DaVinci Resolve";
    let mut roots = vec![(
        bridge::root().join("src/davinci_flow/editorial/basic_titles"),
        false,
    )];
    let configured = data
        .get("paths")
        .and_then(|paths| paths["titles"].as_str())
        .unwrap_or_default()
        .split(';')
        .map(str::trim)
        .filter(|p| !p.is_empty())
        .peekable();
    if configured.clone().peek().is_some() {
        roots.extend(configured.map(|path| (PathBuf::from(path), false)));
    } else {
        roots.extend([
            (
                editorial_config::data_dir().join("library/templates"),
                false,
            ),
            (program_data.join(resolve).join("Fusion/Templates"), true),
            (
                user_roaming.join(resolve).join("Support/Fusion/Templates"),
                true,
            ),
            (
                program_data
                    .join(resolve)
                    .join("Support/Workflow Integration Plugins/Snap Captions/Templates"),
                true,
            ),
        ]);
    }
    Ok(scan(&roots, &data))
}

fn capture(template: &TemplateInfo) -> PathBuf {
    let identity = format!(
        "{}:{}:{}:640x360-v1",
        template.id, template.locator, template.fingerprint
    );
    editorial_config::data_dir()
        .join("cache/title_captures")
        .join(format!("{}.png", sha256(identity.as_bytes())))
}

fn local_preview(template: &TemplateInfo) -> TemplatePreview {
    let capture = capture(template);
    let by_kind = |extensions: &[&str]| {
        (!matches!(template.source.as_str(), "media_pool" | "native"))
            .then(|| {
                extensions
                    .iter()
                    .map(|ext| Path::new(&template.locator).with_extension(ext))
                    .find(|path| path.is_file())
            })
            .flatten()
    };
    let image = by_kind(IMAGES).or_else(|| capture.is_file().then_some(capture));
    TemplatePreview {
        image: image
            .map(|path| path.to_string_lossy().into_owned())
            .unwrap_or_default(),
        video: by_kind(VIDEOS)
            .map(|path| path.to_string_lossy().into_owned())
            .unwrap_or_default(),
    }
}

pub(crate) fn preview(template: &TemplateInfo) -> Result<TemplatePreview, String> {
    if template.source != "installed_archive" {
        return Ok(local_preview(template));
    }
    let (path, member) = template
        .locator
        .split_once("::")
        .ok_or("La plantilla carece de archivo de origen.")?;
    let path = Path::new(path);
    let info = path.metadata().map_err(|error| error.to_string())?;
    let mut package = archive(path)?;
    let names: HashSet<String> = package
        .file_names()
        .filter_map(Result::ok)
        .map(|name| name.into_owned())
        .collect();
    let stem = member.rsplit_once('.').map_or(member, |(stem, _)| stem);
    let mut extract = |extensions: &[&str]| -> Result<Option<PathBuf>, String> {
        let Some(item) = siblings(stem, extensions)
            .into_iter()
            .find(|name| names.contains(name))
        else {
            return Ok(None);
        };
        let directory = editorial_config::data_dir().join("cache/title_previews");
        let key = format!(
            "{}:{:?}:{}:{item}",
            path.display(),
            info.modified().ok(),
            info.len()
        );
        let destination = directory.join(format!(
            "{}.{}",
            sha256(key.as_bytes()),
            extension(Path::new(&item))
        ));
        if !destination.is_file() {
            let entry = package.by_name(&item).map_err(|err| err.to_string())?;
            if entry.size() > MAX_PREVIEW_BYTES {
                return Err("La vista previa supera el tamaño permitido.".into());
            }
            let content = bounded_read(entry, MAX_PREVIEW_BYTES)?;
            fs::create_dir_all(&directory).map_err(|error| error.to_string())?;
            let mut pending =
                tempfile::NamedTempFile::new_in(&directory).map_err(|error| error.to_string())?;
            pending
                .write_all(&content)
                .map_err(|error| error.to_string())?;
            pending
                .persist(&destination)
                .map_err(|error| error.to_string())?;
        }
        Ok(Some(destination))
    };
    let image = extract(IMAGES)?.or_else(|| {
        let captured = capture(template);
        captured.is_file().then_some(captured)
    });
    let video = extract(VIDEOS)?;
    Ok(TemplatePreview {
        image: image
            .map(|p| p.to_string_lossy().into_owned())
            .unwrap_or_default(),
        video: video
            .map(|p| p.to_string_lossy().into_owned())
            .unwrap_or_default(),
    })
}

fn selection(ids: &[String]) -> Result<Vec<TemplateInfo>, String> {
    let chosen: HashSet<_> = ids.iter().collect();
    let templates: Vec<_> = catalog()?
        .templates
        .into_iter()
        .filter(|item| chosen.contains(&item.id))
        .collect();
    if templates.is_empty() || templates.len() > 60 || templates.len() != chosen.len() {
        return Err("Elige entre 1 y 60 plantillas disponibles.".into());
    }
    Ok(templates)
}

pub(crate) fn save_preset(name: &str, ids: &[String]) -> Result<(usize, Vec<String>), String> {
    let name = name.trim();
    if name.is_empty() || name.chars().count() > 80 {
        return Err("Escribe un nombre de preset de entre 1 y 80 caracteres.".into());
    }
    let templates = selection(ids)?;
    let mut collected = Vec::new();
    editorial_config::update_preferences(|data| {
        let current = data
            .entry("title_presets")
            .or_insert_with(|| json!({}))
            .as_object_mut()
            .ok_or("El archivo de preferencias contiene presets inválidos.")?;
        if current.len() >= 60 && !current.contains_key(name) {
            return Err("Se alcanzó el límite de 60 presets.".into());
        }
        current.insert(name.into(), json!(templates));
        collected = presets(data);
        Ok(())
    })?;
    Ok((templates.len(), collected))
}

pub(crate) fn use_preset(name: &str) -> Result<(usize, Vec<String>), String> {
    let mut selected = Vec::new();
    editorial_config::update_preferences(|data| {
        let value = data
            .get("title_presets")
            .and_then(|presets| presets.get(name.trim()))
            .ok_or("Ese preset ya no está disponible.")?;
        let entries: Vec<TemplateInfo> = serde_json::from_value(value.clone())
            .map_err(|_| "El preset contiene plantillas inválidas.")?;
        if !(1..=60).contains(&entries.len()) {
            return Err("El preset debe contener entre 1 y 60 plantillas.".into());
        }
        selected = entries.iter().map(|entry| entry.id.clone()).collect();
        data.insert("templates".into(), json!(entries));
        Ok(())
    })?;
    Ok((selected.len(), selected))
}

pub(crate) fn choose_pack(pack: &str) -> Result<(usize, Vec<String>), String> {
    let pack = pack.trim().to_lowercase();
    if pack.is_empty() {
        return Err("Selecciona un pack de plantillas.".into());
    }
    let catalog = catalog()?;
    let entries: Vec<_> = catalog
        .templates
        .into_iter()
        .filter(|title| {
            title.category == pack
                || if pack == "native" {
                    title.source == "native"
                        || title.locator.to_lowercase().contains("templates.drfx")
                } else {
                    title.name.to_lowercase().contains(&pack)
                }
        })
        .take(30)
        .collect();
    if entries.is_empty() {
        return Ok((0, catalog.selected_ids));
    }
    save_selection(&entries)
}

fn save_selection(entries: &[TemplateInfo]) -> Result<(usize, Vec<String>), String> {
    editorial_config::update_preferences(|data| {
        data.insert("templates".into(), json!(entries));
        Ok(())
    })?;
    Ok((
        entries.len(),
        entries.iter().map(|title| title.id.clone()).collect(),
    ))
}

pub(crate) fn assign_node(ids: &[String], tool: &str, input: &str) -> Result<usize, String> {
    let mut entries = selection(ids)?;
    let input = if input.trim().is_empty() {
        "StyledText"
    } else {
        input.trim()
    };
    for title in &mut entries {
        title.text_tool = tool.trim().into();
        title.text_input = input.into();
    }
    save_selection(&entries).map(|(count, _)| count)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn scans_archive_without_extracting_and_keeps_locator_identifiers() {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("Templates.drfx");
        let mut archive = zip::ZipWriter::new(File::create(&path).unwrap());
        let options = zip::write::SimpleFileOptions::default()
            .compression_method(zip::CompressionMethod::Deflated);
        let setting = br#"{ Tools = ordered() { Root = MacroOperator { Inputs = { Main = InstanceInput { Source = "StyledText" } } } } }"#;
        for (name, bytes) in [
            ("Edit/Titles/Title.setting", setting.as_slice()),
            ("Edit/Titles/Title.large.mov", b"preview".as_slice()),
            ("__MACOSX/Edit/Titles/Title.setting", setting.as_slice()),
        ] {
            archive.start_file(name, options).unwrap();
            archive.write_all(bytes).unwrap();
        }
        archive.finish().unwrap();
        let items = scan(&[(directory.path().into(), true)], &Map::new());
        let template = &items.templates[0];
        assert_eq!(items.templates.len(), 1);
        assert_eq!(
            (
                &*template.category,
                &*template.preview_kind,
                &*template.text_tool,
                &*template.text_input
            ),
            ("native", "video", "Root", "Main")
        );
        assert_eq!(
            template.locator,
            format!("{}::Edit/Titles/Title.setting", path.display())
        );
        assert_eq!(fs::read_dir(directory.path()).unwrap().count(), 1);
    }

    #[test]
    fn filters_media_pool_titles_without_including_subtitle_clips() {
        let sample = json!([
            {"id":"T-1","name":"SC-8-Intro","type":"Fusion Title","folders":["Master"]},
            {"id":"T-1","name":"Duplicado","type":"Fusion Title","folders":["Master"]},
            {"id":"T-2","name":"Texto","type":"","folders":["Master","Plantillas","Para vídeos"]},
            {"id":"S-1","name":"Subtítulo","type":"Subtitle","folders":["Master","Plantillas"]},
            {"id":"V-1","name":"Plano","type":"Video","folders":["Master"]},
        ]);
        let choices = project_catalog(&sample).unwrap();
        assert_eq!(choices.len(), 2);
        assert_eq!((&*choices[0].id, &*choices[0].name), ("pool_T-1", "Intro"));
        assert_eq!(choices[1].id, "pool_T-2");
    }
}
