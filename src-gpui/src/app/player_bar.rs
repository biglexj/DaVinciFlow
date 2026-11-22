//! Reproductor integrado multimedia (vídeo, música, SFX y locuciones) acotado a su sección.
use super::*;
use davinci_flow_gpui::audio_player::{AudioTrack, PlaybackStatus, format_ms};
use gpui_kit::component::Icon;

const SEEK_STEPS: usize = 40;
const VOLUME_STEPS: [u8; 10] = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100];

impl FlowApp {
    pub(super) fn clear_video_frame(&mut self, window: &mut Window) {
        if let Some(old) = self.video_frame.take() {
            let _ = window.drop_image(old);
        }
    }

    pub(super) fn sync_player_snapshot(
        &mut self,
        window: Option<&mut Window>,
        cx: &mut Context<Self>,
    ) {
        let prev_path = self.player_state.current.as_ref().map(|t| t.path.clone());
        self.player_state = self.audio_player.snapshot();
        self.playing_sound = match self.player_state.status {
            PlaybackStatus::Playing | PlaybackStatus::Loading => {
                self.player_state.current.as_ref().map(|t| t.path.clone())
            }
            PlaybackStatus::Paused | PlaybackStatus::Stopped => None,
        };

        let Some(track) = self.player_state.current.clone() else {
            self.video_streamer.stop();
            self.video_modal_open = false;
            self.player_origin = None;
            if let Some(win) = window {
                self.clear_video_frame(win);
            }
            return;
        };

        if !track.is_video {
            if prev_path.as_ref() != Some(&track.path) {
                self.video_streamer.stop();
                self.video_modal_open = false;
                if let Some(win) = window {
                    self.clear_video_frame(win);
                }
            }
            return;
        }

        if self.player_origin == Some(Tab::Brolls) {
            self.media_source = Some(track.path.clone());
        }

        let switched_track = prev_path.as_ref() != Some(&track.path);
        if self.video_synced_epoch != self.player_state.stream_epoch
            && self.player_state.status != PlaybackStatus::Loading
        {
            self.video_synced_epoch = self.player_state.stream_epoch;
            if switched_track && let Some(win) = window.as_deref() {
                let _ = win;
            }
            self.video_streamer
                .start(track.path.clone(), self.player_state.position_ms);
        }

        let should_pull = matches!(
            self.player_state.status,
            PlaybackStatus::Playing | PlaybackStatus::Paused | PlaybackStatus::Stopped
        );
        if should_pull
            && let Some(win) = window
            && let Some((_, jpeg_bytes)) = self
                .video_streamer
                .take_frame_for(self.player_state.position_ms, self.video_frame.is_none())
        {
            let img_data = Image::from_bytes(ImageFormat::Jpeg, jpeg_bytes);
            if let Ok(render_img) = img_data.to_image_data(cx.svg_renderer())
                && let Some(old) = self.video_frame.replace(render_img)
            {
                let _ = win.drop_image(old);
            }
        }
    }

    pub(super) fn ensure_player_pump(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        if self.player_pump_active {
            return;
        }
        self.player_pump_active = true;
        cx.spawn_in(window, async move |this, cx| {
            loop {
                let is_video = this
                    .update_in(cx, |this, _, _| {
                        this.player_state
                            .current
                            .as_ref()
                            .is_some_and(|t| t.is_video)
                    })
                    .unwrap_or(false);
                let interval = if is_video { 40 } else { 120 };
                cx.background_executor()
                    .timer(std::time::Duration::from_millis(interval))
                    .await;
                let keep_going = this
                    .update_in(cx, |this, window, cx| {
                        this.sync_player_snapshot(Some(window), cx);
                        let waiting_first_frame = this
                            .player_state
                            .current
                            .as_ref()
                            .is_some_and(|t| t.is_video)
                            && this.video_frame.is_none()
                            && this.video_streamer.error().is_none();
                        let active = matches!(
                            this.player_state.status,
                            PlaybackStatus::Playing | PlaybackStatus::Loading
                        ) || waiting_first_frame;
                        if !active {
                            this.player_pump_active = false;
                            if let Some(err) = this
                                .player_state
                                .error
                                .clone()
                                .or_else(|| this.video_streamer.error())
                            {
                                this.notify(Err(err), cx);
                            }
                        }
                        cx.notify();
                        active
                    })
                    .unwrap_or(false);
                if !keep_going {
                    break;
                }
            }
        })
        .detach();
    }

    #[allow(clippy::too_many_arguments)]
    pub(super) fn play_media_with_queue(
        &mut self,
        origin: Tab,
        track: AudioTrack,
        queue: Vec<AudioTrack>,
        queue_index: Option<usize>,
        open_modal: bool,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) {
        if self
            .player_state
            .current
            .as_ref()
            .is_some_and(|c| c.path == track.path)
            && matches!(
                self.player_state.status,
                PlaybackStatus::Playing | PlaybackStatus::Paused
            )
        {
            self.player_origin = Some(origin);
            if open_modal && track.is_video {
                self.video_modal_open = true;
            }
            self.audio_player.toggle_pause();
            self.sync_player_snapshot(Some(window), cx);
            self.ensure_player_pump(window, cx);
            cx.notify();
            return;
        }
        let title = track.title.clone();
        let is_video = track.is_video;
        self.player_origin = Some(origin);
        self.video_modal_open = open_modal && is_video;
        self.clear_video_frame(window);
        self.video_synced_epoch = 0;
        if is_video && origin == Tab::Brolls {
            self.media_source = Some(track.path.clone());
        }
        self.audio_player.play(track, queue, queue_index);
        self.sync_player_snapshot(Some(window), cx);
        self.ensure_player_pump(window, cx);
        self.notify(Ok(format!("Reproduciendo: {title}")), cx);
    }

    pub(super) fn player_icon_for_track(track: &AudioTrack) -> IconName {
        if track.is_video {
            return IconName::Clapperboard;
        }
        match track.kind.as_str() {
            "Música" => IconName::Music,
            "SFX" => IconName::AudioLines,
            "Voz" => IconName::MicVocal,
            _ => IconName::AudioWaveform,
        }
    }

    fn icon_control(
        id: impl Into<ElementId>,
        tooltip: &'static str,
        icon: IconName,
        active: bool,
        disabled: bool,
    ) -> Stateful<Div> {
        let p = palette();
        let icon_color = if active { p.on_accent } else { p.text };
        div()
            .id(id)
            .role(Role::Button)
            .aria_label(tooltip)
            .w(px(32.))
            .h(px(30.))
            .rounded(px(7.))
            .flex()
            .items_center()
            .justify_center()
            .bg(rgb(if active { p.accent } else { p.raised }))
            .when(!active, |d| d.border_1().border_color(rgb(p.line)))
            .when(disabled, |d| d.opacity(0.4).cursor_default())
            .when(!disabled, |d| {
                d.cursor_pointer().hover(move |s| {
                    if active {
                        s.bg(rgb(p.accent_hover))
                    } else {
                        s.bg(rgb(p.active)).border_color(rgb(p.accent))
                    }
                })
            })
            .child(Icon::new(icon).size(px(15.)).text_color(rgb(icon_color)))
    }

    fn is_media_player_tab(tab: Tab) -> bool {
        matches!(tab, Tab::Brolls | Tab::Music | Tab::Sfx | Tab::Fetch)
    }

    /// Reproductor completo visible en todas las pestañas multimedia (B-Rolls, Música, SFX, Luna Fetch).
    pub fn player_bar_for_tab(&self, tab: Tab, cx: &mut Context<Self>) -> Div {
        if self.player_state.current.is_none() || !Self::is_media_player_tab(tab) {
            return div();
        }
        self.render_player_deck("deck", false, cx)
    }

    /// Reproductor compacto integrado dentro de la tarjeta «Audio generado» en Generación de voz.
    pub fn inline_voice_player(&self, cx: &mut Context<Self>) -> Div {
        if self.player_origin != Some(Tab::Voice) || self.player_state.current.is_none() {
            return div();
        }
        self.render_player_deck("voice-deck", true, cx)
    }

    /// Mini-control compacto en el extremo derecho del pie cuando estás en pestañas que no son multimedia.
    pub fn footer_mini_player(&self, cx: &mut Context<Self>) -> Div {
        let Some(track) = &self.player_state.current else {
            return div();
        };
        if Self::is_media_player_tab(self.tab)
            || (self.tab == Tab::Voice && self.player_origin == Some(Tab::Voice))
        {
            return div();
        }
        let p = palette();
        let is_playing = self.player_state.status == PlaybackStatus::Playing;
        let is_loading = self.player_state.status == PlaybackStatus::Loading;
        let duration_ms = self.player_state.duration_ms;
        let short_title = track
            .path
            .file_name()
            .map(|n| n.to_string_lossy().into_owned())
            .filter(|s| !s.is_empty())
            .unwrap_or_else(|| track.title.clone());

        row()
            .flex_shrink_0()
            .gap(px(6.))
            .items_center()
            .px(px(8.))
            .py(px(3.))
            .rounded(px(8.))
            .bg(rgb(p.card))
            .border_1()
            .border_color(rgb(p.line))
            .child(
                div()
                    .max_w(px(160.))
                    .min_w_0()
                    .overflow_hidden()
                    .whitespace_nowrap()
                    .text_ellipsis()
                    .text_size(px(11.5))
                    .text_color(rgb(p.muted))
                    .child(short_title),
            )
            .child(
                Self::icon_control(
                    "mini-rw",
                    "Retroceder 10 segundos",
                    IconName::Rewind,
                    false,
                    duration_ms == 0,
                )
                .w(px(26.))
                .h(px(24.))
                .on_click(cx.listener(|this, _, window, cx| {
                    this.audio_player.seek_delta_ms(-10_000);
                    this.sync_player_snapshot(Some(window), cx);
                    this.ensure_player_pump(window, cx);
                    cx.notify();
                })),
            )
            .child(
                Self::icon_control(
                    "mini-toggle",
                    if is_playing { "Pausar" } else { "Reproducir" },
                    if is_playing {
                        IconName::Pause
                    } else {
                        IconName::Play
                    },
                    true,
                    is_loading,
                )
                .w(px(30.))
                .h(px(24.))
                .on_click(cx.listener(|this, _, window, cx| {
                    this.audio_player.toggle_pause();
                    this.sync_player_snapshot(Some(window), cx);
                    this.ensure_player_pump(window, cx);
                    cx.notify();
                })),
            )
            .child(
                Self::icon_control(
                    "mini-ff",
                    "Adelantar 10 segundos",
                    IconName::FastForward,
                    false,
                    duration_ms == 0,
                )
                .w(px(26.))
                .h(px(24.))
                .on_click(cx.listener(|this, _, window, cx| {
                    this.audio_player.seek_delta_ms(10_000);
                    this.sync_player_snapshot(Some(window), cx);
                    this.ensure_player_pump(window, cx);
                    cx.notify();
                })),
            )
            .child(
                Self::icon_control(
                    "mini-close",
                    "Cerrar reproductor",
                    IconName::X,
                    false,
                    false,
                )
                .w(px(26.))
                .h(px(24.))
                .on_click(cx.listener(|this, _, window, cx| {
                    this.stop_audio_with_window(Some(window), cx);
                })),
            )
    }

    pub(super) fn render_player_deck(
        &self,
        prefix: &'static str,
        compact: bool,
        cx: &mut Context<Self>,
    ) -> Div {
        let Some(track) = &self.player_state.current else {
            return div();
        };

        let is_playing = self.player_state.status == PlaybackStatus::Playing;
        let is_loading = self.player_state.status == PlaybackStatus::Loading;
        let duration_ms = self.player_state.duration_ms;
        let position_ms = if duration_ms > 0 {
            self.player_state.position_ms.min(duration_ms)
        } else {
            self.player_state.position_ms
        };
        let has_queue = self.player_state.queue.len() > 1;
        let queue_badge = match (self.player_state.queue_index, has_queue) {
            (Some(idx), true) => format!(
                "{} · {}/{}",
                track.kind,
                idx + 1,
                self.player_state.queue.len()
            ),
            _ => track.kind.clone(),
        };

        let filled_steps = if duration_ms > 0 {
            ((position_ms as f64 / duration_ms as f64) * SEEK_STEPS as f64)
                .round()
                .clamp(0.0, SEEK_STEPS as f64) as usize
        } else {
            0
        };

        let mut progress_track = row()
            .flex_1()
            .min_w_0()
            .h(px(16.))
            .gap(px(1.))
            .items_center();
        for step in 0..SEEK_STEPS {
            let filled = step < filled_steps;
            let is_head = step + 1 == filled_steps && duration_ms > 0;
            let target_ms = if duration_ms > 0 {
                (duration_ms.saturating_mul(step as u64)) / SEEK_STEPS as u64
            } else {
                0
            };
            progress_track = progress_track.child(
                div()
                    .id(ElementId::Name(format!("{prefix}-seek-{step}").into()))
                    .flex_1()
                    .h(px(14.))
                    .flex()
                    .items_center()
                    .when(duration_ms > 0, |d| {
                        d.cursor_pointer()
                            .on_click(cx.listener(move |this, _, window, cx| {
                                this.audio_player.seek_ms(target_ms);
                                this.sync_player_snapshot(Some(window), cx);
                                this.ensure_player_pump(window, cx);
                                cx.notify();
                            }))
                    })
                    .child(
                        div()
                            .w_full()
                            .h(px(if is_head { 8. } else { 5. }))
                            .rounded(px(2.))
                            .bg(rgb(if filled { ACCENT } else { 0x2B3338 })),
                    ),
            );
        }

        let effective_vol = if self.player_state.muted || !self.player_state.has_audio {
            0
        } else {
            self.player_state.volume
        };
        let mut vol_bars = row().h(px(18.)).gap(px(2.)).items_end();
        for (idx, level) in VOLUME_STEPS.iter().copied().enumerate() {
            let active = effective_vol >= level;
            let bar_height = 6.0 + (idx as f32) * 1.1;
            vol_bars = vol_bars.child(
                div()
                    .id(ElementId::Name(format!("{prefix}-vol-{idx}").into()))
                    .w(px(5.))
                    .h(px(18.))
                    .flex()
                    .items_end()
                    .when(self.player_state.has_audio, |d| {
                        d.cursor_pointer()
                            .on_click(cx.listener(move |this, _, window, cx| {
                                this.audio_player.set_volume(level);
                                this.sync_player_snapshot(Some(window), cx);
                                cx.notify();
                            }))
                    })
                    .child(
                        div()
                            .w_full()
                            .h(px(bar_height))
                            .rounded(px(2.))
                            .bg(rgb(if active { ACCENT } else { 0x2B3338 })),
                    ),
            );
        }

        let ext = track
            .path
            .extension()
            .and_then(|s| s.to_str())
            .unwrap_or_default()
            .to_ascii_uppercase();
        let meta_line = if !self.player_state.has_audio && track.is_video {
            format!("{queue_badge} · {ext} · Sin pista de audio")
        } else if ext.is_empty() {
            queue_badge
        } else {
            format!("{queue_badge} · {ext}")
        };

        let track_path = track.path.clone();
        let is_video = track.is_video;

        let p = palette();
        let container = if compact {
            column()
                .w_full()
                .bg(rgb(p.field))
                .border_1()
                .border_color(rgb(p.line))
                .rounded(px(8.))
                .px(px(12.))
                .py(px(8.))
                .gap(px(6.))
        } else {
            column()
                .flex_shrink_0()
                .w_full()
                .bg(rgb(p.card))
                .border_1()
                .border_color(rgb(p.line))
                .rounded(px(8.))
                .px(px(14.))
                .py(px(8.))
                .gap(px(6.))
        };

        container.child(
            row()
                .w_full()
                .gap(px(12.))
                .items_center()
                .child(
                    row()
                        .w(px(if compact { 210. } else { 250. }))
                        .min_w(px(170.))
                        .gap(px(10.))
                        .items_center()
                        .child(
                            div()
                                .w(px(34.))
                                .h(px(34.))
                                .rounded(px(8.))
                                .bg(rgb(ACTIVE))
                                .border_1()
                                .border_color(rgb(ACCENT))
                                .flex()
                                .items_center()
                                .justify_center()
                                .child(
                                    Icon::new(Self::player_icon_for_track(track))
                                        .size(px(17.))
                                        .text_color(rgb(ACCENT)),
                                ),
                        )
                        .child(
                            column()
                                .flex_1()
                                .min_w_0()
                                .gap(px(2.))
                                .child(
                                    div()
                                        .text_size(px(12.5))
                                        .font_weight(FontWeight::SEMIBOLD)
                                        .text_color(rgb(TEXT))
                                        .text_ellipsis()
                                        .child(track.title.clone()),
                                )
                                .child(
                                    div()
                                        .text_size(px(11.))
                                        .text_color(rgb(MUTED))
                                        .text_ellipsis()
                                        .child(meta_line),
                                ),
                        ),
                )
                .child(
                    column()
                        .flex_1()
                        .min_w_0()
                        .gap(px(4.))
                        .child(
                            row()
                                .w_full()
                                .justify_center()
                                .gap(px(6.))
                                .when(has_queue && !compact, |r| {
                                    r.child(
                                        Self::icon_control(
                                            ElementId::Name(format!("{prefix}-prev").into()),
                                            "Anterior",
                                            IconName::SkipBack,
                                            false,
                                            false,
                                        )
                                        .on_click(
                                            cx.listener(|this, _, window, cx| {
                                                this.audio_player.prev_track();
                                                this.sync_player_snapshot(Some(window), cx);
                                                this.ensure_player_pump(window, cx);
                                                cx.notify();
                                            }),
                                        ),
                                    )
                                })
                                .child(
                                    Self::icon_control(
                                        ElementId::Name(format!("{prefix}-rw").into()),
                                        "Retroceder 10 segundos",
                                        IconName::Rewind,
                                        false,
                                        duration_ms == 0,
                                    )
                                    .on_click(cx.listener(
                                        |this, _, window, cx| {
                                            this.audio_player.seek_delta_ms(-10_000);
                                            this.sync_player_snapshot(Some(window), cx);
                                            this.ensure_player_pump(window, cx);
                                            cx.notify();
                                        },
                                    )),
                                )
                                .child(
                                    Self::icon_control(
                                        ElementId::Name(format!("{prefix}-toggle").into()),
                                        if is_playing { "Pausar" } else { "Reproducir" },
                                        if is_playing {
                                            IconName::Pause
                                        } else {
                                            IconName::Play
                                        },
                                        true,
                                        is_loading,
                                    )
                                    .w(px(38.))
                                    .on_click(cx.listener(
                                        |this, _, window, cx| {
                                            this.audio_player.toggle_pause();
                                            this.sync_player_snapshot(Some(window), cx);
                                            this.ensure_player_pump(window, cx);
                                            cx.notify();
                                        },
                                    )),
                                )
                                .child(
                                    Self::icon_control(
                                        ElementId::Name(format!("{prefix}-stop").into()),
                                        "Detener",
                                        IconName::Square,
                                        false,
                                        false,
                                    )
                                    .on_click(cx.listener(
                                        |this, _, window, cx| {
                                            this.audio_player.stop(true);
                                            this.sync_player_snapshot(Some(window), cx);
                                            cx.notify();
                                        },
                                    )),
                                )
                                .child(
                                    Self::icon_control(
                                        ElementId::Name(format!("{prefix}-ff").into()),
                                        "Adelantar 10 segundos",
                                        IconName::FastForward,
                                        false,
                                        duration_ms == 0,
                                    )
                                    .on_click(cx.listener(
                                        |this, _, window, cx| {
                                            this.audio_player.seek_delta_ms(10_000);
                                            this.sync_player_snapshot(Some(window), cx);
                                            this.ensure_player_pump(window, cx);
                                            cx.notify();
                                        },
                                    )),
                                )
                                .when(has_queue && !compact, |r| {
                                    r.child(
                                        Self::icon_control(
                                            ElementId::Name(format!("{prefix}-next").into()),
                                            "Siguiente",
                                            IconName::SkipForward,
                                            false,
                                            false,
                                        )
                                        .on_click(
                                            cx.listener(|this, _, window, cx| {
                                                this.audio_player.next_track();
                                                this.sync_player_snapshot(Some(window), cx);
                                                this.ensure_player_pump(window, cx);
                                                cx.notify();
                                            }),
                                        ),
                                    )
                                })
                                .child(
                                    Self::icon_control(
                                        ElementId::Name(format!("{prefix}-loop").into()),
                                        "Repetir",
                                        IconName::Repeat1,
                                        self.player_state.loop_track,
                                        false,
                                    )
                                    .on_click(cx.listener(
                                        |this, _, window, cx| {
                                            this.audio_player.toggle_loop();
                                            this.sync_player_snapshot(Some(window), cx);
                                            cx.notify();
                                        },
                                    )),
                                ),
                        )
                        .child(
                            row()
                                .w_full()
                                .gap(px(8.))
                                .items_center()
                                .child(
                                    div()
                                        .w(px(44.))
                                        .text_size(px(11.))
                                        .text_color(rgb(MUTED))
                                        .child(format_ms(position_ms)),
                                )
                                .child(progress_track)
                                .child(
                                    div()
                                        .w(px(44.))
                                        .text_size(px(11.))
                                        .text_color(rgb(MUTED))
                                        .child(if duration_ms > 0 {
                                            format_ms(duration_ms)
                                        } else if is_loading {
                                            "…".into()
                                        } else {
                                            "--:--".into()
                                        }),
                                ),
                        ),
                )
                .child(
                    row()
                        .gap(px(8.))
                        .items_center()
                        .when(is_video && !self.video_modal_open && !compact, |r| {
                            r.child(
                                button(
                                    ElementId::Name(format!("{prefix}-expand").into()),
                                    "Ampliar vídeo",
                                    false,
                                )
                                .on_click(cx.listener(
                                    |this, _, _, cx| {
                                        this.video_modal_open = true;
                                        cx.notify();
                                    },
                                )),
                            )
                        })
                        .when(!compact && !is_video, |r| {
                            let imp = track_path.clone();
                            r.child(
                                button(
                                    ElementId::Name(format!("{prefix}-import").into()),
                                    "Importar",
                                    self.busy,
                                )
                                .on_click(cx.listener(
                                    move |this, _, window, cx| {
                                        this.import_file(imp.clone(), window, cx)
                                    },
                                )),
                            )
                        })
                        .when(self.player_state.has_audio, |r| {
                            r.child(
                                Self::icon_control(
                                    ElementId::Name(format!("{prefix}-mute").into()),
                                    if self.player_state.muted {
                                        "Activar sonido"
                                    } else {
                                        "Silenciar"
                                    },
                                    if self.player_state.muted || self.player_state.volume == 0 {
                                        IconName::VolumeX
                                    } else {
                                        IconName::Volume2
                                    },
                                    false,
                                    false,
                                )
                                .on_click(cx.listener(
                                    |this, _, window, cx| {
                                        this.audio_player.toggle_mute();
                                        this.sync_player_snapshot(Some(window), cx);
                                        cx.notify();
                                    },
                                )),
                            )
                            .child(vol_bars)
                            .child(
                                div()
                                    .w(px(34.))
                                    .text_size(px(11.))
                                    .text_color(rgb(MUTED))
                                    .child(format!("{effective_vol}%")),
                            )
                        })
                        .child(
                            Self::icon_control(
                                ElementId::Name(format!("{prefix}-close").into()),
                                "Cerrar reproductor",
                                IconName::X,
                                false,
                                false,
                            )
                            .on_click(cx.listener(
                                |this, _, window, cx| {
                                    this.stop_audio_with_window(Some(window), cx);
                                },
                            )),
                        ),
                ),
        )
    }
}
