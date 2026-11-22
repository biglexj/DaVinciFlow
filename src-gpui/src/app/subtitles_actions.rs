//! Acciones del ciclo de corrección de subtítulos, captura y exportación SRT.
use super::*;

impl FlowApp {
    pub(super) fn sync_editor(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let text = self.session.draft().to_owned();
        self.edit
            .update(cx, |state, cx| state.set_value(text, window, cx));
        cx.notify();
    }

    pub(super) fn refilter(&mut self, cx: &mut Context<Self>) {
        let query = self.find.read(cx).value().to_lowercase();
        self.filtered_cues = self.session.filtered_indices(&query);
        cx.notify();
    }

    pub(super) fn filter_library(&mut self, cx: &mut Context<Self>) {
        let query = self.library_filter.read(cx).value().to_lowercase();
        self.library_filtered = self
            .library_inventory
            .resources
            .iter()
            .enumerate()
            .filter(|(_, resource)| {
                query.is_empty() || resource.name.to_lowercase().contains(&query)
            })
            .map(|(index, _)| index)
            .collect();
        cx.notify();
    }

    pub(super) fn select_cue(&mut self, index: usize, window: &mut Window, cx: &mut Context<Self>) {
        match self.session.select(index) {
            Ok(()) => self.sync_editor(window, cx),
            Err(error) => self.notify(Err(error), cx),
        }
    }

    pub(super) fn install_document(
        &mut self,
        doc: Document,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        if let Err(error) = self.session.load(doc) {
            self.notify(Err(error), cx);
            return;
        }
        self.proposal = None;
        self.proposal_input.clear();
        self.proposal_dirty = false;
        self.capture_snapshot = None;
        self.ai_snapshot = None;
        self.ai_markers.clear();
        self.conflicts.clear();
        self.batch_processed = 0;
        self.batch_total = 0;
        self.batch_next = None;
        self.editor_stage = 1;
        self.find.update(cx, |s, cx| s.set_value("", window, cx));
        self.refilter(cx);
        self.sync_editor(window, cx);
        let document = self.session.document();
        let warnings = document.warnings.join(" ");
        self.notify(
            Ok(format!(
                "{} subtítulos cargados. {warnings}",
                document.cues.len()
            )),
            cx,
        );
    }

    pub(super) fn choose_srt(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if self.busy {
            return;
        }
        if self.session.is_dirty()
            || self.session.has_draft()
            || self.proposal_dirty
            || self.review_has_draft(cx)
        {
            self.notify(
                Err("Guarda o descarta la edición pendiente y exporta o deshaz los cambios antes de abrir otra fuente.".into()),
                cx,
            );
            return;
        }
        let receiver = cx.prompt_for_paths(PathPromptOptions {
            files: true,
            directories: false,
            multiple: false,
            prompt: Some("Abrir subtítulos SRT".into()),
        });
        cx.spawn_in(window, async move |this, cx| {
            let selection = receiver.await;
            let _ = this.update_in(cx, |this, window, cx| match selection {
                Ok(Ok(Some(paths))) => {
                    if let Some(path) = paths.into_iter().next() {
                        this.work(
                            "Leyendo SRT…",
                            window,
                            cx,
                            move || subtitles::load(&path),
                            |this, doc, window, cx| this.install_document(doc, window, cx),
                        );
                    }
                }
                Ok(Ok(None)) => {}
                _ => this.notify(Err("No se pudo abrir el selector de archivos.".into()), cx),
            });
        })
        .detach();
    }

    pub(super) fn export(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if self.busy || self.session.document().cues.is_empty() {
            return;
        }
        let snapshot = match self.session.export_snapshot() {
            Ok(snapshot) => snapshot,
            Err(error) => {
                self.notify(Err(error), cx);
                return;
            }
        };
        let directory = std::env::var_os("USERPROFILE")
            .map(PathBuf::from)
            .unwrap_or_else(bridge::root);
        let receiver = cx.prompt_for_new_path(&directory, Some("subtitulos-corregidos.srt"));
        cx.spawn_in(window, async move |this, cx| {
            let selection = receiver.await;
            let _ = this.update_in(cx, |this, window, cx| match selection {
                Ok(Ok(Some(mut path))) => {
                    if path.extension().is_none() {
                        path.set_extension("srt");
                    }
                    if !path
                        .extension()
                        .is_some_and(|s| s.eq_ignore_ascii_case("srt"))
                    {
                        this.notify(Err("La exportación debe tener extensión .srt.".into()), cx);
                        return;
                    }
                    this.work(
                        "Exportando subtítulos…",
                        window,
                        cx,
                        move || {
                            let receipt = snapshot.save_new(&path)?;
                            Ok((path, receipt))
                        },
                        |this, (path, receipt), _, cx| {
                            let result = this
                                .session
                                .accept_export(receipt)
                                .map(|()| format!("SRT exportado: {}", path.display()));
                            this.notify(result, cx);
                        },
                    );
                }
                Ok(Ok(None)) => {}
                _ => this.notify(
                    Err("No se pudo abrir el diálogo de exportación.".into()),
                    cx,
                ),
            });
        })
        .detach();
    }

    /// Lee los subtítulos de Resolve con los valores de pista y rango del Editor.
    pub(super) fn capture(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if self.session.is_dirty()
            || self.session.has_draft()
            || self.proposal_dirty
            || self.review_has_draft(cx)
        {
            self.notify(
                Err("Guarda o descarta la edición pendiente y exporta o deshaz los cambios antes de capturar otra fuente.".into()),
                cx,
            );
            return;
        }
        let track = self.number(&self.editor_track, cx, 1);
        let first = self.number(&self.editor_first, cx, 1);
        let last = self.number(&self.editor_last, cx, 120);
        let (track, first, last) = match (track, first, last) {
            (Some(track), Some(first), Some(last)) => (track, first, last),
            _ => {
                self.notify(Err("Pista, Desde y Hasta deben ser números.".into()), cx);
                return;
            }
        };
        self.work(
            "Leyendo subtítulos de Resolve…",
            window,
            cx,
            move || bridge::capture(track, first, last),
            |this, (doc, snapshot), window, cx| {
                this.install_document(doc, window, cx);
                this.capture_snapshot = Some(snapshot);
            },
        );
    }

    /// Captura la secuencia completa de la pista activa de Resolve.
    pub(super) fn capture_full(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if self.session.is_dirty()
            || self.session.has_draft()
            || self.proposal_dirty
            || self.review_has_draft(cx)
        {
            self.notify(
                Err(
                    "Guarda o descarta la edición pendiente antes de capturar toda la pista."
                        .into(),
                ),
                cx,
            );
            return;
        }
        let Some(track) = self.number(&self.editor_track, cx, 1) else {
            self.notify(Err("La pista debe ser un número positivo.".into()), cx);
            return;
        };
        self.work(
            "Capturando toda la pista de subtítulos de Resolve…",
            window,
            cx,
            move || bridge::capture(track, 1, 100_000),
            |this, (doc, snapshot), window, cx| {
                let count = doc.cues.len().max(1);
                this.editor_first
                    .update(cx, |s, cx| s.set_value("1", window, cx));
                this.editor_last
                    .update(cx, |s, cx| s.set_value(count.to_string(), window, cx));
                this.install_document(doc, window, cx);
                this.capture_snapshot = Some(snapshot);
            },
        );
    }

    /// Desplaza el rango de captura al bloque anterior o siguiente y captura de Resolve.
    pub(super) fn shift_capture_range(
        &mut self,
        forward: bool,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        let first = self.number(&self.editor_first, cx, 1).unwrap_or(1);
        let last = self.number(&self.editor_last, cx, 120).unwrap_or(120);
        let size = last.saturating_sub(first).saturating_add(1).max(1);
        let (new_first, new_last) = if forward {
            (last.saturating_add(1), last.saturating_add(size))
        } else {
            if first <= 1 {
                self.notify(
                    Ok("Ya te encuentras en el primer bloque de subtítulos.".into()),
                    cx,
                );
                return;
            }
            let nl = first.saturating_sub(1).max(1);
            let nf = nl.saturating_sub(size - 1).max(1);
            (nf, nl)
        };
        self.editor_first
            .update(cx, |s, cx| s.set_value(new_first.to_string(), window, cx));
        self.editor_last
            .update(cx, |s, cx| s.set_value(new_last.to_string(), window, cx));
        self.capture(window, cx);
    }

    /// Lee un valor entero de un campo; `None` cuando no es un número válido.
    pub(super) fn number(
        &self,
        field: &Entity<InputState>,
        cx: &Context<Self>,
        fallback: u32,
    ) -> Option<u32> {
        let raw = field.read(cx).value().trim().to_owned();
        if raw.is_empty() {
            return Some(fallback);
        }
        let value = raw.parse::<u32>().ok()?;
        if value == 0 { None } else { Some(value) }
    }

    pub(super) fn check_resolve(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.resolve = None;
        self.work(
            "Consultando Resolve…",
            window,
            cx,
            bridge::status,
            |this, status, _, cx| {
                let message = status.description.clone();
                let running = status.running;
                this.resolve = Some(status);
                this.notify(if running { Ok(message) } else { Err(message) }, cx);
            },
        );
    }

    pub(super) fn normalize(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let result = self.session.normalize();
        self.after_batch(result, window, cx);
    }

    pub(super) fn replace(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let find = self.find.read(cx).value().to_string();
        let replacement = self.replacement.read(cx).value().to_string();
        let result = self
            .session
            .replace(&find, &replacement, self.case_sensitive);
        self.after_batch(result, window, cx);
    }

    pub(super) fn apply_glossary(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let glossary = self.glossary.read(cx).value().to_string();
        let result = self.session.apply_glossary(&glossary);
        self.after_batch(result, window, cx);
    }

    fn after_batch(
        &mut self,
        result: Result<usize, String>,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        if result.is_ok() {
            self.sync_editor(window, cx);
            self.refilter(cx);
        }
        self.notify(
            result.map(|n| format!("{n} subtítulos modificados. Los tiempos se conservan.")),
            cx,
        );
    }

    pub(super) fn save_edit(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let result = self.session.save_draft();
        if result.is_ok() {
            self.sync_editor(window, cx);
            self.refilter(cx);
        }
        self.notify(
            result.map(|_| "Cambio guardado. Exporta el SRT para conservarlo en disco.".into()),
            cx,
        );
    }

    pub(super) fn discard_edit(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.session.discard_draft();
        self.sync_editor(window, cx);
    }

    pub(super) fn restore_cue(
        &mut self,
        index: usize,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        let result = self.session.restore_cue(index);
        if result.is_ok() {
            self.sync_editor(window, cx);
            self.refilter(cx);
        }
        self.notify(
            result.map(|_| "Subtítulo restaurado a su texto original.".into()),
            cx,
        );
    }

    pub(super) fn next_cue(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let Some(current) = self.session.selected() else {
            return;
        };
        let next = current + 1;
        if next >= self.session.document().cues.len() {
            self.notify(Ok("No hay más subtítulos en esta fuente.".into()), cx);
            return;
        }
        self.select_cue(next, window, cx);
    }

    pub(super) fn history(&mut self, redo: bool, window: &mut Window, cx: &mut Context<Self>) {
        let result = if redo {
            self.session.redo()
        } else {
            self.session.undo()
        };
        if result.is_ok() {
            self.sync_editor(window, cx);
            self.refilter(cx);
        }
        self.notify(
            result.map(|()| {
                if redo {
                    "Cambio rehecho.".into()
                } else {
                    "Cambio deshecho.".into()
                }
            }),
            cx,
        );
    }

    /// Escribe los subtítulos actuales en la pista nativa de subtítulos de DaVinci Resolve.
    pub(super) fn write_subtitles_to_resolve(
        &mut self,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        if self.busy || self.session.has_draft() {
            self.notify(
                Err(
                    "Guarda o descarta la edición pendiente antes de enviar subtítulos a Resolve."
                        .into(),
                ),
                cx,
            );
            return;
        }
        if self.session.document().cues.is_empty() {
            self.notify(
                Err("No hay subtítulos cargados para escribir en Resolve.".into()),
                cx,
            );
            return;
        }
        let fps = self
            .capture_snapshot
            .as_ref()
            .and_then(|s| s["fps"].as_f64())
            .filter(|value| value.is_finite() && *value > 0.)
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
        let track = self.number(&self.editor_track, cx, 1);
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
            "Escribiendo subtítulos en DaVinci Resolve…",
            window,
            cx,
            move || services::write_subtitles(&cues, track, "davinci-flow-subtitulos"),
            |this, receipt, _, cx| {
                this.notify(
                    Ok(format!(
                        "{} subtítulos escritos en la pista {} de Resolve.",
                        receipt.cue_count, receipt.track_index
                    )),
                    cx,
                );
            },
        );
    }

    /// Propaga los subtítulos corregidos al Editor; ambas vistas comparten la sesión.
    pub(super) fn sync_to_editor(&mut self, cx: &mut Context<Self>) {
        if self.session.document().cues.is_empty() {
            self.notify(Err("No hay subtítulos para sincronizar.".into()), cx);
            return;
        }
        self.tab = Tab::Editor;
        self.notify(
            Ok("Subtítulos corregidos cargados en el Editor.".into()),
            cx,
        );
    }
}
