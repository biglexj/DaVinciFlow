# Prueba real en Resolve — 6 de septiembre de 2026

Responsable técnico: Codex, con control autorizado por Biglex. Entorno: Windows, Python 3.13, DaVinci Resolve Studio 21.0.0b.33, 1920 × 1080, 24 fps.

Proyecto: Crear proyecto 1. Original: Timeline 1. Toda inserción de prueba se hizo en la copia **DF — Prueba fase 1 — 2026-09-06**, ID cc07b26c-e1f5-4b9d-9908-a9e6d13cd445.

## Resultado observado

- Se reconocen las seis composiciones de DaVinciFlow/biglexj. En las seis se verificaron copia, cambio de texto con tildes, conservación del inventario de nodos y texto original intacto al volver a copiarlas. Los pequeños clips de sondeo se retiraron.
- Se aplicaron tres capas simultáneas con biglexpe-superior, biglexpe y biglexpe-inferior. Captura visual y fotograma exportado confirmaron posiciones, texto y aspecto originales.
- Se importó Rise Fade desde Templates.drfx. Se comprobó control expuesto, imagen en el visor, nodos Follower y KeyframeStretcher y variación de la curva Opacity1. Una frase larga desborda su diseño: en la muestra final se utiliza con «¡Qué buen servicio!».
- Text+ básico Principal se aplicó y se verificó visualmente con «escucha esto, ya se». Los básicos Contexto y Énfasis se incluyen en el catálogo, pero no tienen prueba visual individual en esta sesión.
- La LLM gemini-3.5-flash recibió subtítulos reales. Las propuestas originales se guardaron y se revisaron antes de escribir. Se corrigieron agrupaciones poco útiles, conservando las palabras originales.
- Muestra final: subtítulos 1–16, 15 incluidos, 27 clips; el subtítulo 3, duplicado y de dos fotogramas, está excluido de la propuesta. Los intervalos son los nativos; no se corrigió el hueco existente en el montaje.
- Posiciones y duraciones verificadas en Resolve, incluidas las entradas 86411–86458 y 86466–86489. Reaplicar conserva los mismos 27 IDs, sin duplicados.
- Reversión probada por el servicio: retiró únicamente la ejecución de prueba. Después se dejó la muestra final aplicada para revisión.
- Prueba de interfaz: el botón Revisar y generar con LLM abre el editor, captura 20 subtítulos y seis plantillas del proyecto (más tres básicos). Abrir propuesta restauró los 16 bloques revisados; Aplicar confirmó 27 elementos sin duplicarlos.
- Al revisar el original, sus pistas DF_CONTEXT, DF_MAIN y DF_ACCENT seguían vacías. Audio original conservado: dos clips en A1 y siete SFX previos en A2. No se añadieron sonidos en esta fase.

## Fallos encontrados y corregidos

1. La imagen auxiliar DF_Fusion_Title.png se catalogaba como plantilla: ahora se filtran los tipos que no son títulos/Fusion.
2. El portador de imagen fija podía superar el intervalo solicitado. Se utiliza AVI mínimo con duración real y se rechaza cualquier duración de vídeo distinta.
3. En esta versión de Resolve, endFrame=46 devuelve 46 fotogramas. El adaptador se corrigió y comprueba el resultado exacto.
4. Algunas macros declaran Outputs con una tabla normal. El lector ahora acepta ambas formas.
5. Resolve importaba la macro con MediaOut desconectado. Se enlaza y verifica su salida de imagen mediante la API; se comprueba el enlace de salida además del resultado de importación.
6. El botón principal todavía ejecutaba el generador histórico. Ahora abre captura y revisión LLM.
7. Los recursos generados se guardan en .davinci_flow/generated; los portadores de esta muestra se trasladaron allí y se reenlazaron antes de guardar el proyecto.
8. El registro editorial se separa por proyecto y secuencia para que una ejecución anterior de otra secuencia no bloquee la actual.

## Evidencia y entrega

MEDIA_POOL_VALIDATION.json contiene la matriz de las seis plantillas. SAMPLE_EXECUTION.json contiene la ejecución final. Los JSON detallados, propuestas originales/revisadas, composición de diagnóstico y fotogramas exportados permanecen en temp/editorial-phase1/live, fuera del control de versiones. No se versionan composiciones del usuario ni fotogramas personales.

El registro operativo de la muestra está en la carpeta personal .davinci_flow/records/editorial/0fdc4e0e829dc9a88acdee67bc914e66/last.json. La UI obtiene esta ruta por identidad de proyecto y secuencia.

## Límites pendientes

No equivale a certificar los 332 títulos instalados. Las animaciones con tiempos fijos necesitan revisión a distintas duraciones; no se promete ajuste automático ni reproducción fluida universal. Queda la aceptación visual de Biglex, la legibilidad de cada frase y la evaluación de las entradas/salidas durante reproducción. Se mantienen los subtítulos nativos y los SFX existentes. Dos pistas sonoras y regeneración selectiva corresponden a fase 2.

Comprobación posterior al reenlace: ReplaceClip restableció los nombres de los dos clips basados en AVI. Se restauraron por los IDs del registro; se comprobaron los 27 textos/composiciones y una nueva aplicación conservó exactamente los mismos 27 IDs. Proyecto guardado después de la verificación.
