# Validación
 
- Pruebas unitarias de suite completa: 180 pruebas ejecutadas exitosamente con `python -m unittest discover -s tests` (100% aprobadas, 0 errores, 0 fallos).
- Validación de `DesktopTests`:
  - `test_editor_layout_buttons_and_expanded_table`: verifica `table_view.expand == True`, presencia del botón `Cargar SRT` y reubicación de `Aplicar revisión` y `Deshacer muestra` en la barra de acciones superior.
  - `test_auto_capture_default`: verifica que la captura de subtítulos generados en Resolve se ejecute automáticamente sin requerir intervención manual.
  - `test_settings_model_selector_and_key_persistence`: verifica persistencia de la clave enmascarada (`••••••••••••••••`) y escaneo dinámico de modelos de Gemini con actualización de opciones en el selector (`ft.Dropdown`).
- Escaneo real de API Gemini: llamada en vivo verificó la disponibilidad de modelos (`gemini-3.5-flash-lite`, `gemini-3.5-flash`, `gemini-3.7-flash`, `gemini-3.1-flash-lite`, `gemini-3.6-flash`, `gemini-3.8-flash`, `gemini-3.5-transcribe`).
- Purga completa de Tkinter:
  - Verificación estricta con `grep_search`: cero importaciones o referencias a `tkinter` en `src/` y `tests/`.
  - Archivos eliminados con confirmación en Git: `editorial_window.py`, `library_panel.py`, `template_panel.py`, `tkinter_window.py`, `uimanager_window.py`, `widgets.py`, `workbench_window.py` y `test_editorial_ui.py`.
  - El punto de entrada nativo `davinci_flow.ui.open_davinci_flow_ui` y el CLI `davinci_flow --flet-ui` operan exclusivamente sobre la arquitectura Flet (`davinci_flow.ui.desktop`).


