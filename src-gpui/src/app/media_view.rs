//! Pestañas «B-Rolls» y «Música»: recursos locales con paginación, preescucha y vista previa.
use super::*;

const PAGE_SIZE: usize = 48;

impl FlowApp {
    fn media_rows(&self, page_indices: Vec<usize>, cx: &mut Context<Self>) -> impl IntoElement {
        let entity = cx.entity().downgrade();
        let media_queue: Vec<davinci_flow_gpui::audio_player::AudioTrack> = page_indices
            .iter()
            .filter_map(|&idx| self.library_inventory.resources.get(idx))
            .filter(|res| {
                res.category == "music"
                    || res.category == "sfx"
                    || davinci_flow_gpui::video_player::is_video_path(&res.path)
            })
            .map(|res| {
                let is_video = davinci_flow_gpui::video_player::is_video_path(&res.path);
                davinci_flow_gpui::audio_player::AudioTrack {
                    path: res.path.clone(),
                    title: res.name.clone(),
                    kind: if is_video {
                        "Vídeo"
                    } else if res.category == "sfx" {
                        "SFX"
                    } else {
                        "Música"
                    }
                    .into(),
                    is_video,
                }
            })
            .collect();
        uniform_list(
            "media-resources",
            page_indices.len(),
            move |range, _, cx| {
                let Some(entity) = entity.upgrade() else {
                    return vec![];
                };
                let this = entity.read(cx);
                let active_track = this.player_state.current.as_ref().map(|c| c.path.clone());
                let is_paused = this.player_state.status
                    == davinci_flow_gpui::audio_player::PlaybackStatus::Paused;
                range
                    .filter_map(|position| page_indices.get(position).copied())
                    .map(|index| {
                        let resource = &this.library_inventory.resources[index];
                        let selected = this.preferences.is_selected(&resource.id);
                        let weak = entity.downgrade();
                        let preview = entity.downgrade();
                        let import_ent = entity.downgrade();
                        let path = resource.path.clone();
                        let import_path = resource.path.clone();
                        let is_video = davinci_flow_gpui::video_player::is_video_path(&path);
                        let playable =
                            resource.category == "music" || resource.category == "sfx" || is_video;
                        let is_playing = this.playing_sound.as_ref() == Some(&path);
                        let is_this_paused = active_track.as_ref() == Some(&path) && is_paused;
                        let queue_for_click = media_queue.clone();
                        let queue_pos = queue_for_click.iter().position(|t| t.path == path);
                        let origin_tab = if resource.category == "visuals" {
                            Tab::Brolls
                        } else if resource.category == "sfx" {
                            Tab::Sfx
                        } else {
                            Tab::Music
                        };
                        let track_for_click = davinci_flow_gpui::audio_player::AudioTrack {
                            path: path.clone(),
                            title: resource.name.clone(),
                            kind: if is_video {
                                "Vídeo"
                            } else if resource.category == "sfx" {
                                "SFX"
                            } else {
                                "Música"
                            }
                            .into(),
                            is_video,
                        };
                        let ext = resource
                            .path
                            .extension()
                            .and_then(|s| s.to_str())
                            .unwrap_or_default()
                            .to_ascii_uppercase();
                        let (btn_icon, btn_text) = if playable {
                            if is_playing {
                                (IconName::Pause, "Pausar")
                            } else if is_this_paused {
                                (IconName::Play, "Reanudar")
                            } else {
                                (IconName::Play, "Reproducir")
                            }
                        } else {
                            (IconName::Eye, "Ver imagen")
                        };
                        let action_btn = fixed_media_button(
                            ("preview", index),
                            btn_icon,
                            btn_text,
                            is_playing,
                            this.busy,
                            118.0,
                        );
                        let action_btn = if this.busy {
                            action_btn
                        } else {
                            action_btn.on_click(move |_, window, cx| {
                                if let Some(entity) = preview.upgrade() {
                                    entity.update(cx, |this, cx| {
                                        if playable {
                                            let queue = if queue_for_click.is_empty() {
                                                vec![track_for_click.clone()]
                                            } else {
                                                queue_for_click.clone()
                                            };
                                            this.play_media_with_queue(
                                                origin_tab,
                                                track_for_click.clone(),
                                                queue,
                                                queue_pos.or(Some(0)),
                                                false,
                                                window,
                                                cx,
                                            );
                                        } else {
                                            this.preview_media(path.clone(), window, cx);
                                        }
                                    });
                                }
                            })
                        };
                        let p = palette();
                        row()
                            .w_full()
                            .h(px(52.))
                            .px(px(12.))
                            .gap(px(10.))
                            .border_b_1()
                            .border_color(rgb(p.line))
                            .bg(rgb(if is_playing || is_this_paused || selected {
                                p.active
                            } else {
                                p.card
                            }))
                            .child(chip(ext, selected))
                            .child(
                                div()
                                    .flex_1()
                                    .min_w_0()
                                    .child(div().text_ellipsis().child(resource.name.clone()))
                                    .child(label(format!(
                                        "{:.1} MB",
                                        resource.bytes as f64 / 1_048_576.
                                    ))),
                            )
                            .child(
                                button(
                                    ("share", index),
                                    if selected { "✓ IA" } else { "IA" },
                                    this.busy,
                                )
                                .on_click(move |_, _, cx| {
                                    if let Some(entity) = weak.upgrade() {
                                        entity
                                            .update(cx, |this, cx| this.toggle_resource(index, cx));
                                    }
                                }),
                            )
                            .child(action_btn)
                            .child(
                                button(("import-med", index), "Importar", this.busy).on_click(
                                    move |_, window, cx| {
                                        if let Some(entity) = import_ent.upgrade() {
                                            entity.update(cx, |this, cx| {
                                                this.import_file(import_path.clone(), window, cx)
                                            });
                                        }
                                    },
                                ),
                            )
                    })
                    .collect::<Vec<_>>()
            },
        )
        .h_full()
    }

    pub fn media_view(&self, category: &'static str, cx: &mut Context<Self>) -> Div {
        if self.library_inventory.category != category {
            return column()
                .size_full()
                .child(label("Preparando la categoría de recursos…"));
        }
        let total = self.library_filtered.len();
        let offset = self
            .media_offset
            .min(total.saturating_sub(1) / PAGE_SIZE * PAGE_SIZE);
        let page_indices: Vec<usize> = self
            .library_filtered
            .iter()
            .copied()
            .skip(offset)
            .take(PAGE_SIZE)
            .collect();
        let pages = (total + PAGE_SIZE - 1).max(1) / PAGE_SIZE;
        let current_page = offset / PAGE_SIZE + 1;

        let list_card = if page_indices.is_empty() {
            card()
                .flex_1()
                .min_w_0()
                .h_full()
                .min_h_0()
                .items_center()
                .justify_center()
                .gap(px(8.))
                .child(section(if category == "visuals" {
                    "Sin B-Rolls indexados en este filtro"
                } else {
                    "Sin pistas de música en este filtro"
                }))
                .child(label(
                    "Añade una carpeta o pulsa «Reindexar» para explorar tus recursos locales.",
                ))
        } else {
            card()
                .flex_1()
                .min_w_0()
                .h_full()
                .min_h_0()
                .p_0()
                .overflow_hidden()
                .child(self.media_rows(page_indices, cx))
        };

        let mut body = row()
            .w_full()
            .flex_1()
            .min_h_0()
            .items_start()
            .gap(px(12.))
            .child(list_card);
        if category == "visuals" {
            let active_video = self
                .player_state
                .current
                .as_ref()
                .filter(|t| t.is_video && self.player_origin == Some(Tab::Brolls));
            let mut preview = card().w(px(400.)).flex_shrink_0().gap(px(10.)).child(
                row()
                    .w_full()
                    .justify_between()
                    .child(section("Vista previa"))
                    .when(active_video.is_some(), |r| {
                        r.child(chip("Vídeo en vivo", true))
                    }),
            );
            if let Some(frame) = &self.video_frame
                && active_video.is_some()
            {
                preview = preview.child(
                    div()
                        .w_full()
                        .h(px(225.))
                        .rounded(px(6.))
                        .bg(rgb(0x0B0E10))
                        .border_1()
                        .border_color(rgb(LINE))
                        .overflow_hidden()
                        .child(
                            img(frame.clone())
                                .w_full()
                                .h(px(225.))
                                .object_fit(ObjectFit::Contain),
                        ),
                );
            } else if active_video.is_some() {
                preview = preview.child(
                    div()
                        .w_full()
                        .h(px(225.))
                        .rounded(px(6.))
                        .bg(rgb(0x0B0E10))
                        .border_1()
                        .border_color(rgb(LINE))
                        .flex()
                        .items_center()
                        .justify_center()
                        .child(label("Cargando fotogramas del vídeo…")),
                );
            } else if let Some(path) = &self.media_preview {
                preview = preview.child(
                    img(path.clone())
                        .w_full()
                        .h(px(225.))
                        .object_fit(ObjectFit::Contain),
                );
            } else {
                preview = preview.child(
                    div()
                        .w_full()
                        .h(px(225.))
                        .rounded(px(6.))
                        .bg(rgb(FIELD))
                        .border_1()
                        .border_color(rgb(LINE))
                        .flex()
                        .items_center()
                        .justify_center()
                        .child(label("Pulsa «Reproducir» en un vídeo o «Ver imagen»")),
                );
            }
            if let Some(path) = &self.media_source {
                let is_video_src = davinci_flow_gpui::video_player::is_video_path(path);
                let src_for_play = path.clone();
                let import = path.clone();
                preview = preview
                    .child(label(
                        path.file_name()
                            .unwrap_or_default()
                            .to_string_lossy()
                            .into_owned(),
                    ))
                    .child(
                        row()
                            .w_full()
                            .gap(px(8.))
                            .when(is_video_src, |r| {
                                r.child(
                                    div()
                                        .flex_1()
                                        .flex_basis(px(0.))
                                        .min_w_0()
                                        .flex()
                                        .flex_col()
                                        .child(
                                            button("media-expand", "Ampliar vídeo", self.busy)
                                                .on_click(cx.listener(
                                                    move |this, _, window, cx| {
                                                        if this
                                                            .player_state
                                                            .current
                                                            .as_ref()
                                                            .is_some_and(|t| t.path == src_for_play)
                                                        {
                                                            this.video_modal_open = true;
                                                            cx.notify();
                                                        } else {
                                                            let track =
                                                    davinci_flow_gpui::audio_player::AudioTrack {
                                                        path: src_for_play.clone(),
                                                        title: src_for_play
                                                            .file_stem()
                                                            .unwrap_or_default()
                                                            .to_string_lossy()
                                                            .into_owned(),
                                                        kind: "Vídeo".into(),
                                                        is_video: true,
                                                    };
                                                            this.play_media_with_queue(
                                                                Tab::Brolls,
                                                                track.clone(),
                                                                vec![track],
                                                                Some(0),
                                                                true,
                                                                window,
                                                                cx,
                                                            );
                                                        }
                                                    },
                                                )),
                                        ),
                                )
                            })
                            .child(
                                div()
                                    .flex_1()
                                    .flex_basis(px(0.))
                                    .min_w_0()
                                    .flex()
                                    .flex_col()
                                    .child(
                                        accent_button(
                                            "media-import",
                                            "Importar a Resolve",
                                            self.busy,
                                        )
                                        .on_click(
                                            cx.listener(move |this, _, window, cx| {
                                                this.import_file(import.clone(), window, cx)
                                            }),
                                        ),
                                    ),
                            ),
                    );
            }
            body = body.child(preview);
        }
        let current_tab = if category == "visuals" {
            Tab::Brolls
        } else {
            Tab::Music
        };
        column()
            .size_full()
            .min_h_0()
            .gap(px(8.))
            .child(
                row()
                    .gap(px(8.))
                    .child(div().flex_1().child(Input::new(&self.library_filter)))
                    .child(button("add-folder", "Añadir carpeta", self.busy).on_click(
                        cx.listener(|this, _, window, cx| this.choose_library_folder(window, cx)),
                    ))
                    .child(
                        button("manage-folders", "Gestionar carpetas", self.busy).on_click(
                            cx.listener(move |this, _, window, cx| {
                                this.prepare_category(category, window, cx);
                                this.load_for_tab(Tab::Library, window, cx);
                            }),
                        ),
                    )
                    .child(
                        accent_button("index-library", "Reindexar", self.busy).on_click(
                            cx.listener(|this, _, window, cx| this.scan_library(window, cx)),
                        ),
                    ),
            )
            .child(
                row()
                    .justify_between()
                    .child(label(format!(
                        "{total} recursos · {} carpetas · {}/80 compartidos con IA · página {current_page}/{pages}",
                        self.preferences.folders_for(category).len(),
                        self.preferences.selected.len()
                    )))
                    .child(
                        row()
                            .gap(px(6.))
                            .child(
                                button("med-prev", "◀ Anterior", offset == 0).on_click(
                                    cx.listener(move |this, _, _, cx| {
                                        this.media_offset = offset.saturating_sub(PAGE_SIZE);
                                        cx.notify();
                                    }),
                                ),
                            )
                            .child(
                                button("med-next", "Siguiente ▶", offset + PAGE_SIZE >= total)
                                    .on_click(cx.listener(move |this, _, _, cx| {
                                        this.media_offset = offset + PAGE_SIZE;
                                        cx.notify();
                                    })),
                            ),
                    ),
            )
            .child(body)
            .child(self.player_bar_for_tab(current_tab, cx))
    }
}
