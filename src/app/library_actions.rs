//! Acciones de biblioteca fuera de la composición de la ventana.
use super::*;

impl FlowApp {
    // --- Biblioteca ---

    pub(super) fn sync_preferences_to_backend(&self, cx: &mut Context<Self>) {
        let folders = self.preferences.folders.clone();
        let selected = self.preferences.selected.clone();
        cx.background_executor()
            .spawn(async move {
                let _ = services::sync_library(&folders, &selected);
            })
            .detach();
    }

    fn apply_library_change(
        &mut self,
        category_changed: Option<&str>,
        done_message: Option<String>,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        let affects_titles = category_changed.is_none() || category_changed == Some("titles");
        let refresh_templates =
            affects_titles && (!self.templates.is_empty() || self.tab == Tab::Catalog);
        if !refresh_templates {
            self.sync_preferences_to_backend(cx);
            self.scan_library(window, cx);
            if let Some(msg) = done_message {
                self.notify(Ok(msg), cx);
            }
            return;
        }
        let folders = self.preferences.folders.clone();
        let selected = self.preferences.selected.clone();
        let active_category = self.library_category.clone();
        let active_folders = self.preferences.folders_for(&active_category);
        self.work(
            "Actualizando biblioteca y catálogo de plantillas…",
            window,
            cx,
            move || {
                services::sync_library(&folders, &selected)?;
                let catalog = services::template_catalog()?;
                let inventory = library::scan_category(&active_category, &active_folders, 2000);
                Ok((catalog, inventory))
            },
            move |this, (catalog, inventory), _, cx| {
                this.templates = catalog.templates;
                this.catalog_diagnostics = catalog.diagnostics;
                this.catalog_presets = catalog.presets;
                if this.catalog_selected.is_empty() {
                    this.catalog_selected = catalog.selected_ids.into_iter().collect();
                }
                if inventory.category == this.library_category {
                    let count = inventory.resources.len();
                    let warnings = inventory.warnings.join(" ");
                    this.library_inventory = inventory;
                    this.filter_library(cx);
                    let msg = done_message.unwrap_or_else(|| {
                        format!(
                            "Plantillas y biblioteca actualizadas ({count} recursos). {warnings}"
                        )
                    });
                    this.notify(Ok(msg), cx);
                } else {
                    let msg = done_message.unwrap_or_else(|| {
                        "Catálogo de plantillas actualizado con las carpetas configuradas.".into()
                    });
                    this.notify(Ok(msg), cx);
                }
            },
        );
    }

    pub(super) fn choose_library_folder(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let category = self.library_category.clone();
        let receiver = cx.prompt_for_paths(PathPromptOptions {
            files: false,
            directories: true,
            multiple: false,
            prompt: Some(format!("Añadir carpeta de {}", library::label(&category)).into()),
        });
        cx.spawn_in(window, async move |this, cx| {
            let selection = receiver.await;
            let _ = this.update_in(cx, |this, window, cx| match selection {
                Ok(Ok(Some(paths))) => {
                    if let Some(path) = paths.into_iter().next() {
                        let mut preferences = this.preferences.clone();
                        let mut folders = preferences.folders_for(&category);
                        if !folders.contains(&path) {
                            folders.push(path);
                            preferences.set_folders(&category, folders);
                        }
                        if let Err(error) = preferences.save() {
                            this.notify(Err(error), cx);
                            return;
                        }
                        this.preferences = preferences;
                        this.apply_library_change(Some(&category), None, window, cx);
                    }
                }
                Ok(Ok(None)) => {}
                _ => this.notify(Err("No se pudo abrir el selector de carpetas.".into()), cx),
            });
        })
        .detach();
    }

    pub(super) fn remove_library_folder(
        &mut self,
        index: usize,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        if self.busy {
            return;
        }
        let mut preferences = self.preferences.clone();
        let mut folders = self.preferences.folders_for(&self.library_category);
        if index >= folders.len() {
            return;
        }
        folders.remove(index);
        let category = self.library_category.clone();
        preferences.set_folders(&category, folders);
        if let Err(error) = preferences.save() {
            self.notify(Err(error), cx);
            return;
        }
        self.preferences = preferences;
        self.apply_library_change(
            Some(&category),
            Some(format!("Carpeta quitada de {}.", library::label(&category))),
            window,
            cx,
        );
    }

    pub(super) fn clear_library_category(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if self.busy {
            return;
        }
        let category = self.library_category.clone();
        let mut preferences = self.preferences.clone();
        preferences.clear_category(&category);
        if let Err(error) = preferences.save() {
            self.notify(Err(error), cx);
            return;
        }
        self.preferences = preferences;
        self.apply_library_change(
            Some(&category),
            Some(format!(
                "Carpetas vaciadas en {}.",
                library::label(&category)
            )),
            window,
            cx,
        );
    }

    pub(super) fn reset_library(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if self.busy {
            return;
        }
        let mut preferences = self.preferences.clone();
        preferences.clear_all();
        if let Err(error) = preferences.save() {
            self.notify(Err(error), cx);
            return;
        }
        self.preferences = preferences;
        self.apply_library_change(
            None,
            Some("Biblioteca restablecida: sin carpetas ni recursos precargados.".into()),
            window,
            cx,
        );
    }

    pub(super) fn select_library_category(
        &mut self,
        category: &str,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        self.prepare_category(category, window, cx);
    }

    pub(super) fn scan_library(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if self.busy {
            self.library_scan_pending = true;
            return;
        }
        self.library_scan_pending = false;
        let category = self.library_category.clone();
        let folders = self.preferences.folders_for(&category);
        if folders.is_empty() {
            self.library_inventory = library::scan_category(&category, &folders, 2000);
            self.filter_library(cx);
            self.notify(
                Ok(format!(
                    "No hay carpetas configuradas para {}.",
                    library::label(&category)
                )),
                cx,
            );
            return;
        }
        self.work(
            "Indexando los nombres de tus recursos…",
            window,
            cx,
            move || Ok(library::scan_category(&category, &folders, 2000)),
            |this, inventory, _, cx| {
                if inventory.category != this.library_category {
                    this.library_scan_pending = true;
                    return;
                }
                let count = inventory.resources.len();
                let warnings = inventory.warnings.join(" ");
                this.library_inventory = inventory;
                this.filter_library(cx);
                this.notify(Ok(format!("{count} recursos indexados. {warnings}")), cx);
            },
        );
    }

    pub(super) fn toggle_resource(&mut self, index: usize, cx: &mut Context<Self>) {
        let Some(resource) = self.library_inventory.resources.get(index) else {
            return;
        };
        let id = resource.id.clone();
        let mut preferences = self.preferences.clone();
        match preferences.toggle_selected(&id) {
            Ok(_) => {
                if let Err(error) = preferences.save() {
                    self.notify(Err(error), cx);
                    return;
                }
                self.preferences = preferences;
                self.sync_preferences_to_backend(cx);
                cx.notify();
            }
            Err(error) => self.notify(Err(error), cx),
        }
    }

    pub(super) fn remove_missing_resources(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let prefs = self.preferences.clone();
        self.work(
            "Comprobando recursos seleccionados en disco…",
            window,
            cx,
            move || {
                let mut available = std::collections::HashSet::new();
                for (category, _) in library::CATEGORIES {
                    let inv =
                        library::scan_category(category, &prefs.folders_for(category), 20_000);
                    for res in inv.resources {
                        available.insert(res.id);
                    }
                }
                Ok(available)
            },
            |this, available, _, cx| {
                let mut preferences = this.preferences.clone();
                let before = preferences.selected.len();
                preferences.selected.retain(|id| available.contains(id));
                let removed = before.saturating_sub(preferences.selected.len());
                if let Err(error) = preferences.save() {
                    this.notify(Err(error), cx);
                    return;
                }
                this.preferences = preferences;
                this.sync_preferences_to_backend(cx);
                this.notify(
                    Ok(format!(
                        "{removed} selección(es) no disponible(s) eliminada(s)."
                    )),
                    cx,
                );
            },
        );
    }
}
