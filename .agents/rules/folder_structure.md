---
trigger: always_on
---

# Mapa de carpetas — DaVinci Flow

El árbol vigente aplica la [organización de proyectos](../../../Docs/global/architecture/project-structure.md) al repositorio Rust.

```text
DaVinciFlow/
├── Cargo.toml              # Paquete Rust y versión de GPUI
├── src/                    # Motor Rust y entrada nativa
│   ├── app/                # Vistas y acciones de GPUI por función
│   └── resolve_scripts/    # Operaciones ejecutadas por el MCP de Resolve
├── compat/python/
│   ├── bridge/             # Contratos locales de los adaptadores
│   ├── src/davinci_flow/   # Servicios pendientes de migración
│   └── tests/              # Pruebas de compatibilidad
├── assets/                 # Recursos maestros
├── docs/                   # Guías y arquitectura
├── process/                # Registro de trabajos
├── scripts/                # Arranque y tareas de Mise
└── target/                 # Artefactos de Cargo, ignorados por Git
```

En `main`, `mise dev` abre GPUI. En `v-python`, `mise dev` abre Flet 1.0.0 desde ese mismo checkout. La edición Flet está descontinuada.
