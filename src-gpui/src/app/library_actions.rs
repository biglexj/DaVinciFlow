//! Acciones de biblioteca fuera de la composición de la ventana.
use super::*;

impl FlowApp {
    // --- Biblioteca ---

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
                        this.scan_library(window, cx);
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
        preferences.set_folders(&self.library_category, folders.clone());
        if let Err(error) = preferences.save() {
            self.notify(Err(error), cx);
            return;
        }
        self.preferences = preferences;
        self.scan_library(window, cx);
        self.notify(
            Ok(format!(
                "Carpeta quitada de {}.",
                library::label(&self.library_category)
            )),
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
                cx.notify();
            }
            Err(error) => self.notify(Err(error), cx),
        }
    }
}
