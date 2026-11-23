//! Consulta de versiones por HTTPS sin depender de la aplicación Python.
use crate::{native_http, services::Release};
use regex::Regex;
use semver::Version;
use serde::Deserialize;
use std::{sync::LazyLock, time::Duration};

const URL: &str = "https://api.github.com/repos/biglexj/DaVinciFlow/releases/latest";
const RELEASES: &str = "https://github.com/biglexj/DaVinciFlow/releases/";

#[derive(Deserialize)]
struct Asset {
    name: String,
    browser_download_url: String,
}

#[derive(Deserialize)]
struct GithubRelease {
    tag_name: String,
    html_url: String,
    published_at: Option<String>,
    body: Option<String>,
    #[serde(default)]
    assets: Vec<Asset>,
}

pub(crate) fn latest() -> Result<Option<Release>, String> {
    let client = native_http::client(Duration::from_secs(8))?;
    let request = client
        .get(URL)
        .header("Accept", "application/vnd.github+json");
    let response = native_http::response(request.send(), "GitHub")
        .map_err(|_| "No se pudo consultar GitHub Releases.".to_owned())?;
    if response.status() == reqwest::StatusCode::NOT_FOUND {
        return Ok(None);
    }
    convert(
        native_http::json(response, "GitHub")?,
        env!("CARGO_PKG_VERSION"),
    )
    .map(Some)
}

fn convert(raw: GithubRelease, current: &str) -> Result<Release, String> {
    let version = raw.tag_name.trim().trim_start_matches(['v', 'V']);
    let remote =
        Version::parse(version).map_err(|_| "GitHub devolvió una versión sin formato SemVer.")?;
    let current =
        Version::parse(current).map_err(|_| "La versión local no tiene formato SemVer.")?;
    let page = raw.html_url;
    if !page.starts_with(&format!("{RELEASES}tag/")) {
        return Err("GitHub no devolvió la página oficial de la versión.".into());
    }
    let download_url = raw
        .assets
        .into_iter()
        .filter(|asset| {
            asset
                .browser_download_url
                .starts_with(&format!("{RELEASES}download/"))
        })
        .filter_map(|asset| {
            let name = asset.name.to_ascii_lowercase();
            let rank = [".exe", ".msi", ".zip", ".whl", ".tar.gz"]
                .iter()
                .position(|ext| name.ends_with(ext))?;
            Some((rank, asset))
        })
        .min_by_key(|(rank, _)| *rank)
        .map(|(_, asset)| asset)
        .map(|asset| asset.browser_download_url)
        .unwrap_or_else(|| page.clone());
    Ok(Release {
        version: version.into(),
        is_newer: remote.cmp_precedence(&current).is_gt(),
        published_at: raw.published_at.unwrap_or_default(),
        notes: sanitize(raw.body.as_deref().unwrap_or_default()),
        download_url,
        page_url: page,
    })
}

fn sanitize(body: &str) -> String {
    static MARKUP: LazyLock<Regex> =
        LazyLock::new(|| Regex::new(r"<[^>]*>|[A-Za-z]:\\[^\s]+").unwrap());
    static LINKS: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\[([^]]+)\]\([^)]*\)").unwrap());
    let clean = LINKS.replace_all(body, "$1");
    let clean = MARKUP.replace_all(&clean, "");
    let notes = clean
        .lines()
        .map(|line| {
            let line = line.trim().trim_start_matches('#').trim();
            let line = line
                .strip_prefix("- ")
                .or_else(|| line.strip_prefix("* "))
                .map(|value| format!("• {value}"))
                .unwrap_or_else(|| line.to_owned());
            line.replace("**", "").replace("__", "").replace('`', "")
        })
        .filter(|line| !line.trim().is_empty())
        .collect::<Vec<_>>()
        .join("\n");
    if notes.is_empty() {
        "Consulta los detalles en GitHub Releases.".into()
    } else {
        notes
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn does_not_treat_build_metadata_as_a_new_version_and_prefers_the_installer() {
        let release = serde_json::from_value(json!({
            "tag_name":"v1.0.0+build.2",
            "html_url":format!("{RELEASES}tag/v1.0.0+build.2"),
            "body":"## Ajustes\n- **Arreglo** en [GitHub](https://github.com/).",
            "assets":[
                {"name":"SHA256SUMS.txt","browser_download_url":format!("{RELEASES}download/SHA256SUMS.txt")},
                {"name":"portátil.zip","browser_download_url":format!("{RELEASES}download/portable.zip")},
                {"name":"Setup.exe","browser_download_url":format!("{RELEASES}download/Setup.exe")}
            ],
        })).unwrap();
        let checked = convert(release, "1.0.0").unwrap();
        assert!(!checked.is_newer);
        assert!(checked.download_url.ends_with("/Setup.exe"));
        assert_eq!(checked.notes, "Ajustes\n• Arreglo en GitHub.");
    }
}
