# Flujo de revisión y selector de rutas — Plan

- Estado: `DRAFT`
- Fecha: `2026-09-10`
- Proyecto: `DaVinci Flow`

## Objetivo

Permitir cerrar o salir de la revisión de composición en el editor, aplicar revisiones sin forzar el guardado manual individual de cada bloque si el usuario aprueba la propuesta completa, y dotar al selector de archivos de navegación entre unidades de disco (C:, D:, etc.) y creación de carpetas en caliente.

## Alcance

- Incluye:
  - Botón de cierre y salida del panel `Revisar composición` con deselección de fila en el editor.
  - Método `approve_all()` en `Proposal` y `EditorialController`.
  - Botón "Aprobar todo" en la barra de herramientas del editor y confirmación automática al pulsar "Aplicar revisión" si restan bloques sin marcar individualmente.
  - Detección de unidades lógicas en Windows (C:\, D:\, etc.) y chips/accesos directos en `WorkspaceFilePicker`.
  - Soporte de "Nueva carpeta" / "Crear carpeta" directamente en el diálogo del selector de archivos.
  - Pruebas unitarias para `approve_all`, `WorkspaceFilePicker` y el flujo de cierre del editor.
- No incluye:
  - Modificación del contrato estricto de validación en `generation_plan` cuando `require_review=True` (se preserva la regla de que todo bloque aplicado esté explícitamente revisado/aprobado).
  - Cambios en el motor de transcripción o análisis LLM.

## Enfoque

1. Agregar botón de cerrar revisión en la cabecera y acciones de `review_card` en `editor_view.py` con restablecimiento de selección.
2. Implementar `approve_all()` en `model.py` y `controller.py`, e integrarlo en `editor_view.py` (botón explícito y confirmación al aplicar).
3. Actualizar `shared/path_picker.py` con detección de unidades de disco en Windows y creación interactiva de carpetas.
4. Actualizar y añadir pruebas unitarias en `tests/test_desktop.py` y `tests/test_editorial.py`.

## Criterios de finalización

- [ ] Se puede cerrar el panel `Revisar composición` y deseleccionar la fila para volver a ver la lista completa.
- [ ] Al pulsar "Aplicar revisión", si hay bloques pendientes, se ofrece aprobar todos y aplicar directamente a Resolve sin errores bloqueantes.
- [ ] Existe un botón "Aprobar todo" en la interfaz para marcar todas las propuestas válidas en un solo clic.
- [ ] El selector de archivos muestra accesos directos a los discos disponibles (C:, D:, etc.) y permite cambiar de unidad con un clic.
- [ ] El selector de archivos permite crear una nueva carpeta dentro del directorio activo.
- [ ] La suite completa de 217+ pruebas unitarias se ejecuta y pasa en verde.

## Autorización

- [ ] Plan aprobado para ejecución.
