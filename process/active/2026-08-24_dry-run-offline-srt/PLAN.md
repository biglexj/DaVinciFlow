# Previsualización Offline (Dry-Run con SRT sin Resolve) — Plan

- Estado: `COMPLETED`
- Fecha: `2026-08-24`
- Proyecto: `DaVinci Flow`

## Objetivo

Permitir que `davinci-flow --generate --dry-run --srt <archivo>` genere el registro completo de previsualización (capas + SFX + tiempos) sin exigir una sesión activa de DaVinci Resolve.

## Alcance

- Incluye:
  - Timeline sintética (`_HeadlessTimeline`) en `davinci_flow/application.py` para el dry-run sin contacto con el Media Pool.
  - `generate_from_active_timeline` deja de llamar incondicionalmente a `connect_to_resolve()` cuando se trata de un dry-run sobre un SRT.
- No incluye:
  - La generación física real (sigue requiriendo Resolve abierto).
  - La inserción de marcadores reales, que solo ocurre fuera de dry-run.

## Criterios de finalización

- [x] `--generate --dry-run --srt` devuelve un record con estado `dry_run` sin Resolve abierto.
- [x] La ruta sin `--srt` continúa exigiendo conexión a Resolve.
- [x] 100% de las pruebas unitarias pasan.
