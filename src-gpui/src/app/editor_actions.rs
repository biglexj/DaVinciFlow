use super::*;

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
    fn sync_review(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if let Some(d) = self
            .proposal
            .as_ref()
            .and_then(|p| p.decisions.get(self.review_selected))
        {
            let (context, main, accent, note) = (
                d.context.clone(),
                d.main.clone(),
                d.accent.clone(),
                d.edit_note.clone(),
            );
            self.review_enabled = d.enabled;
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
    pub(super) fn prepare_proposal(
        &mut self,
        ai: bool,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        if self.session.has_draft() || self.review_has_draft(cx) || self.proposal_dirty {
            self.notify(
                Err(
                    "Guarda o descarta la edición pendiente antes de preparar otra propuesta."
                        .into(),
                ),
                cx,
            );
            return;
        }
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
        let library_preferences = self.preferences.clone();
        self.work(
            if ai {
                "Preparando propuesta con IA…"
            } else {
                "Preparando propuesta directa…"
            },
            window,
            cx,
            move || {
                if options.direction.is_empty(){options.direction=services::settings()?.preferences.direction;}
                for (category,_) in library::CATEGORIES {
                    let inventory=library::scan_category(category,&library_preferences.folders_for(category),20_000);
                    options.resources.extend(inventory.resources.iter().filter(|r|library_preferences.is_selected(&r.id)).map(|r|serde_json::json!({"id":r.id,"name":r.name,"category":r.category})));
                }
                let (templates, _) = services::templates()?;
                let proposal = editorial::Proposal::direct(
                    &document,
                    capture.as_ref(),
                    templates,
                    fps,
                    options,
                )?;
                let proposal=if ai {editorial::generate(&proposal)?}else{proposal};
                Ok((proposal,editorial::document_revision(&document)))
            },
            |this, (proposal,input), window, cx| {
                this.proposal = Some(proposal);
                this.proposal_input=input;
                this.proposal_dirty = true;
                this.review_selected = 0;
                this.editor_stage = 2;
                this.sync_review(window, cx);
                this.notify(
                    Ok("Propuesta lista. Revisa los bloques antes de aplicar.".into()),
                    cx,
                );
            },
        );
    }
    pub(super) fn review_save(&mut self, window: &mut Window, cx: &mut Context<Self>) {
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
        decision.templates = self.review_templates.clone();
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
            self.notify(Err("La transcripción cambió después de preparar la propuesta. Prepara una propuesta nueva.".into()),cx);
            return;
        }
        if let Err(e) = proposal.validate(true) {
            self.notify(Err(e), cx);
            return;
        }
        self.work(
            "Aplicando la propuesta revisada en Resolve…",
            window,
            cx,
            move || editorial::apply(&proposal),
            |this, record, _, cx| {
                this.last_application = Some(record);
                this.notify(
                    Ok("Resolve confirmó la aplicación de la propuesta.".into()),
                    cx,
                );
            },
        );
    }
    pub(super) fn undo_application(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.work(
            "Deshaciendo la última ejecución registrada…",
            window,
            cx,
            editorial::undo,
            |this, _, _, cx| {
                this.last_application = None;
                this.notify(
                    Ok("Resolve confirmó la reversión de la última ejecución.".into()),
                    cx,
                );
            },
        );
    }
}
