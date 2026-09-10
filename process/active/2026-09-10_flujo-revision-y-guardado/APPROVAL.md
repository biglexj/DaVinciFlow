# Flujo de revisión y selector de rutas — Aprobación

- Estado: `PENDING`

## Controles

- [x] Validación técnica del agente (223/223 pruebas unitarias en verde).
- [ ] Validación funcional del tester.
- [ ] Aprobación final de Biglex.
- [ ] `ROADMAP.md` actualizado.
- [ ] Sesión cerrada con resumen breve.

## Decisión

- [ ] `APPROVED`
- [ ] `REWORK`
- [ ] `CANCELLED`
- [ ] `SUPERSEDED`

## Resumen

- Implementado cierre de tarjeta de revisión con deselección de fila en el editor.
- Agregado método `approve_all()` en modelo y controlador, botón "Aprobar todo" en UI y confirmación interactiva en `Aplicar revisión`.
- Soporte para navegación entre unidades lógicas de disco (C:, D:, etc.) y creación de carpetas ("Nueva carpeta") en el selector de rutas.

## Destino

- `APPROVED` con todos los controles completos → `process/completed/2026/`.
- `CANCELLED`, `SUPERSEDED` o cierre incompleto → `process/archive/2026/`.
- `REWORK` → permanece en `process/active/`.

Mueve la carpeta completa y no conserves una copia duplicada en `active`.
