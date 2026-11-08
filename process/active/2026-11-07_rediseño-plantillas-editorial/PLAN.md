# Rediseño y Clasificación de Plantillas Text+ — Plan

- Estado: `DRAFT`
- Fecha: `2026-11-07`
- Responsable: `biglexj`
- Proyecto: `DaVinci Flow`

## Objetivo

Reemplazar las plantillas actuales de títulos (`basic_titles`) por una suite normalizada, coherente y alineada con los temas oficiales (**Ely** y **Aurora**), corrigiendo inconsistencias tipográficas, jerarquías rotas y rescates cromáticos arbitrarios.

---

## Diagnóstico de Plantillas Actuales

| Plantilla Actual | Inconsistencia Detectada | Impacto Editorial |
|---|---|---|
| `Shorts Bold` | Énfasis usa amarillo no normativo (`#FFFF00`); falta emparejamiento tipográfico con contexto. | Rompe la identidad de marca (Brand Guard) y satura en pantallas móviles. |
| `YouTube Dinámico` | Usa `Montserrat` indistintamente en todas las capas; trazos y sombras con parámetros dispares. | Pérdida de jerarquía de lectura y baja diferenciación visual. |
| `Noticiero TV` | Posicionamiento Y estático sin consideración de safe zones para resoluciones mixtas; estilo excesivamente pesado. | Puede invadir tercios inferiores o solaparse con grafismos de canal. |
| `Text+ básico` | Valores por defecto planos sin afinado de kerning, padding ni contraste. | Aspecto genérico desalineado del estándar visual de DaVinci Flow. |

---

## Clasificación Propuesta

### 1. Por Formato y Caso de Uso (Objetivo)
- **Shorts / Reels / TikTok (9:16)**:
  - *Objetivo*: Captura de atención inmediata, lectura rápida en centro/tercio medio seguro (`Y: 0.28 - 0.38`).
  - *Jerarquía*: Énfasis potente, contorno estricto anti-fondo y sombras profundas pero suaves.
- **YouTube Dinámico / Video Largo (16:9)**:
  - *Objetivo*: Acompañamiento narrativo elegante, lectura fluida sin fatiga en tercio inferior (`Y: 0.15 - 0.20`).
  - *Jerarquía*: Textos limpios, espaciado equilibrado y sutil realce de palabras clave.
- **Editorial / Noticiero / Documental**:
  - *Objetivo*: Rigor informativo, sobriedad y máxima legibilidad.
  - *Jerarquía*: Contexto superior identificativo (`Inter`), titular principal rotundo (`Montserrat`/`Poppins`).

### 2. Por Tokens de Marca (Brand Guard)
- **Tema Ely**:
  - Fuente principal / énfasis: `Montserrat` (Black / ExtraBold).
  - Fuente contexto: `Inter` (Medium).
  - Paleta: Primario `#00C7B1` (Teal), Secundario `#FB7793`, Acento `#FFE6CA`, Texto `#FFFFFF`, Contexto `#6E7179`.
- **Tema Aurora**:
  - Fuente principal / énfasis: `Poppins` (Bold / ExtraBold).
  - Fuente contexto: `Inter` (Regular / Medium).
  - Paleta: Primario `#F83C78` (Magenta), Secundario `#389EA2`, Acento `#00AAFF` (Cyan), Texto `#FFFFFF`, Contexto `#CBD5E1`.

### 3. Por Capa de Línea de Tiempo (Multicapa 3-Track)
- `DF_CONTEXT`: Información secundaria / metadata (menor tamaño, color neutro tenue).
- `DF_MAIN`: Frase nuclear (tamaño medio-alto, blanco de alto contraste).
- `DF_ACCENT`: Término clave / gancho (tamaño mayor, color de acento oficial, soporte para animación pop/bounce).

---

## Alcance

- Incluye:
  - Generación de los nuevos archivos `.setting` en `src/davinci_flow/editorial/basic_titles/` clasificados por tema y objetivo.
  - Actualización de los presets en [fusion_template.py](file:///d:/Proyectos/biglexj/DaVinciFlow/src/davinci_flow/generation/fusion_template.py) y catálogo en [catalog_view.py](file:///d:/Proyectos/biglexj/DaVinciFlow/src-flet/features/catalog/catalog_view.py).
  - Pruebas automatizadas de conformidad con `BrandGuardError` y tokens.
- No incluye:
  - Modificación del motor de subtítulos SRT o de la API de Resolve.

---

## Criterios de Finalización

- [ ] Todas las plantillas en `basic_titles` validan contra `ThemeTokens` de Ely o Aurora.
- [ ] No existen colores fuera de la paleta oficial ni combinaciones de fuentes fuera de `Montserrat`, `Poppins` e `Inter`.
- [ ] Las 3 capas (`DF_CONTEXT`, `DF_MAIN`, `DF_ACCENT`) cuentan con posiciones coherentes en coordenadas normalizadas.
- [ ] La suite de pruebas de `tests/` pasa sin regresiones (`mise test` o `python -m unittest`).
- [ ] La interfaz Flet (`catalog_view.py`) refleja las nuevas categorías y muestras previas.
