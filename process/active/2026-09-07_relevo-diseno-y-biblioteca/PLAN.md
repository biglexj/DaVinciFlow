# Relevo de diseño y biblioteca

Fecha: 2026-09-07. Proyecto: `D:\Proyectos\biglexj\DaVinciFlow`.

## Punto de partida

La versión previa está registrada localmente en e52a58a y 2a43069. La implementación actual incluye editor con cuatro pestañas, propuesta selectiva 1.1.0, compatibilidad 1.0.0 y biblioteca por categorías. Pasan 164 pruebas. No hay todavía una propuesta selectiva real aprobada: Gemini 3.8 respondió HTTP 503 y la interfaz recorta los controles inferiores.

El usuario pidió dejar el diseño preparado para un diseñador distinto. Este proceso entrega el encargo y la división del trabajo; no inicia un rediseño ni una migración física de archivos.

Corrección posterior del mismo 7 de septiembre: recuperar la disposición visual anterior, con navegación vertical a la izquierda y contenido a la derecha. Se descarta la barra superior de pestañas como diseño objetivo. Mantener las funciones nuevas en paneles internos de una sola ventana; ver las referencias del brief.

## Rumbo de producto

La transcripción es una fuente de tiempos y significado. El editor decide qué ideas merecen rótulo, con qué composición y sobre qué imagen, dejando también planos sin texto. El subtitulado completo queda como modo alternativo. Hasta tres capas son una capacidad, nunca una obligación de rellenar cada frase.

## Orden y responsables

| Bloque | Responsable | Entregable | Dependencia |
|---|---|---|---|
| D — Interfaz | Diseñador que asigne Biglex | [Brief de diseño](DESIGN_BRIEF.md), composición y revisión de todos los estados | Puede preparar diseño desde esta base |
| A — Recursos | Agente de biblioteca/integración | [Contrato y clasificación de assets](ASSETS.md), rutas verificadas e inventario revisable | Comparte nombres/estados con D; no depende de la estética final |
| F — Cierre funcional | Agente de LLM/Resolve | Propuesta selectiva real, aplicación revisada y reversión en una copia | D debe permitir acceder a todos los controles; A debe entregar recursos válidos si se usan |

Después de F, continuar los procesos existentes de [fase 2, sonido](../2026-09-06_fase-2_sonido-y-cierre-funcional/PLAN.md) y [fase 3, visuals](../2026-09-06_fase-3_visuals-desde-carpeta/PLAN.md). No crear implementaciones paralelas de sus motores.

## Propiedad de archivos

- D: `ui/widgets.py`, `ui/workbench_window.py` y presentación de `ui/editorial_window.py`, `ui/library_panel.py`, `ui/template_panel.py`.
- A: `assets/library.py`, `editorial/preferences.py` y adaptadores de catálogo. Coordinar cambios de `ui/library_panel.py` con D; no editarlo simultáneamente sin repartir funciones.
- F: `editorial/model.py`, `planner.py`, `service.py`, `writer.py` y pruebas relacionadas. El diseñador no cambia huellas, tiempos, validadores ni registros de ejecución.
- Entradas: `--ui`, `--editorial-ui` y el menú de Resolve deben abrir el mismo espacio con navegación lateral y panel central intercambiable.

## Fuera del encargo de diseño

No cambiar de framework, proveedor, modelo ni formato de propuestas por estética. No convertir nuevamente el editor en varias ventanas. No conservar las pestañas horizontales superiores como diseño principal: Biglex eligió la estructura anterior con barra lateral. No mezclar música y efectos por tener la misma extensión. No mover la biblioteca externa ni sustituir títulos propios por imitaciones de la referencia.

## Primera acción al retomar

Leer TASKS y VALIDATION, comprobar Git y tomar el bloque asignado. Para diseño: reproducir primero el recorte del panel de revisión. Para recursos: usar la ruta real con tilde. Para LLM: probar el modelo exacto y registrar el resultado sin fallback silencioso.
