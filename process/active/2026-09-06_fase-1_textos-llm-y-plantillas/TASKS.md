# Fase 1 — Subtítulos, LLM y plantillas reales — Tareas

Estado: implementación y muestra real comprobadas; aceptación visual de Biglex pendiente.

- [x] T01 — Auditar el recorrido histórico y dirigir el botón principal a la revisión editorial.
- [x] T02 — Inventario de 332 títulos instalados, tres básicos incluidos y seis plantillas del Media Pool; matriz real en MEDIA_POOL_VALIDATION.json.
- [x] T03 — Contrato editorial 1.0.0 y adaptación a GenerationPlan sin cambiar el esquema histórico.
- [x] T04 — Propuesta LLM con subtítulos/cortes nativos, validación y llamadas reales a gemini-3.5-flash.
- [x] T05 — Editor compartido, persistencia, revisión por bloque, selección de plantillas y acceso desde ambas interfaces.
- [x] T06 — Inserción exacta de 27 clips en la copia de prueba, reutilización sin duplicados y reversión comprobada.
- [x] T07 — Resolver defectos encontrados y documentar contratos y límites para fase 2.
- [ ] T08 — Biglex revisa la muestra durante reproducción y decide ajustes de legibilidad y entradas/salidas. No inferir aceptación a partir de las pruebas técnicas.

Evidencia: VALIDATION.md y LIVE_VALIDATION.md. Implementación en src/davinci_flow/editorial y ui/editorial_window.py. No se han implementado nuevos SFX ni visuals en esta fase.
