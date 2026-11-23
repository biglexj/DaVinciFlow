use super::*;

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum ProposalMode {
    Direct,
    Ai,
    Decisions,
    BatchNext,
}

impl FlowApp {
    pub(super) fn review_has_draft(&self, cx: &App) -> bool {
        let Some(decision) = self
            .proposal
            .as_ref()
            .and_then(|p| p.decisions.get(self.review_selected))
        else {
            return false;
        };
        self.review_context.read(cx).value().as_ref() != decision.context
            || self.review_main.read(cx).value().as_ref() != decision.main
            || self.review_accent.read(cx).value().as_ref() != decision.accent
            || self.review_note.read(cx).value().as_ref() != decision.edit_note
            || self.review_enabled != decision.enabled
            || self.review_sfx != decision.resource_id
            || self.review_templates != decision.templates
    }

    pub(super) fn select_review(
        &mut self,
        index: usize,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        if self.review_has_draft(cx) {
            self.notify(
                Err("Guarda la revisión del bloque antes de cambiar de selección.".into()),
                cx,
            );
            return;
        }
        self.review_selected = index;
        self.sync_review(window, cx);
    }

    pub(super) fn sync_review(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if let Some(d) = self
            .proposal
            .as_ref()
            .and_then(|p| p.decisions.get(self.review_selected))
        {
            let (context, main, accent, note, sfx) = (
                d.context.clone(),
                d.main.clone(),
                d.accent.clone(),
                d.edit_note.clone(),
                d.resource_id.clone(),
            );
            self.review_enabled = d.enabled;
            self.review_sfx = sfx;
            self.review_sfx_open = false;
            self.review_templates = d.templates.clone();
            self.review_context
                .update(cx, |s, cx| s.set_value(context, window, cx));
            self.review_main
                .update(cx, |s, cx| s.set_value(main, window, cx));
            self.review_accent
                .update(cx, |s, cx| s.set_value(accent, window, cx));
            self.review_note
                .update(cx, |s, cx| s.set_value(note, window, cx));
        }
        cx.notify();
    }

    pub(super) fn prepare_proposal_with(
        &mut self,
        mode: ProposalMode,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        if self.session.has_draft() || self.review_has_draft(cx) {
            self.notify(
                Err(
                    "Guarda o descarta la edición pendiente antes de preparar otra propuesta."
                        .into(),
                ),
                cx,
            );
            return;
        }
        self.persist_editor_preferences(cx);
        let document = self.session.document().clone();
        let capture = self.capture_snapshot.clone();
        let fps = self
            .editor_fps
            .read(cx)
            .value()
            .parse::<f64>()
            .unwrap_or(24.);
        let mut options = self.editor_options.clone();
        options.direction = self.editor_direction.read(cx).value().trim().to_owned();
        let batch_size = self.editor_batch_size.clone();
        let library_preferences = self.preferences.clone();
        let selected_templates = self.catalog_selected.clone();
        let existing_proposal = (self.proposal_input == editorial::document_revision(&document))
            .then(|| self.proposal.clone())
            .flatten();
        let resolve_running = self.resolve.as_ref().is_some_and(|r| r.running);
        let cached_project_templates: Vec<services::TemplateInfo> = self
            .templates
            .iter()
            .filter(|t| t.source == "media_pool")
            .cloned()
            .collect();
        let label = match mode {
            ProposalMode::Direct => "Preparando propuesta directa…",
            ProposalMode::Ai => "Preparando propuesta con IA…",
            ProposalMode::Decisions => "Evaluando decisiones editoriales…",
            ProposalMode::BatchNext => "Procesando la siguiente tanda con IA…",
        };
        self.work(
            label,
            window,
            cx,
            move || {
                let _ = services::sync_library(
                    &library_preferences.folders,
                    &library_preferences.selected,
                );
                if options.direction.is_empty() {
                    options.direction = services::settings()?.preferences.direction;
                }
                for (category, _) in library::CATEGORIES {
                    let inventory = library::scan_category(
                        category,
                        &library_preferences.folders_for(category),
                        20_000,
                    );
                    options.resources.extend(
                        inventory
                            .resources
                            .iter()
                            .filter(|r| library_preferences.is_selected(&r.id))
                            .map(|r| {
                                serde_json::json!({
                                    "id": r.id,
                                    "name": r.name,
                                    "category": r.category
                                })
                            }),
                    );
                }
                let (mut templates, _) = services::templates()?;
                if capture.is_some() || resolve_running || !cached_project_templates.is_empty() {
                    let project_items =
                        services::project_templates().unwrap_or(cached_project_templates);
                    if !project_items.is_empty() {
                        let mut existing_ids: std::collections::HashSet<String> =
                            templates.iter().map(|t| t.id.clone()).collect();
                        let mut merged = Vec::new();
                        for item in project_items {
                            if existing_ids.insert(item.id.clone()) {
                                merged.push(item);
                            }
                        }
                        merged.extend(templates);
                        templates = merged;
                    }
                }
                let filtered: Vec<_> = if !selected_templates.is_empty() {
                    templates
                        .iter()
                        .filter(|t| selected_templates.contains(&t.id))
                        .cloned()
                        .collect()
                } else {
                    Vec::new()
                };
                let all_default_files =
                    !filtered.is_empty() && filtered.iter().all(|t| t.source == "installed_file");
                if filtered.is_empty() || all_default_files {
                    let applicable: Vec<_> = templates
                        .iter()
                        .filter(|t| matches!(t.source.as_str(), "media_pool" | "installed_bin"))
                        .take(30)
                        .cloned()
                        .collect();
                    if !applicable.is_empty() {
                        templates = applicable;
                    } else if !filtered.is_empty() {
                        templates = filtered;
                    }
                } else {
                    templates = filtered;
                }
                let base = editorial::Proposal::direct(
                    &document,
                    capture.as_ref(),
                    templates,
                    fps,
                    options,
                )?;
                match mode {
                    ProposalMode::Direct => {
                        Ok((base, editorial::document_revision(&document), None))
                    }
                    ProposalMode::Ai => {
                        let generated = editorial::generate(&base)?;
                        Ok((generated, editorial::document_revision(&document), None))
                    }
                    ProposalMode::Decisions => {
                        let generated = editorial::generate_decisions(&base)?;
                        Ok((generated, editorial::document_revision(&document), None))
                    }
                    ProposalMode::BatchNext => {
                        let progress =
                            editorial::batch_next(&base, &batch_size, existing_proposal.as_ref())?;
                        let p = progress.proposal.clone();
                        Ok((p, editorial::document_revision(&document), Some(progress)))
                    }
                }
            },
            |this, (proposal, input, batch), window, cx| {
                this.proposal = Some(proposal);
                this.proposal_input = input;
                this.proposal_dirty = true;
                this.conflicts.clear();
                this.review_selected = 0;
                this.editor_stage = 2;
                this.sync_review(window, cx);
                if let Some(progress) = batch {
                    this.batch_processed = progress.processed;
                    this.batch_total = progress.total;
                    this.batch_next = progress.next_number;
                    this.notify(
                        Ok(format!(
                            "Tanda guardada ({}/{} subtítulos procesados). {}",
                            progress.processed, progress.total, progress.message
                        )),
                        cx,
                    );
                } else {
                    this.notify(
                        Ok("Propuesta lista. Revisa los bloques antes de aplicar.".into()),
                        cx,
                    );
                }
            },
        );
    }

    pub(super) fn review_save(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let user_resource_match = if self.review_sfx.is_empty() {
            None
        } else {
            self.user_sfx_resources
                .iter()
                .chain(self.user_broll_resources.iter())
                .find(|r| r.id == self.review_sfx)
                .cloned()
        };
        let Some(proposal) = &mut self.proposal else {
            return;
        };
        let Some(original) = proposal.decisions.get(self.review_selected) else {
            return;
        };
        let mut decision = original.clone();
        decision.context = self.review_context.read(cx).value().to_string();
        decision.main = self.review_main.read(cx).value().to_string();
        decision.accent = self.review_accent.read(cx).value().to_string();
        decision.edit_note = self.review_note.read(cx).value().to_string();
        decision.enabled = self.review_enabled;
        decision.resource_id = self.review_sfx.clone();
        decision.templates = self.review_templates.clone();
        if let Some(res) = user_resource_match
            && let Some(opts) = &mut proposal.options
        {
            let already_listed = opts
                .resources
                .iter()
                .any(|r| r.get("id").and_then(Value::as_str) == Some(res.id.as_str()));
            if !already_listed {
                if opts.resources.len() >= 80 {
                    self.notify(
                        Err("La propuesta alcanzó el límite de 80 recursos compartidos.".into()),
                        cx,
                    );
                    return;
                }
                opts.resources.push(serde_json::json!({
                    "id": res.id,
                    "name": res.name,
                    "category": res.category,
                }));
            }
        }
        for (layer, text) in [
            ("context", &decision.context),
            ("main", &decision.main),
            ("accent", &decision.accent),
        ] {
            if text.trim().is_empty() {
                decision.templates.remove(layer);
            } else if !decision.templates.contains_key(layer)
                && let Some(template) = proposal.templates.first()
            {
                decision.templates.insert(layer.into(), template.id.clone());
            }
        }
        match proposal.review(self.review_selected, decision) {
            Ok(()) => {
                self.proposal_dirty = true;
                self.sync_review(window, cx);
                self.notify(Ok("Bloque guardado y marcado como revisado.".into()), cx);
            }
            Err(error) => self.notify(Err(error), cx),
        }
    }

    pub(super) fn review_next(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if self.review_has_draft(cx) {
            self.review_save(window, cx);
            if self.error {
                return;
            }
        }
        let Some(total) = self.proposal.as_ref().map(|p| p.decisions.len()) else {
            return;
        };
        if self.review_selected + 1 < total {
            self.review_selected += 1;
            self.sync_review(window, cx);
        } else {
            self.notify(
                Ok("Has llegado al último bloque de la propuesta.".into()),
                cx,
            );
        }
    }

    pub(super) fn review_approve_all(&mut self, cx: &mut Context<Self>) {
        if self.review_has_draft(cx) {
            self.notify(Err("Guarda primero la edición del bloque.".into()), cx);
            return;
        }
        if let Some(p) = &mut self.proposal {
            let result = p
                .approve_all()
                .map(|()| "Todos los bloques se han marcado como revisados.".into());
            if result.is_ok() {
                self.proposal_dirty = true;
            }
            self.notify(result, cx);
        }
    }

    pub(super) fn cycle_review_template(&mut self, layer: &str, cx: &mut Context<Self>) {
        self.review_template_layer = if self.review_template_layer.as_deref() == Some(layer) {
            None
        } else {
            Some(layer.into())
        };
        cx.notify();
    }

    pub(super) fn save_proposal(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if self.review_has_draft(cx) {
            self.notify(
                Err("Guarda la edición antes de exportar la propuesta.".into()),
                cx,
            );
            return;
        }
        let Some(proposal) = self.proposal.clone() else {
            return;
        };
        let receiver = cx.prompt_for_new_path(&bridge::root(), Some("propuesta-revisada.json"));
        cx.spawn_in(window, async move |this, cx| {
            let selection = receiver.await;
            let _ = this.update_in(cx, |this, window, cx| {
                if let Ok(Ok(Some(mut path))) = selection {
                    if path.extension().is_none() {
                        path.set_extension("json");
                    }
                    this.work(
                        "Guardando propuesta…",
                        window,
                        cx,
                        move || {
                            proposal.save_new(&path)?;
                            Ok((
                                path,
                                serde_json::to_value(proposal).map_err(|e| e.to_string())?,
                            ))
                        },
                        |this, (path, saved), _, cx| {
                            if this
                                .proposal
                                .as_ref()
                                .and_then(|p| serde_json::to_value(p).ok())
                                .as_ref()
                                == Some(&saved)
                            {
                                this.proposal_dirty = false;
                            }
                            this.notify(Ok(format!("Propuesta guardada: {}", path.display())), cx);
                        },
                    );
                }
            });
        })
        .detach();
    }

    pub(super) fn open_proposal(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if self.proposal_dirty
            || self.session.is_dirty()
            || self.session.has_draft()
            || self.review_has_draft(cx)
        {
            self.notify(
                Err("Guarda los cambios pendientes antes de abrir otra propuesta.".into()),
                cx,
            );
            return;
        }
        let receiver = cx.prompt_for_paths(PathPromptOptions {
            files: true,
            directories: false,
            multiple: false,
            prompt: Some("Abrir propuesta editorial".into()),
        });
        cx.spawn_in(window, async move |this, cx| {
            let selection = receiver.await;
            let _ = this.update_in(cx, |this, window, cx| {
                if let Ok(Ok(Some(paths))) = selection
                    && let Some(path) = paths.into_iter().next()
                {
                    this.work(
                        "Leyendo propuesta…",
                        window,
                        cx,
                        move || editorial::Proposal::load(&path),
                        |this, p, window, cx| {
                            let document = serde_json::from_value::<subtitles::ResolveSnapshot>(
                                p.snapshot.clone(),
                            )
                            .map_err(|e| e.to_string())
                            .and_then(Document::try_from);
                            match document {
                                Ok(doc) => {
                                    this.install_document(doc, window, cx);
                                    this.capture_snapshot = Some(p.snapshot.clone());
                                    if let Some(opts) = &p.options {
                                        this.editor_options = opts.clone();
                                        let dir = opts.direction.clone();
                                        this.editor_direction
                                            .update(cx, |s, cx| s.set_value(dir, window, cx));
                                    }
                                    this.proposal = Some(p);
                                    this.proposal_input =
                                        editorial::document_revision(this.session.document());
                                    this.proposal_dirty = false;
                                    this.review_selected = 0;
                                    this.editor_stage = 2;
                                    this.sync_review(window, cx);
                                }
                                Err(error) => this.notify(Err(error), cx),
                            }
                        },
                    );
                }
            });
        })
        .detach();
    }

    pub(super) fn apply_proposal(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if self.review_has_draft(cx) || self.session.has_draft() {
            self.notify(Err("Guarda los borradores antes de aplicar.".into()), cx);
            return;
        }
        let Some(proposal) = self.proposal.clone() else {
            return;
        };
        if self.proposal_input != editorial::document_revision(self.session.document()) {
            self.notify(
                Err("La transcripción cambió después de preparar la propuesta. Prepara una propuesta nueva.".into()),
                cx,
            );
            return;
        }
        let unreviewed = proposal.decisions.len().saturating_sub(proposal.reviewed());
        if unreviewed > 0 {
            let receiver = window.prompt(
                PromptLevel::Warning,
                "Aprobar y aplicar propuesta",
                Some(&format!(
                    "Hay {unreviewed} bloque(s) pendiente(s) de revisión manual. ¿Deseas marcar todos como revisados y aplicar la propuesta en DaVinci Resolve?"
                )),
                &[
                    PromptButton::Cancel("Volver a revisar".into()),
                    PromptButton::Ok("Aprobar todo y aplicar".into()),
                ],
                cx,
            );
            cx.spawn_in(window, async move |this, cx| {
                if receiver.await.ok() == Some(1) {
                    let _ = this.update_in(cx, |this, window, cx| {
                        this.review_approve_all(cx);
                        if !this.error {
                            this.apply_proposal_confirmed(window, cx);
                        }
                    });
                }
            })
            .detach();
            return;
        }
        self.apply_proposal_confirmed(window, cx);
    }

    fn apply_proposal_confirmed(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let Some(proposal) = self.proposal.clone() else {
            return;
        };
        if let Err(e) = proposal.validate(true) {
            self.notify(Err(e), cx);
            return;
        }
        self.work(
            "Aplicando la propuesta revisada en Resolve…",
            window,
            cx,
            move || editorial::apply(&proposal),
            |this, outcome, _, cx| match outcome {
                editorial::ApplyOutcome::Applied(record) => {
                    this.conflicts.clear();
                    this.last_application = Some(record);
                    this.notify(
                        Ok("Resolve confirmó la aplicación de la propuesta.".into()),
                        cx,
                    );
                }
                editorial::ApplyOutcome::Conflicts(conflicts) => {
                    let count = conflicts.len();
                    this.conflicts = conflicts;
                    this.notify(
                        Err(format!(
                            "Se detectaron {count} colisión(es) en las pistas de DaVinci Flow. Usa «Limpiar pistas DF» o mueve los clips ajenos."
                        )),
                        cx,
                    );
                }
            },
        );
    }

    pub(super) fn clean_df_tracks(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if self.busy {
            return;
        }
        let receiver = window.prompt(
            PromptLevel::Warning,
            "Limpiar pistas de DaVinci Flow",
            Some(
                "¿Deseas eliminar los clips de las pistas DF_CONTEXT, DF_MAIN, DF_ACCENT y DF_SFX en la línea de tiempo activa? Las pistas del usuario permanecerán intactas.",
            ),
            &[
                PromptButton::Cancel("Cancelar".into()),
                PromptButton::Ok("Limpiar pistas DF".into()),
            ],
            cx,
        );
        cx.spawn_in(window, async move |this, cx| {
            if receiver.await.ok() == Some(1) {
                let _ = this.update_in(cx, |this, window, cx| {
                    this.work(
                        "Limpiando pistas DF en Resolve…",
                        window,
                        cx,
                        editorial::clean_tracks,
                        |this, deleted, _, cx| {
                            this.conflicts.clear();
                            this.notify(
                                Ok(format!(
                                    "Pistas DF limpiadas en Resolve: {deleted} clips eliminados."
                                )),
                                cx,
                            );
                        },
                    );
                });
            }
        })
        .detach();
    }

    pub(super) fn undo_application(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.work(
            "Deshaciendo la última ejecución registrada…",
            window,
            cx,
            editorial::undo,
            |this, _, _, cx| {
                this.last_application = None;
                this.conflicts.clear();
                this.notify(
                    Ok("Resolve confirmó la reversión de la última ejecución.".into()),
                    cx,
                );
            },
        );
    }
}
