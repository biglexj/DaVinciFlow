//! Pestaña «Luna Fetch»: análisis, descarga e importación directa en DaVinci Resolve.
use super::*;
use gpui_kit::component::checkbox::Checkbox;

impl FlowApp {
    pub fn fetch_view(&self, cx: &mut Context<Self>) -> Div {
        let mut view = column().size_full().min_h_0().gap(px(10.)).child(
            card()
                .gap(px(10.))
                .child(section("Enlace del vídeo o música"))
                .child(
                    row()
                        .gap(px(8.))
                        .child(div().flex_1().child(Input::new(&self.fetch_url)))
                        .child(button("fetch-analyze", "Analizar", self.busy).on_click(
                            cx.listener(|this, _, window, cx| this.fetch_analyze(window, cx)),
                        ))
                        .child(
                            accent_button(
                                "fetch-download",
                                "Descargar e importar",
                                self.busy || self.fetch_url.read(cx).value().trim().is_empty(),
                            )
                            .on_click(
                                cx.listener(|this, _, window, cx| this.fetch_download(window, cx)),
                            ),
                        ),
                )
                .child(
                    row()
                        .gap(px(10.))
                        .items_center()
                        .child(
                            button(
                                "fetch-video",
                                if self.fetch_audio {
                                    "🎬 Vídeo (MP4)"
                                } else {
                                    "✓ 🎬 Vídeo (MP4)"
                                },
                                self.busy,
                            )
                            .on_click(cx.listener(|this, _, _, cx| {
                                this.fetch_audio = false;
                                cx.notify();
                            })),
                        )
                        .child(
                            button(
                                "fetch-audio",
                                if self.fetch_audio {
                                    "✓ 🎵 Música / Audio (MP3)"
                                } else {
                                    "🎵 Música / Audio (MP3)"
                                },
                                self.busy,
                            )
                            .on_click(cx.listener(|this, _, _, cx| {
                                this.fetch_audio = true;
                                cx.notify();
                            })),
                        )
                        .child(
                            Checkbox::new("fetch-import-check")
                                .label("Importar automáticamente en DaVinci Resolve")
                                .checked(self.fetch_import)
                                .on_click(cx.listener(|this, checked: &bool, _, cx| {
                                    this.fetch_import = *checked;
                                    cx.notify();
                                })),
                        )
                        .child(div().flex_1())
                        .child(label("Destino en Resolve: Luna Fetch / (Videos o Música)")),
                )
                .child(
                    row()
                        .gap(px(8.))
                        .child(field_label("Carpeta en disco:"))
                        .child(div().flex_1().child(Input::new(&self.fetch_directory)))
                        .child(
                            button("fetch-folder", "Elegir carpeta", self.busy).on_click(
                                cx.listener(|this, _, window, cx| {
                                    this.choose_fetch_folder(window, cx)
                                }),
                            ),
                        ),
                ),
        );

        if let Some(info) = &self.fetch_info {
            let duration = if info.duration_display.is_empty() {
                format!("{:.0} s", info.duration_seconds)
            } else {
                info.duration_display.clone()
            };
            let mut badges = row().gap(px(6.)).child(chip(duration, false));
            if let Some(ext) = &info.extractor
                && !ext.is_empty()
            {
                badges = badges.child(chip(ext.clone(), true));
            }
            if info.is_audio {
                badges = badges.child(chip("Solo audio", false));
            }
            view = view.child(
                card()
                    .gap(px(6.))
                    .child(section(info.title.clone()))
                    .child(label(format!(
                        "Subido por: {}",
                        info.uploader.as_deref().unwrap_or("Autor no disponible")
                    )))
                    .child(badges),
            );
        } else {
            view = view.child(
                card()
                    .gap(px(4.))
                    .child(section("Pega un enlace para analizar metadatos"))
                    .child(label(
                        "Compatible con YouTube, Suno AI, SoundCloud, TikTok y más de 1000 sitios.",
                    )),
            );
        }

        if !self.fetch_history.is_empty() {
            let mut list = column()
                .id("fetch-history-list")
                .max_h(px(260.))
                .overflow_y_scroll()
                .gap(px(6.));
            for (idx, item) in self.fetch_history.iter().enumerate() {
                let play = item.path.clone();
                let is_video_item = davinci_flow_gpui::video_player::is_video_path(&play);
                let is_audio_item =
                    item.kind == "audio" || davinci_flow_gpui::audio_player::is_audio_path(&play);
                let playable = is_audio_item || is_video_item;
                let is_playing_item = self.playing_sound.as_ref() == Some(&play);
                let item_title = if item.title.is_empty() {
                    if is_video_item {
                        "Vídeo de Luna Fetch".to_string()
                    } else {
                        "Audio de Luna Fetch".to_string()
                    }
                } else {
                    item.title.clone()
                };
                let folder = item.path.clone();
                let import = item.path.clone();
                let imported = item.imported;
                let play_btn = fixed_media_button(
                    ("fetch-play", idx),
                    if is_playing_item {
                        IconName::Pause
                    } else {
                        IconName::Play
                    },
                    if playable {
                        if is_playing_item {
                            "Pausar"
                        } else {
                            "Reproducir"
                        }
                    } else {
                        "Abrir archivo"
                    },
                    is_playing_item,
                    self.busy,
                    118.0,
                );
                let play_btn = if self.busy {
                    play_btn
                } else {
                    play_btn.on_click(cx.listener(move |this, _, window, cx| {
                        if playable {
                            let track = davinci_flow_gpui::audio_player::AudioTrack {
                                path: play.clone(),
                                title: item_title.clone(),
                                kind: if is_video_item {
                                    "Luna Fetch · Vídeo"
                                } else {
                                    "Luna Fetch"
                                }
                                .into(),
                                is_video: is_video_item,
                            };
                            this.play_media_with_queue(
                                Tab::Fetch,
                                track.clone(),
                                vec![track],
                                Some(0),
                                is_video_item,
                                window,
                                cx,
                            );
                        } else {
                            cx.open_with_system(&play);
                        }
                    }))
                };
                list = list.child(
                    row()
                        .w_full()
                        .px(px(12.))
                        .py(px(8.))
                        .rounded(px(8.))
                        .bg(rgb(0x161A1D))
                        .border_1()
                        .border_color(rgb(LINE))
                        .gap(px(10.))
                        .child(
                            column()
                                .flex_1()
                                .min_w_0()
                                .gap(px(2.))
                                .child(
                                    row()
                                        .gap(px(8.))
                                        .child(
                                            div()
                                                .text_size(px(12.5))
                                                .font_weight(FontWeight::SEMIBOLD)
                                                .text_ellipsis()
                                                .child(if item.title.is_empty() {
                                                    "Descarga".to_string()
                                                } else {
                                                    item.title.clone()
                                                }),
                                        )
                                        .child(chip(
                                            if imported { "En Resolve" } else { "Local" },
                                            imported,
                                        )),
                                )
                                .child(label(item.path.display().to_string())),
                        )
                        .child(play_btn)
                        .child(
                            button(("fetch-reveal", idx), "Abrir carpeta", self.busy)
                                .on_click(cx.listener(move |_, _, _, cx| cx.reveal_path(&folder))),
                        )
                        .child(
                            button(
                                ("fetch-import", idx),
                                "Importar a Resolve",
                                self.busy || imported,
                            )
                            .on_click(cx.listener(
                                move |this, _, window, cx| {
                                    this.import_file(import.clone(), window, cx)
                                },
                            )),
                        ),
                );
            }
            view = view.child(
                card()
                    .gap(px(8.))
                    .child(section("Descargas de la sesión"))
                    .child(list),
            );
        }
        view.child(self.player_bar_for_tab(Tab::Fetch, cx))
    }
}
