//! Pestañas «Efectos (SFX)» y «Plantillas»: catálogos completos del proyecto.
use super::*;
use gpui_kit::component::Icon;
use gpui_kit::component::checkbox::Checkbox;

const CATALOG_SOURCES: [(&str, &str); 13] = [
    ("all", "Todas"),
    ("davinci_flow", "DaVinci Flow"),
    ("karaoke", "Karaoke"),
    ("native", "✨ Nativos"),
    ("shorts", "📱 Shorts"),
    ("youtube", "🎬 YouTube"),
    ("news", "📰 Noticiero"),
    ("media_pool", "📁 Proyecto"),
    ("installed", "✨ DRFX"),
    ("basic", "Text+ básico"),
    ("animated", "Animadas"),
    ("preview_video", "Con animación"),
    ("preview_image", "Con miniatura"),
];

const STYLE_PACKS: [(&str, &str); 5] = [
    ("native", "✨ Nativos DaVinci"),
    ("shorts", "📱 Shorts Bold"),
    ("youtube", "🎬 YouTube Dinámico"),
    ("news", "📰 Noticiero TV"),
    ("basic", "✏️ Text+ Básico"),
];

/// Etiqueta de origen de una plantilla, como en la interfaz vigente.
fn source_label(template: &services::TemplateInfo) -> &'static str {
    match template.category.as_str() {
        "davinci_flow" => "DaVinci Flow",
        "karaoke" => "DaVinci Flow · Karaoke",
        "shorts" => "📱 Shorts Bold",
        "youtube" => "🎬 YouTube Dinámico",
        "news" => "📰 Noticiero TV",
        _ => {
            if template.locator.contains("basic_titles") || template.category == "basic" {
                "Text+ básico"
            } else {
                match template.source.as_str() {
                    "media_pool" => "📁 Proyecto · Media Pool",
                    "installed_bin" => "Referencia animada",
                    "installed_archive" => "✨ DRFX Instalado",
                    _ => "Instalado / archivo",
                }
            }
        }
    }
}

fn template_matches_source(template: &services::TemplateInfo, source: &str) -> bool {
    let cat = template.category.as_str();
    let loc_lower = template.locator.to_lowercase();
    let name_lower = template.name.to_lowercase();
    match source {
        "all" => true,
        "davinci_flow" | "karaoke" => cat == source,
        "preview_video" => template.preview_kind == "video",
        "preview_image" => template.preview_kind == "image",
        "animated" => cat == "animated",
        "native" => {
            cat == "native" || template.source == "native" || loc_lower.contains("templates.drfx")
        }
        "shorts" => cat == "shorts" || name_lower.contains("short"),
        "youtube" => cat == "youtube" || name_lower.contains("youtube"),
        "news" => cat == "news" || name_lower.contains("noticiero"),
        "media_pool" => template.source == "media_pool",
        "basic" => cat == "basic" || template.locator.contains("basic_titles"),
        "installed" => {
            template.source != "media_pool" && !template.locator.contains("basic_titles")
        }
        _ => true,
    }
}

#[derive(Clone)]
struct SfxRowItem {
    id: String,
    name: String,
    category: String,
    subpath: String,
    full_path: Option<PathBuf>,
    duration: Option<f64>,
    gain_db: Option<f64>,
}

fn empty_catalog_card(icon: IconName, title: Option<&'static str>, msg: &'static str) -> Div {
    let mut box_card = card()
        .w_full()
        .flex_1()
        .min_h_0()
        .items_center()
        .justify_center()
        .gap(px(10.))
        .p(px(36.))
        .child(Icon::new(icon).size(px(32.)).text_color(rgb(ACCENT)));
    if let Some(heading) = title {
        box_card = box_card.child(
            div()
                .text_size(px(17.))
                .font_weight(FontWeight::MEDIUM)
                .child(heading),
        );
    }
    box_card.child(label(msg))
}

fn catalog_list_frame(child: impl IntoElement) -> Div {
    column()
        .w_full()
        .flex_1()
        .min_h_0()
        .bg(rgb(CARD))
        .rounded(px(10.))
        .overflow_hidden()
        .child(div().w_full().flex_1().min_h_0().child(child))
}

impl FlowApp {
    pub fn sfx_view(&self, cx: &mut Context<Self>) -> Div {
        let query = self.sfx_query.read(cx).value().trim().to_lowercase();
        let selected_cat = self.sfx_category.as_str();

        let mut all_items: Vec<SfxRowItem> = Vec::new();
        let mut categories: BTreeSet<String> = BTreeSet::new();

        if self.library_inventory.category == "sfx" {
            for res in &self.library_inventory.resources {
                let cat = res
                    .name
                    .split(['/', '\\'])
                    .next()
                    .filter(|part| *part != res.name)
                    .unwrap_or("General")
                    .to_string();
                categories.insert(cat.clone());
                all_items.push(SfxRowItem {
                    id: res.id.clone(),
                    name: res.name.clone(),
                    category: cat,
                    subpath: res.path.to_string_lossy().into_owned(),
                    full_path: Some(res.path.clone()),
                    duration: None,
                    gain_db: None,
                });
            }
        }
        for asset in &self.sfx_assets {
            let cat = format!("Procedural ({})", asset.category);
            categories.insert(cat.clone());
            all_items.push(SfxRowItem {
                id: asset.id.clone(),
                name: asset.name.clone(),
                category: cat,
                subpath: asset.id.clone(),
                full_path: None,
                duration: Some(asset.duration_seconds),
                gain_db: Some(asset.recommended_gain_db),
            });
        }

        let filtered: Vec<SfxRowItem> = all_items
            .into_iter()
            .filter(|item| {
                (selected_cat == "all" || item.category == selected_cat)
                    && (query.is_empty()
                        || item.name.to_lowercase().contains(&query)
                        || item.subpath.to_lowercase().contains(&query))
            })
            .collect();

        let total = filtered.len();
        let page_size = 48usize;
        let offset = self
            .sfx_offset
            .min(total.saturating_sub(1) / page_size * page_size);
        let page_items: Vec<SfxRowItem> =
            filtered.into_iter().skip(offset).take(page_size).collect();
        let pages = (total + page_size - 1).max(1) / page_size;
        let current_page = offset / page_size + 1;

        let now_playing = self
            .playing_sound
            .as_ref()
            .and_then(|p| p.file_name())
            .map(|n| format!("▶ {}", n.to_string_lossy()))
            .unwrap_or_else(|| "Ningún sonido en reproducción".into());

        let cat_btn = |active: bool, id: String, lbl: String| {
            if active {
                accent_button(id, lbl, false)
            } else {
                button(id, lbl, false)
            }
        };
        let mut cat_row = row().gap(px(6.)).child(
            cat_btn(
                selected_cat == "all",
                "sfx-cat-all".into(),
                if selected_cat == "all" {
                    format!("Todos ({total})")
                } else {
                    "Todos".into()
                },
            )
            .on_click(cx.listener(|this, _, _, cx| {
                this.sfx_category = "all".into();
                this.sfx_offset = 0;
                cx.notify();
            })),
        );
        for cat in categories.into_iter().take(6) {
            let cat_val = cat.clone();
            let btn = cat_btn(selected_cat == cat, format!("sfx-cat-{cat}"), cat);
            cat_row = cat_row.child(btn.on_click(cx.listener(move |this, _, _, cx| {
                this.sfx_category = cat_val.clone();
                this.sfx_offset = 0;
                cx.notify();
            })));
        }

        let sfx_field = |w: f32, lbl: &'static str, state: &Entity<InputState>| {
            column()
                .w(px(w))
                .gap(px(4.))
                .child(field_label(lbl))
                .child(Input::new(state))
        };
        let view =
            column()
                .size_full()
                .min_h_0()
                .gap(px(8.))
                .child(
                    card()
                        .gap(px(8.))
                        .child(
                            row()
                                .justify_between()
                                .child(
                                    row()
                                        .gap(px(8.))
                                        .child(
                                            Icon::new(IconName::AudioLines)
                                                .size(px(18.))
                                                .text_color(rgb(ACCENT)),
                                        )
                                        .child(section("Ajustes de inyección sonora en Resolve:")),
                                )
                                .child(label(now_playing)),
                        )
                        .child(
                            row()
                                .gap(px(10.))
                                .items_end()
                                .child(sfx_field(110., "Pista SFX", &self.sfx_track_name))
                                .child(sfx_field(
                                    130.,
                                    "Anticipación (frames)",
                                    &self.sfx_anticipation,
                                ))
                                .child(
                                    button("sfx-go-lib", "Ir a Biblioteca SFX", self.busy)
                                        .on_click(cx.listener(|this, _, window, cx| {
                                            this.prepare_category("sfx", window, cx);
                                            this.load_for_tab(Tab::Library, window, cx);
                                        })),
                                )
                                .child(
                                    button("sfx-reindex", "Reindexar carpeta", self.busy).on_click(
                                        cx.listener(|this, _, window, cx| {
                                            this.prepare_category("sfx", window, cx);
                                            this.load_sfx_catalog(window, cx);
                                        }),
                                    ),
                                )
                                .when(self.playing_sound.is_some(), |r| {
                                    r.child(button("sfx-stop", "Detener audio", false).on_click(
                                        cx.listener(|this, _, _, cx| this.stop_audio(cx)),
                                    ))
                                }),
                        ),
                )
                .child(
                    row()
                        .gap(px(8.))
                        .child(div().flex_1().child(Input::new(&self.sfx_query)))
                        .child(cat_row),
                )
                .child(
                    row()
                        .justify_between()
                        .child(label(format!(
                            "{total} sonidos encontrados · página {current_page}/{pages}"
                        )))
                        .child(
                            row()
                                .gap(px(6.))
                                .child(button("sfx-prev", "◀ Anterior", offset == 0).on_click(
                                    cx.listener(move |this, _, _, cx| {
                                        this.sfx_offset = offset.saturating_sub(page_size);
                                        cx.notify();
                                    }),
                                ))
                                .child(
                                    button("sfx-next", "Siguiente ▶", offset + page_size >= total)
                                        .on_click(cx.listener(move |this, _, _, cx| {
                                            this.sfx_offset = offset + page_size;
                                            cx.notify();
                                        })),
                                ),
                        ),
                );

        if page_items.is_empty() {
            return view.child(empty_catalog_card(
                IconName::AudioLines,
                None,
                "No se encontraron efectos para este filtro.",
            ));
        }

        let entity = cx.entity().downgrade();
        let sfx_queue: Vec<davinci_flow_gpui::audio_player::AudioTrack> = page_items
            .iter()
            .filter_map(|item| {
                item.full_path
                    .as_ref()
                    .map(|p| davinci_flow_gpui::audio_player::AudioTrack {
                        path: p.clone(),
                        title: item.name.clone(),
                        kind: "SFX".into(),
                        is_video: false,
                    })
            })
            .collect();
        let rows = uniform_list("sfx-list", page_items.len(), move |range, _, cx| {
            let Some(entity) = entity.upgrade() else {
                return vec![];
            };
            let this = entity.read(cx);
            let is_paused =
                this.player_state.status == davinci_flow_gpui::audio_player::PlaybackStatus::Paused;
            let active_track = this.player_state.current.as_ref().map(|c| c.path.clone());
            range
                .filter_map(|index| page_items.get(index))
                .map(|item| {
                    let weak = entity.downgrade();
                    let weak_copy = entity.downgrade();
                    let id = item.id.clone();
                    let full_path = item.full_path.clone();
                    let import_source = item.full_path.clone();
                    let copy_val = item.subpath.clone();
                    let item_name = item.name.clone();
                    let queue_clone = sfx_queue.clone();
                    let is_playing = full_path
                        .as_ref()
                        .is_some_and(|p| this.playing_sound.as_ref() == Some(p));
                    let is_this_paused = full_path
                        .as_ref()
                        .is_some_and(|p| active_track.as_ref() == Some(p) && is_paused);
                    let (btn_icon, btn_label) = if is_playing {
                        (IconName::Pause, "Pausar")
                    } else if is_this_paused {
                        (IconName::Play, "Reanudar")
                    } else {
                        (IconName::Play, "Reproducir")
                    };
                    let play_btn = fixed_media_button(
                        ElementId::Name(format!("sfx-play-{}", item.id).into()),
                        btn_icon,
                        btn_label,
                        is_playing,
                        this.busy,
                        118.0,
                    );
                    let play_btn = if this.busy {
                        play_btn
                    } else {
                        play_btn.on_click(move |_, window, cx| {
                            if let Some(entity) = weak.upgrade() {
                                entity.update(cx, |this, cx| {
                                    if let Some(path) = &full_path {
                                        let queue_pos =
                                            queue_clone.iter().position(|t| t.path == *path);
                                        let track = davinci_flow_gpui::audio_player::AudioTrack {
                                            path: path.clone(),
                                            title: item_name.clone(),
                                            kind: "SFX".into(),
                                            is_video: false,
                                        };
                                        let queue = if queue_clone.is_empty() {
                                            vec![track.clone()]
                                        } else {
                                            queue_clone.clone()
                                        };
                                        this.play_media_with_queue(
                                            Tab::Sfx,
                                            track,
                                            queue,
                                            queue_pos.or(Some(0)),
                                            false,
                                            window,
                                            cx,
                                        );
                                    } else {
                                        this.play_sfx(id.clone(), window, cx);
                                    }
                                });
                            }
                        })
                    };
                    let p = palette();
                    let meta = |w: f32, val: String| {
                        div()
                            .w(px(w))
                            .text_size(px(11.))
                            .text_color(rgb(MUTED))
                            .child(val)
                    };
                    row()
                        .w_full()
                        .h(px(46.))
                        .px(px(14.))
                        .gap(px(10.))
                        .border_b_1()
                        .border_color(rgb(p.line))
                        .bg(rgb(if is_playing || is_this_paused {
                            p.active
                        } else {
                            p.card
                        }))
                        .child(
                            div()
                                .flex_1()
                                .min_w_0()
                                .text_ellipsis()
                                .child(item.name.clone()),
                        )
                        .child(chip(item.category.clone(), is_playing))
                        .when_some(item.duration, |r, d| {
                            r.child(meta(64., format!("{d:.2} s")))
                        })
                        .when_some(item.gain_db, |r, g| {
                            r.child(meta(60., format!("{g:.0} dB")))
                        })
                        .child(play_btn)
                        .when_some(import_source, |r, import_path| {
                            let weak_import = entity.downgrade();
                            let import_id = item.id.clone();
                            r.child(
                                button(
                                    ElementId::Name(format!("sfx-import-{import_id}").into()),
                                    "Importar",
                                    this.busy,
                                )
                                .on_click(move |_, window, cx| {
                                    if let Some(entity) = weak_import.upgrade() {
                                        entity.update(cx, |this, cx| {
                                            this.import_file(import_path.clone(), window, cx)
                                        });
                                    }
                                }),
                            )
                        })
                        .child(
                            button(
                                ElementId::Name(format!("sfx-copy-{}", item.id).into()),
                                "Copiar ruta",
                                false,
                            )
                            .on_click(move |_, _, cx| {
                                cx.write_to_clipboard(ClipboardItem::new_string(copy_val.clone()));
                                if let Some(entity) = weak_copy.upgrade() {
                                    entity.update(cx, |this, cx| {
                                        this.notify(Ok("Ruta copiada al portapapeles.".into()), cx)
                                    });
                                }
                            }),
                        )
                })
                .collect::<Vec<_>>()
        });
        view.child(catalog_list_frame(rows.h_full()))
            .child(self.player_bar_for_tab(Tab::Sfx, cx))
    }

    pub fn catalog_view(&self, cx: &mut Context<Self>) -> Div {
        let query = self.catalog_query.read(cx).value().trim().to_lowercase();
        let source = self.catalog_source.as_str();

        let filtered: Vec<services::TemplateInfo> = self
            .templates
            .iter()
            .filter(|t| {
                let q_ok = query.is_empty()
                    || t.name.to_lowercase().contains(&query)
                    || t.locator.to_lowercase().contains(&query)
                    || t.category.to_lowercase().contains(&query);
                q_ok && template_matches_source(t, source)
            })
            .cloned()
            .collect();

        let total = filtered.len();
        let page_size = 60usize;
        let offset = self
            .catalog_offset
            .min(total.saturating_sub(1) / page_size * page_size);
        let visible: Vec<services::TemplateInfo> =
            filtered.into_iter().skip(offset).take(page_size).collect();
        let current_page = offset / page_size + 1;
        let pages = (total + page_size - 1).max(1) / page_size;

        let mut view =
            column()
                .size_full()
                .min_h_0()
                .gap(px(8.))
                .child(
                    card()
                        .w_full()
                        .gap(px(8.))
                        .child(
                            row()
                                .w_full()
                                .justify_between()
                                .gap(px(8.))
                                .child(
                                    row()
                                        .gap(px(6.))
                                        .child(
                                            button("cat-installed", "Leer instalados", self.busy)
                                                .on_click(cx.listener(|this, _, window, cx| {
                                                    this.load_templates(window, cx)
                                                })),
                                        )
                                        .child(
                                            button("cat-project", "Leer proyecto", self.busy)
                                                .on_click(cx.listener(|this, _, window, cx| {
                                                    this.load_project_templates(window, cx)
                                                })),
                                        )
                                        .child(
                                            button("cat-folder", "Añadir carpeta", self.busy)
                                                .on_click(cx.listener(|this, _, window, cx| {
                                                    this.prepare_category("titles", window, cx);
                                                    this.choose_library_folder(window, cx);
                                                })),
                                        ),
                                )
                                .child(row().gap(px(6.)).children(STYLE_PACKS.iter().map(
                                    |(pack, label)| {
                                        let pack = *pack;
                                        button(format!("pack-{pack}"), *label, self.busy).on_click(
                                            cx.listener(move |this, _, window, cx| {
                                                this.apply_catalog_pack(pack, window, cx)
                                            }),
                                        )
                                    },
                                ))),
                        )
                        .child(
                            row()
                                .w_full()
                                .gap(px(8.))
                                .child(div().flex_1().child(Input::new(&self.catalog_query))),
                        )
                        .child(row().w_full().gap(px(6.)).children(
                            CATALOG_SOURCES.iter().take(9).map(|(key, lbl)| {
                                let active = source == *key;
                                let key = *key;
                                let btn = if active {
                                    accent_button(format!("src-{key}"), *lbl, false)
                                } else {
                                    button(format!("src-{key}"), *lbl, false)
                                };
                                div()
                                    .flex_1()
                                    .min_w_0()
                                    .flex()
                                    .flex_col()
                                    .child(btn.on_click(cx.listener(move |this, _, _, cx| {
                                        this.catalog_source = key.into();
                                        this.catalog_offset = 0;
                                        cx.notify();
                                    })))
                            }),
                        )),
                )
                .child(
                    row()
                        .w_full()
                        .items_start()
                        .gap(px(10.))
                        .child(
                            card()
                                .flex_1()
                                .min_w_0()
                                .gap(px(8.))
                                .child(section("Mis presets de plantillas"))
                                .child(
                                    row()
                                        .w_full()
                                        .gap(px(6.))
                                        .when(!self.catalog_presets.is_empty(), |r| {
                                            r.children(self.catalog_presets.iter().take(4).map(
                                                |preset| {
                                                    let p_name = preset.clone();
                                                    button(
                                                        format!("preset-use-{p_name}"),
                                                        p_name.clone(),
                                                        self.busy,
                                                    )
                                                    .on_click(cx.listener(
                                                        move |this, _, window, cx| {
                                                            this.use_catalog_preset(
                                                                p_name.clone(),
                                                                window,
                                                                cx,
                                                            )
                                                        },
                                                    ))
                                                },
                                            ))
                                        })
                                        .child(
                                            div()
                                                .flex_1()
                                                .min_w_0()
                                                .child(Input::new(&self.catalog_preset_name)),
                                        )
                                        .child(
                                            button("save-preset", "Guardar selección", self.busy)
                                                .on_click(cx.listener(|this, _, window, cx| {
                                                    this.save_catalog_preset(window, cx)
                                                })),
                                        ),
                                ),
                        )
                        .child(
                            card()
                                .flex_1()
                                .min_w_0()
                                .gap(px(8.))
                                .child(section("Nodo de texto personalizado (.setting)"))
                                .child(
                                    row()
                                        .w_full()
                                        .gap(px(8.))
                                        .child(
                                            div()
                                                .flex_1()
                                                .min_w_0()
                                                .child(Input::new(&self.catalog_node_name)),
                                        )
                                        .child(
                                            div()
                                                .flex_1()
                                                .min_w_0()
                                                .child(Input::new(&self.catalog_node_input)),
                                        )
                                        .child(
                                            button("assign-node", "Asignar nodo", self.busy)
                                                .on_click(cx.listener(|this, _, window, cx| {
                                                    this.assign_catalog_node(window, cx)
                                                })),
                                        ),
                                ),
                        ),
                )
                .child(
                    row()
                        .w_full()
                        .justify_between()
                        .child(label(format!(
                            "{total} encontradas · {} elegidas · página {current_page}/{pages}",
                            self.catalog_selected.len()
                        )))
                        .child(
                            row()
                                .gap(px(6.))
                                .child(button("cat-prev", "◀ Anterior", offset == 0).on_click(
                                    cx.listener(move |this, _, _, cx| {
                                        this.catalog_offset = offset.saturating_sub(page_size);
                                        cx.notify();
                                    }),
                                ))
                                .child(
                                    button("cat-next", "Siguiente ▶", offset + page_size >= total)
                                        .on_click(cx.listener(move |this, _, _, cx| {
                                            this.catalog_offset = offset + page_size;
                                            cx.notify();
                                        })),
                                )
                                .child(
                                    button(
                                        "cat-clear",
                                        "Quitar selección",
                                        self.catalog_selected.is_empty(),
                                    )
                                    .on_click(cx.listener(
                                        |this, _, _, cx| {
                                            this.catalog_selected.clear();
                                            cx.notify();
                                        },
                                    )),
                                ),
                        ),
                );

        if !self.catalog_diagnostics.is_empty() {
            view = view.child(label(self.catalog_diagnostics.join(" ")));
        }
        if visible.is_empty() {
            return view.child(empty_catalog_card(
                IconName::Type,
                Some("Catálogo de plantillas"),
                "No hay plantillas para este filtro.",
            ));
        }

        let entity = cx.entity().downgrade();
        let rows = uniform_list("catalog-list", visible.len(), move |range, _, cx| {
            let Some(entity) = entity.upgrade() else {
                return vec![];
            };
            let this = entity.read(cx);
            range
                .filter_map(|index| visible.get(index))
                .map(|template| {
                    let id = template.id.clone();
                    let selected = this.catalog_selected.contains(&id);
                    let weak_toggle = entity.downgrade();
                    let weak_preview = entity.downgrade();
                    let tpl_clone = template.clone();
                    row()
                        .w_full()
                        .h(px(50.))
                        .px(px(14.))
                        .gap(px(12.))
                        .border_b_1()
                        .border_color(rgb(LINE))
                        .bg(rgb(if selected { ACTIVE } else { CARD }))
                        .child(
                            Checkbox::new(ElementId::Name(format!("cat-check-{id}").into()))
                                .checked(selected)
                                .on_click(move |_, _, cx| {
                                    if let Some(entity) = weak_toggle.upgrade() {
                                        entity.update(cx, |this, cx| {
                                            if this.catalog_selected.contains(&id) {
                                                this.catalog_selected.remove(&id);
                                            } else if this.catalog_selected.len() < 60 {
                                                this.catalog_selected.insert(id.clone());
                                            } else {
                                                this.notify(
                                                    Err("Elige hasta 60 plantillas.".into()),
                                                    cx,
                                                );
                                                return;
                                            }
                                            cx.notify();
                                        });
                                    }
                                }),
                        )
                        .child(
                            div()
                                .flex_1()
                                .min_w_0()
                                .font_weight(FontWeight::MEDIUM)
                                .text_ellipsis()
                                .child(template.name.clone()),
                        )
                        .child(chip(source_label(template), selected))
                        .child(
                            div()
                                .flex_1()
                                .min_w_0()
                                .text_size(px(11.))
                                .text_color(rgb(MUTED))
                                .text_ellipsis()
                                .child(template.locator.clone()),
                        )
                        .child(
                            button(
                                ElementId::Name(format!("cat-preview-{}", template.id).into()),
                                "Ver diseño",
                                this.busy,
                            )
                            .on_click(move |_, window, cx| {
                                if let Some(entity) = weak_preview.upgrade() {
                                    entity.update(cx, |this, cx| {
                                        this.preview_catalog_template(
                                            tpl_clone.clone(),
                                            window,
                                            cx,
                                        );
                                    });
                                }
                            }),
                        )
                })
                .collect::<Vec<_>>()
        });
        view.child(catalog_list_frame(rows.h_full()))
    }

    pub fn catalog_preview_overlay(
        &self,
        title: &str,
        preview: &services::TemplatePreview,
        cx: &mut Context<Self>,
    ) -> Div {
        let p = palette();
        let mut modal = card().w(px(640.)).overflow_hidden().gap(px(10.)).child(
            row()
                .w_full()
                .min_w_0()
                .gap(px(10.))
                .justify_between()
                .child(
                    div()
                        .flex_1()
                        .min_w_0()
                        .overflow_hidden()
                        .whitespace_nowrap()
                        .text_ellipsis()
                        .text_size(px(13.))
                        .font_weight(FontWeight::SEMIBOLD)
                        .text_color(rgb(p.text))
                        .child(title.to_string()),
                )
                .child(div().flex_shrink_0().child(
                    button("close-cat-preview", "Cerrar", false).on_click(cx.listener(
                        |this, _, _, cx| {
                            this.catalog_preview = None;
                            cx.notify();
                        },
                    )),
                )),
        );
        if !preview.image.is_empty() {
            modal = modal
                .child(
                    img(PathBuf::from(&preview.image))
                        .w_full()
                        .h(px(340.))
                        .object_fit(ObjectFit::Contain),
                )
                .child(label("Captura real del diseño de la plantilla."));
        } else if !preview.video.is_empty() {
            let video_path = PathBuf::from(&preview.video);
            let title_owned = title.to_string();
            modal = modal
                .child(label(
                    "Esta plantilla incluye una muestra de animación en vídeo.",
                ))
                .child(
                    accent_button("open-cat-video", "Reproducir animación", false).on_click(
                        cx.listener(move |this, _, window, cx| {
                            this.catalog_preview = None;
                            let track = davinci_flow_gpui::audio_player::AudioTrack {
                                path: video_path.clone(),
                                title: title_owned.clone(),
                                kind: "Plantilla".into(),
                                is_video: true,
                            };
                            this.play_media_with_queue(
                                Tab::Catalog,
                                track.clone(),
                                vec![track],
                                Some(0),
                                true,
                                window,
                                cx,
                            );
                        }),
                    ),
                );
        } else {
            modal = modal.child(label(
                "Esta plantilla no incluye vista previa pregenerada. Puedes comprobar su diseño directamente en DaVinci Resolve.",
            ));
        }
        div()
            .absolute()
            .inset_0()
            .flex()
            .items_center()
            .justify_center()
            .bg(rgba(0x00000099))
            .child(modal)
    }
}
