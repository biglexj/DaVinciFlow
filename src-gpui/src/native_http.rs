//! Transporte HTTPS de los servicios nativos. Los errores no incluyen cuerpos ni claves.
use reqwest::blocking::{Client, Response};
use serde::de::DeserializeOwned;
use std::{io::Read, time::Duration};

pub(crate) fn client(timeout: Duration) -> Result<Client, String> {
    Client::builder()
        .https_only(true)
        .redirect(reqwest::redirect::Policy::none())
        .timeout(timeout)
        .connect_timeout(Duration::from_secs(10))
        .user_agent(concat!("DaVinciFlow/", env!("CARGO_PKG_VERSION")))
        .build()
        .map_err(|_| "No se pudo iniciar la conexión HTTPS.".into())
}

pub(crate) fn response(
    result: Result<Response, reqwest::Error>,
    service: &str,
) -> Result<Response, String> {
    result.map_err(|error| {
        if error.is_timeout() {
            format!("{service} no respondió a tiempo.")
        } else {
            format!("No se pudo conectar con {service}.")
        }
    })
}

pub(crate) fn json<T: DeserializeOwned>(response: Response, service: &str) -> Result<T, String> {
    let status = response.status();
    if !status.is_success() {
        return Err(format!("{service} devolvió HTTP {}.", status.as_u16()));
    }
    const LIMIT: u64 = 16 * 1024 * 1024;
    let mut bytes = Vec::new();
    response
        .take(LIMIT + 1)
        .read_to_end(&mut bytes)
        .map_err(|_| format!("No se pudo leer la respuesta de {service}."))?;
    if bytes.len() as u64 > LIMIT {
        return Err(format!("La respuesta de {service} supera 16 MiB."));
    }
    serde_json::from_slice(&bytes)
        .map_err(|_| format!("La respuesta de {service} no tiene el formato esperado."))
}
