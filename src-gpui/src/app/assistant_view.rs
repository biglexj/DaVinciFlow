//! Pestaña «Asistente IA»: consultas de dirección creativa sobre el montaje actual.
use super::*;
use gpui_kit::component::Icon;

const SUGGESTIONS: [(&str, &str); 4] = [
    (
        "💡 Ritmo visual",
        "Sugiere cómo dosificar el ritmo de subtítulos y pausas para mantener máxima atención.",
    ),
    (
        "🎬 Selección B-Roll",
        "¿Qué momentos del guion justifican mejor insertar clips de B-Roll o imágenes?",
    ),
    (
        "🔊 Sonido sutil",
        "¿Qué efectos de sonido (pop, whoosh) recomiendas para acentuar ideas clave sin saturar?",
    ),
    (
        "✨ Dirección para Shorts",
        "Genera una dirección creativa de alto impacto para formato vertical de 60s.",
    ),
];

impl FlowApp {
    fn message_card(
        &self,
        index: usize,
        message: &AssistantMessage,
        cx: &mut Context<Self>,
    ) -> Div {
        let sender_color = if message.is_ai { ACCENT } else { MUTED };
        let background = if message.is_ai { 0x172A24 } else { 0x1B2226 };
        let border = if message.is_ai { ACCENT } else { LINE };
        let mut card = card()
            .gap(px(6.))
            .p(px(12.))
            .bg(rgb(background))
            .border_color(rgb(border))
            .rounded(px(10.))
            .child(
                row()
                    .gap(px(6.))
                    .child(
                        Icon::new(if message.is_ai {
                            IconName::Sparkles
                        } else {
                            IconName::User
                        })
                        .size(px(14.))
                        .text_color(rgb(sender_color)),
                    )
                    .child(
                        div()
                            .text_size(px(12.))
                            .font_weight(FontWeight::SEMIBOLD)
                            .text_color(rgb(sender_color))
                            .child(message.sender),
                    ),
            )
            .child(
                div()
                    .text_size(px(13.))
                    .text_color(rgb(TEXT))
                    .child(message.content.clone()),
            );
        if message.is_ai && index > 0 {
            let content = message.content.clone();
            card = card.child(
                row().justify_end().child(
                    button(
                        ("transfer-direction", index),
                        "Usar dirección creativa",
                        self.busy,
                    )
                    .on_click(cx.listener(move |this, _, window, cx| {
                        this.transfer_direction(&content, window, cx)
                    })),
                ),
            );
        }
        card
    }

    pub fn assistant_view(&self, cx: &mut Context<Self>) -> Div {
        let context = if self.session.document().cues.is_empty() {
            "Sin secuencia capturada. Captura primero en el Editor.".to_string()
        } else {
            format!(
                "Secuencia activa: {} · {} subtítulos",
                self.session.document().source,
                self.session.document().cues.len()
            )
        };
        column()
            .w_full()
            .max_w(px(880.))
            .min_h_0()
            .gap(px(12.))
            .child(
                card().p(px(10.)).gap(px(8.)).child(
                    row()
                        .gap(px(8.))
                        .child(
                            Icon::new(IconName::Sparkles)
                                .size(px(18.))
                                .text_color(rgb(ACCENT)),
                        )
                        .child(label(context)),
                ),
            )
            .child(
                row()
                    .gap(px(6.))
                    .children(SUGGESTIONS.iter().map(|(name, prompt)| {
                        let prompt = prompt.to_string();
                        button(format!("suggestion-{name}"), *name, false).on_click(cx.listener(
                            move |this, _, window, cx| {
                                this.ask_assistant(prompt.clone(), window, cx)
                            },
                        ))
                    })),
            )
            .child(
                column()
                    .max_h(px(380.))
                    .min_h(px(120.))
                    .gap(px(10.))
                    .p(px(12.))
                    .bg(rgb(CARD))
                    .border_1()
                    .border_color(rgb(LINE))
                    .rounded(px(12.))
                    .id("assistant-messages")
                    .overflow_y_scroll()
                    .children(
                        self.assistant_messages
                            .iter()
                            .enumerate()
                            .map(|(index, message)| self.message_card(index, message, cx)),
                    ),
            )
            .child(
                row()
                    .gap(px(8.))
                    .child(div().flex_1().child(Input::new(&self.assistant_prompt)))
                    .child(accent_button("send-prompt", "Enviar", self.busy).on_click(
                        cx.listener(|this, _, window, cx| {
                            let prompt = this.assistant_prompt.read(cx).value().to_string();
                            if prompt.trim().is_empty() {
                                return;
                            }
                            this.assistant_prompt
                                .update(cx, |state, cx| state.set_value("", window, cx));
                            this.ask_assistant(prompt, window, cx);
                        }),
                    )),
            )
    }
}
