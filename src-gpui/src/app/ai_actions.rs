//! Panel de IA y guion de la pestaña «Corrección».
use super::*;

impl FlowApp {
    /// Alterna el panel de alineación semántica.
    pub(super) fn toggle_ai_panel(&mut self, cx: &mut Context<Self>) {
        self.ai_panel_open = !self.ai_panel_open;
        cx.notify();
    }

    /// Alinea el guion con los subtítulos mediante el proveedor de IA configurado.
    pub(super) fn align_with_ai(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if self.busy || self.session.has_draft() {
            self.notify(
                Err("Guarda el borrador antes de iniciar la corrección.".into()),
                cx,
            );
            return;
        }
        if self.session.document().cues.is_empty() {
            self.notify(Err("No hay subtítulos para procesar con IA.".into()), cx);
            return;
        }
        let script = self.ai_script.read(cx).value().to_string();
        let glossary = self.glossary.read(cx).value().to_string();
        let detect_markers = self.ai_detect_markers;
        // El motor trabaja en fotogramas relativos al origen de la fuente.
        let fps = self
            .capture_snapshot
            .as_ref()
            .and_then(|s| s["fps"].as_f64())
            .unwrap_or_else(|| {
                self.editor_fps
                    .read(cx)
                    .value()
                    .trim()
                    .parse::<f64>()
                    .ok()
                    .filter(|value| value.is_finite() && *value > 0.)
                    .unwrap_or(24.)
            });
        let input = editorial::document_revision(self.session.document());
        let snapshot = self
            .capture_snapshot
            .clone()
            .filter(|s| s["source"].as_str() == Some("resolve"));
        let cues: Vec<(f64, f64, String)> = self
            .session
            .document()
            .cues
            .iter()
            .map(|cue| {
                (
                    cue.start_ms as f64 / 1000. * fps,
                    cue.end_ms as f64 / 1000. * fps,
                    cue.text.clone(),
                )
            })
            .collect();
        self.work(
            "Alineando y corrigiendo subtítulos con IA…",
            window,
            cx,
            move || services::align(&cues, &script, &glossary, detect_markers),
            move |this, alignment, window, cx| {
                if input!=editorial::document_revision(this.session.document()) {this.notify(Err("La transcripción cambió durante la corrección; se conserva la edición actual.".into()),cx);return;}
                let corrections = alignment.corrections;
                let markers = alignment.markers.clone();
                let summary = alignment.summary.clone();
                let texts = alignment.cues.clone();
                let applied = this.session.apply_texts(texts);
                match applied {
                    Ok(changed) => {
                        this.ai_markers = markers.clone();
                        this.ai_snapshot=snapshot;
                        this.sync_editor(window, cx);
                        this.refilter(cx);
                        this.notify(
                            Ok(format!(
                                "IA: {corrections} corrección(es), {changed} bloque(s) actualizado(s) y {} marcador(es). {summary}",
                                markers.len()
                            )),
                            cx,
                        );
                    }
                    Err(error) => this.notify(Err(error), cx),
                }
            },
        );
    }

    /// Inserta los marcadores generados por la IA en la línea de tiempo de Resolve.
    pub(super) fn insert_ai_markers(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if self.ai_markers.is_empty() {
            self.notify(
                Err("No hay marcadores generados por la IA para insertar.".into()),
                cx,
            );
            return;
        }
        let markers = self.ai_markers.clone();
        let Some(snapshot) = self.ai_snapshot.clone() else {
            self.notify(
                Err("Los marcadores requieren una captura identificada de Resolve.".into()),
                cx,
            );
            return;
        };
        self.work(
            "Insertando marcadores en DaVinci Resolve…",
            window,
            cx,
            move || services::insert_markers(&markers, &snapshot),
            |this, inserted, _, cx| {
                this.notify(
                    Ok(format!(
                        "Se insertaron {inserted} marcadores en la línea de tiempo activa."
                    )),
                    cx,
                );
            },
        );
    }
}
