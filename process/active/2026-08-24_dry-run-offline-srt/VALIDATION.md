# Previsualización Offline (Dry-Run con SRT sin Resolve) — Validación

- Estado: `VERIFIED`

## Comprobaciones

- [x] V01 — Agente — `uv run python -m davinci_flow --generate --dry-run --srt temp/demo.srt`. Resultado: 17 elementos planificados con estado `dry_run`, sin Resolve abierto.
- [x] V02 — Agente — `--generate --dry-run --srt ... --add-markers`. Resultado: previsualización correcta (sin marcadores en dry-run).
- [x] V03 — Agente — `--generate --dry-run` sin `--srt`. Resultado: error controlado exigiendo sesión de Resolve.
- [x] V04 — Agente — Suite completa `uv run python -m unittest discover -s tests`. Resultado: 97/97 pruebas aprobadas.

## Registro de fallos

- Sin fallos pendientes.

## Nota de evidencia

Evidencia manual reciente: el pipeline por SRT (planificación, capas y SFX) funciona de extremo a extremo sin conexión a Resolve; materialización de SFX (WAV) verificada en `temp/sfx/`.
