# Acerca de DaVinci Flow — Modal e Insignia

- Estado: `IN_PROGRESS`
- Fecha: `2026-09-08`
- Proyecto: `DaVinci Flow`
- Autor: `biglexj`

## Objetivo

Implementar la sección e insignia oficial «Acerca de» en DaVinci Flow, reemplazando el texto estático de la barra lateral por un acceso interactivo y desplegando un diálogo modal enriquecido con información de versión, autoría, licencia, agradecimiento y canales oficiales de apoyo (Donaciones, Buy Me a Coffee, Feedback y GitHub).

## Alcance

- Incluye:
  - Reemplazo del elemento inferior de la barra lateral (`CPython · Flet`) por una insignia interactiva y estilizada de «Acerca de».
  - Creación del diálogo modal `AboutDialog` (o vista modular equivalente) alineado a las reglas del ecosistema y Material Expressive.
  - Inclusión de los cuatro canales oficiales de soporte y donaciones:
    - Donaciones Oficiales (Yape / Plin / Transferencias / Web): `https://www.biglexj.com/donaciones`
    - Buy Me a Coffee: `https://buymeacoffee.com/biglexj`
    - Enviar Feedback / Reportar Error: `https://github.com/biglexj/DaVinciFlow/issues`
    - Perfil de GitHub: `https://github.com/biglexj`
  - Inclusión de metadatos de versión (`davinci_flow.__version__`), licencia MIT y autoría `biglexj (2026)`.
  - Pruebas unitarias de integración de la UI para verificar la apertura y contenido del diálogo.
- No incluye:
  - Sistema de autoactualización en segundo plano (función no activa en DaVinci Flow según `core_profile.md`).

## Enfoque

1. Crear el componente modular `AboutDialog` en `src-flet/features/about/about_dialog.py` (o en `shared/`), respetando la paleta de colores y componentes del espacio de trabajo.
2. Actualizar la barra lateral en `src-flet/app/app.py` para reemplazar el pie estático por el botón / enlace «Acerca de» que dispara el modal.
3. Incorporar tests en `tests/test_desktop.py` para asegurar que el diálogo de «Acerca de» se instancie y despliegue adecuadamente sin regresiones.
4. Validar la ejecución completa de la suite de pruebas.

## Criterios de finalización

- [ ] Insignia «Acerca de» visible en la barra lateral en la posición señalada por el usuario.
- [ ] Modal interactivo que muestra versión, autoría, licencia y botones oficiales con `page.launch_url`.
- [ ] Pruebas unitarias existentes y nuevas ejecutadas exitosamente al 100%.
- [ ] Evidencia registrada en `VALIDATION.md` y `APPROVAL.md`.
