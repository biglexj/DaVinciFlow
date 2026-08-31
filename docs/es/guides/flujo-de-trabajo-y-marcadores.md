# 🎬 Flujo de Trabajo, Animaciones Fusion y Marcadores — DaVinci Flow

Guía técnica y editorial sobre la integración de **DaVinci Flow** con **DaVinci Resolve 21**, detallando el flujo de edición, los disparadores de efectos sonoros por pausas, las animaciones paramétricas de Fusion y el código cromático de marcadores.

---

## 🎯 1. Visión General del Flujo Editorial

DaVinci Flow transforma la transcripción automática de DaVinci Resolve o un archivo `.srt` en una experiencia visual y sonora multicapa de nivel profesional:

```
[Audio / Transcripción nativa de Resolve o SRT]
                     │
                     ▼
       [Alineación & Corrección IA (Gemini)]
          ├── Reemplazo estricto con Glosario
          └── Detección de Marcadores Cromáticos
                     │
                     ▼
        [Motor de Segmentación Multicapa]
          ├── DF_CONTEXT (Pista Superior: Contexto / Subordinadas)
          ├── DF_MAIN    (Pista Central: Núcleo del Mensaje)
          └── DF_ACCENT  (Pista Inferior: Palabras Clave / Énfasis)
                     │
                     ▼
      [Motor de SFX & Disparadores de Pausas]
          ├── Detección de silencios y cortes de tema (> 1.0 s)
          └── Asignación determinista según intención y cooldown
                     │
                     ▼
   [Composición Paramétrica en Fusion (.setting)]
          ├── Pop Bounce (Dinámico / Shorts)
          ├── Slide Up Smooth (Reflexivo / Documental)
          ├── Kinetic Pulse (Impacto / Acento)
          └── Fade Smooth (Elegante / Tutorial)
                     │
                     ▼
      [Escritura Verificada en Timeline de Resolve]
```

---

## 🎨 2. Código Cromático Oficial de Marcadores en Timeline

Para mantener la línea de tiempo de DaVinci Resolve organizada visualmente, DaVinci Flow utiliza un estándar de colores reconocibles por cualquier editor de video:

| Color en Resolve | Nombre del Color | Significado Editorial | Uso Práctico |
|---|---|---|---|
| 🔵 **Blue** | Azul | **Capítulos & Temas** | Inicio de nuevas secciones, cambios de tema o estructura del video. |
| 🟡 **Yellow** | Amarillo | **Puntos Clave & Énfasis** | Conclusiones importantes, declaraciones centrales o *punchlines*. |
| 🟢 **Green** | Verde | **Efectos de Sonido (SFX)** | Disparadores de audio, entradas de whoosh, pops de ritmo o pausas. |
| 🔷 **Cyan** | Cian | **Preguntas & Audiencia** | Preguntas retóricas, llamadas a la reflexión o momentos interactivos. |
| 🟣 **Magenta** | Magenta | **Corrección IA & Glosario** | Palabras corregidas respecto al guion original o términos técnicos. |
| 🌸 **Pink / Rose** | Rosa | **Llamadas a la Acción (CTA)** | Solicitud de suscripción, enlaces en descripción o despedida. |

---

## 🔊 3. Disparadores de SFX por Pausas y Cortes de Tema

DaVinci Flow analiza la distancia temporal entre subtítulos sucesivos:

1. **Detección de Brechas (Gap Detection)**:
   - Cuando existe un silencio o pausa narrativa mayor a **24 fotogramas** ($\ge 1.0\text{ s}$ a 24 fps), el sistema detecta un cambio de ritmo y sugiere un efecto de transición (*Whoosh limpio* o *Pop sutil*).
2. **Control de Enfriamiento (Cooldown)**:
   - Evita la saturación sonora respetando el perfil seleccionado (`reflexivo`, `natural`, `educativo`, `dinamico`, `video_corto`).
3. **Control de Ganancia y Niveles**:
   - Cada efecto de audio se inserta en la pista dedicada `DF_SFX` con un nivel de mezcla recomendado (ej. $-14\text{ dB}$ para whooshes y $-18\text{ dB}$ para campanas).

---

## ✨ 4. Presets de Animación Fusion Paramétrica (.setting)

DaVinci Flow genera composiciones Fusion nativas con nodos `TextPlus` y controladores de transformación con curvas Bezier (`BezierSpline`):

* **`pop_bounce`**: Escala rápida con rebote elástico ($0.85 \to 1.10 \to 1.0$). Ideal para videos cortos, momentos dinámicos y palabras acentuadas.
* **`slide_up`**: Entrada vertical suave ascendente ($Y: 0.12 \to 0.15$) con fundido de opacidad. Perfecto para contexto y vídeos estilo documental.
* **`kinetic_pulse`**: Pulso de impacto inicial ($1.18 \to 1.0$) sincronizado con el primer golpe de voz.
* **`fade_smooth`**: Fundido progresivo de alfa ($0.0 \to 1.0$) de 6 fotogramas sin alteración geométrica.
* **`none`**: Renderizado estático limpio para edición minimalista.

---

## 🌐 5. Preparación para Publicación en Aurora Blog

Este documento sirve como base técnica para el artículo editorial en la web oficial **Aurora Blog**:
* **Título sugerido**: *«DaVinci Flow: De la transcripción al corte final con subtítulos cinemáticos, Fusion y diseño sonoro dinámico»*.
* **Categoría**: `Postproducción / Automatización`.
* **Audiencia**: Editores de DaVinci Resolve, creadores de contenido para YouTube/TikTok y desarrolladores del ecosistema Biglex.
