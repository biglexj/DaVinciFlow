# Acerca de DaVinci Flow — Validación

- Proceso: `2026-09-08_acerca-de-modal-insignia`
- Fecha: `2026-09-08`

## Resumen de Verificaciones

| Caso / Prueba | Método | Resultado Esperado | Resultado Real |
|---|---|---|---|
| Reemplazo en barra lateral | Inspección de código y test | Botón interactivo «Acerca de» en el pie de la barra lateral con hover y tooltip | Superado (`test_sidebar_about_button_and_hover`) |
| Apertura modal Acerca de | Prueba unitaria y llamada | Despliegue de `ft.AlertDialog` centrado con branding y metadatos | Superado (`test_about_dialog_presentation_and_channels`) |
| Enlaces oficiales de soporte | Invocación de callbacks | Redirección a donaciones, buymeacoffee, feedback y github | Superado (`test_about_dialog_presentation_and_channels`) |
| Suite completa de tests | `unittest discover -s tests` | 100% de tests pasando sin regresiones | Superado (187 pruebas satisfactorias en 2.11s) |

## Evidencia

```text
Ran 187 tests in 2.110s
OK
```

- Componente `AboutDialog` creado en `src-flet/features/about/about_dialog.py`:
  - Enlaces canónicos: `https://www.biglexj.com/donaciones`, `https://buymeacoffee.com/biglexj`, `https://github.com/biglexj/DaVinciFlow/issues`, `https://github.com/biglexj`.
  - Iconos y tokens: Material Expressive, dark palette `#121518`, `#00C7B1`.
  - Autoría: `biglexj (2026)`, Licencia MIT, versión dinámica `davinci_flow.__version__`.
  - Datos de runtime: `CPython · Flet v0.86.5` en el diálogo.
- Barra lateral en `src-flet/app/app.py`:
  - `self.about_btn` ubicado al pie tras el `expand=True`, sustituyendo el texto estático `CPython · Flet`.
  - Microinteracción de hover con cambio sutil a `#173A35` y color de acento `#00C7B1`.
- Vista de Ajustes en `src-flet/features/settings/settings_view.py`:
  - Tarjeta «Acerca de DaVinci Flow» con botón de acceso directo para cumplimiento integral con `core_profile.md` y `agent.md`.
