# Integración de Gemini, Comparación con Guion Original, Corrección de Jergas/Marcas y Marcadores en Línea de Tiempo — Plan

- Estado: `DRAFT`
- Fecha: `2026-08-17`
- Proyecto: `DaVinci Flow`

## Objetivo

Habilitar la integración de la API de Google Gemini en DaVinci Flow para comparar transcripciones contra el guion original, corregir errores de reconocimiento (ortografía, jergas, nombres de marca y alucinaciones de DaVinci), colocar marcadores automáticos en la línea de tiempo en puntos importantes y robustecer la integración con la API de DaVinci Resolve.

## Alcance

- Incluye:
  - Módulo de integración con Google Gemini (`GeminiClient`, soporte REST v1beta con `urllib.request` nativo de Python, estructuración JSON).
  - Manejo seguro de credenciales (`GEMINI_API_KEY`, configuración local, sin secretos en repositorios ni logs).
  - Motor de alineación y corrección de subtítulos con guion original (`ScriptAligner` & `CorrectionEngine`) preservando la sincronización de fotogramas (`start_frame`, `end_frame`).
  - Soporte de glosario y reemplazo de términos / nombres de marca / jergas específicas.
  - Generador e insertador de marcadores en la línea de tiempo de DaVinci Resolve (`ResolveMarkerWriter` con colores, nombres y notas temáticas).
  - Robustecimiento de adaptadores Resolve (`ResolveSubtitleReader`, posicionamiento de cursor / timecode antes de insertar títulos Text+, `ResolveTimelineWriter`).
  - Ampliación de interfaz gráfica (`uimanager_window.py` nativo y fallback Tkinter) y CLI (`davinci-flow`) con pestañas/controles para Guion, Glosario, API Key, Marcadores y Corrección IA.
  - Registro de modelos en `AI_MODELS.md` y actualización del perfil en `.agents/rules/core_profile.md`.
- No incluye:
  - Transcripción local pesada de modelos Whisper en GPU local (se delega en Resolve o servicios dedicados como LyraFlow).
  - Almacenamiento en la nube de transcripciones o guiones privados.

## Enfoque

1. **Gestión de Credenciales e Integración con Gemini**: Implementar `davinci_flow/ai/credentials.py` y `davinci_flow/ai/client.py` con cliente HTTP ligero y seguro sin dependencias externas obligatorias.
2. **Motor de Alineación y Corrección**: Implementar `davinci_flow/ai/aligner.py` para comparar subtítulos leídos de Resolve contra el texto del guion original, corregir palabras mal interpretadas y sugerir marcadores.
3. **Escritor de Marcadores en Resolve**: Implementar `davinci_flow/resolve/marker_writer.py` para insertar marcadores con colores y notas en la línea de tiempo de DaVinci Resolve.
4. **Robustecimiento de Adaptadores Resolve**: Corregir lectura de texto de clips de subtítulo y cálculo preciso de timecode/playhead para la inserción de títulos Text+.
5. **Orquestación en Capa de Aplicación**: Extender `davinci_flow/application.py` con funciones de alto nivel para escaneo, corrección con guion, planificación e inserción de marcadores.
6. **Ampliación de GUI y CLI**: Incorporar controles para guion, glosario, clave API y botones de acción en la ventana gráfica y argumentos de línea de comandos.
7. **Documentación y Pruebas**: Crear `AI_MODELS.md`, registrar suite de pruebas unitarias exhaustivas con mocks de Gemini y Resolve, y actualizar documentación.

## Criterios de finalización

- [ ] `GeminiClient` interactúa con la API de Gemini devolviendo respuestas estructuradas sin dependencias externas pesadas.
- [ ] La clave API se maneja de forma segura (variables de entorno, configuración local, enmascaramiento).
- [ ] La alineación con guion corrige errores ortográficos, jerga y marcas manteniendo los timecodes exactos.
- [ ] Los marcadores se insertan correctamente en la línea de tiempo activa de DaVinci Resolve.
- [ ] La interfaz gráfica (UIManager y Tkinter) permite ingresar guion, glosario, API key y ejecutar corrección/marcadores.
- [ ] 100% de las pruebas unitarias pasan exitosamente (`unittest discover`).
- [ ] `AI_MODELS.md` y perfil del proyecto actualizados.

## Autorización

- [ ] Plan aprobado para ejecución.
