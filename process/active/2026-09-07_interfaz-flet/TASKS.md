# Tareas

- [x] Controlador independiente de Tk y conservación de propuestas.
- [x] Editor Flet adaptable con revisión y tablas desplazables:
  - Botón renombrado a «Cargar SRT».
  - Acciones «Aplicar revisión» y «Deshacer muestra» reubicadas en la barra superior en sub-filas alineadas (`SPACE_BETWEEN`) sin contenedor expandido desbordante.
  - Corrección de fondo gris: eliminado el contenedor `expand=True` dentro del `Row(wrap=True)` y aplicado `bgcolor=CARD` a `scroll_table`.
  - Captura automática de subtítulos generados en DaVinci Resolve al abrir la aplicación (`auto_capture_default`).
- [x] Plantillas, biblioteca y ajustes conectados:
  - Corrección de scrolls superpuestos: tema de barras de desplazamiento ajustado a sobrio (`#363E44`), oculto cuando no se desplaza (`thumb_visibility=False`), y cambio a `ScrollMode.AUTO` en todas las vistas (Plantillas, Biblioteca, Ajustes).
  - Persistencia visual de la clave API con máscara `••••••••••••••••` sin borrado al cargar o guardar.
  - Selector dinámico de modelos con escaneo de Gemini API (`list_available_gemini_models`) y botón de refresco.
- [x] Entrada ejecutable y dependencias reproducibles.
- [x] Pruebas funcionales y comprobación visual real (187 pruebas superadas).
- [x] Evidencia y límites de la migración:
  - Eliminación total de archivos legados de Tkinter (`editorial_window.py`, `library_panel.py`, `template_panel.py`, `tkinter_window.py`, `uimanager_window.py`, `widgets.py`, `workbench_window.py`, `test_editorial_ui.py`).
  - Purga de dependencias e importaciones de Tkinter en tests (`test_editorial_highlights.py` actualizado a `EntryPointTests`).
  - Cero dependencias residuales de `tkinter` en el código fuente de producción y pruebas.

