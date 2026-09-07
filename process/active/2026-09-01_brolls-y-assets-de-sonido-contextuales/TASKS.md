# 📝 Tareas — Asistente Contextual de B-Rolls y Assets de Sonido

- [x] **Modelos y Catálogo de B-Rolls/Assets**: Implementado `broll_catalog.py` con escaneo recursivo de directorio e indexación de tags semánticos.
- [x] **Motor de Emparejamiento Semántico**: Implementado `broll_matcher.py` para cruce de transcripción con assets (heurística + Gemini AI).
- [x] **Gestor de Pistas y Escritura**: Añadida pista `DF_BROLL` a `track_manager.py` e inserción en `timeline_writer.py`.
- [x] **Orquestación en Application**: Integrado escaneo de assets y propuestas de B-rolls en `application.py`.
- [x] **Interfaz de Usuario**: Añadidos controles de selección de carpeta de assets y columna `B-Roll / SFX` en UIManager y Tkinter.
- [x] **Pruebas Automatizadas**: Creados tests unitarios para catálogo, matcher y pipeline de B-Rolls (116/116 tests pasando).
- [x] **Validación y Aprobación**: Documentados resultados técnicos en `VALIDATION.md` y `APPROVAL.md`.
