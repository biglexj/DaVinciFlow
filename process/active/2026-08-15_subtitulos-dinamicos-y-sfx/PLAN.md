# Subtítulos dinámicos y SFX — Plan

- Estado: `DRAFT`
- Fecha: `2026-08-15`
- Proyecto: `DaVinci Flow`
- Hito objetivo: `MVP funcional de subtítulos dinámicos multicapa y SFX`
- Proceso precedente: `process/active/2026-08-15_base-inicial/`
- Commit base conocido: `2a8380a`

## 1. Propósito del documento

Este proceso define cómo continuar DaVinci Flow sin depender del historial del chat. Toda persona o agente que retome el proyecto debe poder identificar:

- qué existe realmente;
- qué permanece sin validar;
- cuál es la arquitectura acordada;
- qué orden de implementación debe seguirse;
- qué decisiones requieren aprobación humana;
- qué evidencia demuestra cada avance;
- qué funciones quedan expresamente fuera del primer MVP.

Este documento es una propuesta. No autoriza por sí mismo la implementación: la casilla de autorización al final debe aprobarse primero.

## 2. Visión del producto

DaVinci Flow leerá los subtítulos nativos ya creados por DaVinci Resolve y los transformará en composiciones dinámicas de texto organizadas por jerarquía narrativa. El sistema podrá proponer efectos sonoros, permitir una revisión previa y generar únicamente elementos propios sobre pistas dedicadas, sin alterar los clips ni los subtítulos originales.

La automatización debe ahorrar trabajo repetitivo sin sustituir el criterio editorial de Biglex.

## 3. Estado confirmado al iniciar este proceso

### 3.1 Implementado

- Proyecto Python `0.1.0` con estructura modular.
- Python 3.11 de 64 bits como stack inicial.
- Adaptador para localizar la API de scripting de Resolve.
- Protección para no cargar la biblioteca nativa cuando Resolve está cerrado.
- Lectura de una pista de subtítulos mediante objetos simulados.
- Modelo interno `SubtitleCue` independiente de Resolve.
- Entrada de diagnóstico por terminal.
- Cuatro pruebas unitarias correctas.
- Repositorio Git local sobre `main`.

### 3.2 No validado todavía

- Conexión real con Resolve 21 en ejecución.
- Lectura real del texto mediante `TimelineItem.GetName()`.
- Inicio, final y orden reales de los subtítulos.
- Comportamiento con varias pistas de subtítulos.
- Inserción de títulos Fusion en posiciones arbitrarias.
- Escritura y eliminación segura de elementos generados.
- Interfaz dentro del menú de Resolve.

### 3.3 No implementado

- División semántica en contexto, principal y complemento.
- Temas visuales Aurora y Ely.
- Plantillas Fusion `.setting`.
- Previsualización por marcadores.
- Regeneración parcial e idempotencia.
- Biblioteca y motor SFX.
- Integración opcional con una API de lenguaje.
- Instalador o empaquetado para usuarios.

## 4. Fuentes de verdad y precedencia

En caso de conflicto, utilizar este orden:

1. Instrucción actual y explícita de Biglex.
2. Comportamiento comprobado en la instalación real de DaVinci Resolve 21.
3. Configuración ejecutable y pruebas del repositorio.
4. Este proceso y la documentación local del proyecto.
5. Documentación oficial instalada con DaVinci Resolve.
6. Documentación Core compartida.
7. Capturas o productos de referencia.

Las capturas del producto externo sirven exclusivamente como referencia funcional. Está prohibido copiar su marca, interfaz, recursos, textos comerciales, colores o biblioteca SFX.

## 5. Decisiones técnicas ya adoptadas

- Lenguaje principal: Python.
- Plantillas visuales futuras: Fusion `.setting` o macros equivalentes.
- Fuente temporal: subtítulos nativos existentes en Resolve.
- Arquitectura: modular; el futuro archivo visible en el menú de Resolve será únicamente un iniciador pequeño.
- Modelos locales: descartados para este hito.
- IA: opcional, mediante API y detrás de un contrato independiente del proveedor.
- Seguridad: ninguna clave dentro del repositorio, los registros o las plantillas.
- Edición: no destructiva y reversible.
- Identidad: solo colores, tipografías y recursos oficiales de Aurora o Ely.

## 6. Alcance del MVP

### 6.1 Incluye

- Seleccionar una pista de subtítulos existente.
- Procesar toda la línea de tiempo o un intervalo elegido.
- Convertir cada subtítulo en un bloque interno normalizado.
- Clasificar el texto en hasta tres roles: contexto, principal y complemento.
- Permitir que un rol quede vacío cuando el bloque no necesite tres capas.
- Previsualizar el plan antes de modificar la línea de tiempo.
- Generar títulos sobre pistas propias y nombradas.
- Aplicar un tema oficial seleccionado.
- Proponer e insertar SFX desde una biblioteca propia.
- Regenerar un intervalo sin reprocesar toda la línea de tiempo.
- Retirar únicamente los elementos creados por DaVinci Flow.
- Registrar la ejecución para evitar duplicados.
- Mostrar errores comprensibles y conservar un registro técnico sin secretos.

### 6.2 No incluye en el primer MVP

- Transcribir audio.
- Traducir subtítulos.
- Descargar recursos desde Internet.
- Generar imágenes, vídeo o audio con IA.
- Analizar rostros o seguir sujetos.
- Crear B-roll automáticamente.
- Sincronización musical avanzada por ritmo.
- Colaboración en la nube.
- Tienda de paquetes o sistema de pagos.
- Compatibilidad macOS declarada como validada.
- Publicación o instalador final.

## 7. Arquitectura objetivo

La estructura exacta podrá ajustarse durante la implementación, pero las responsabilidades deben conservarse:

```text
src/davinci_flow/
├── entrypoints/               Iniciadores de terminal y menú de Resolve
├── application/               Casos de uso y coordinación
├── subtitles/                 Bloques, normalización y clasificación
├── generation/                Planes, ejecución, reversión e idempotencia
├── themes/                    Tokens y validación de identidad
├── sfx/                       Catálogo, selección y reglas de densidad
├── resolve/                   Adaptación exclusiva de la API de Resolve
└── language/                  Contrato opcional para clasificación remota
```

No se crearán todas estas carpetas de una sola vez. Cada módulo aparecerá únicamente cuando comience su fase y exista una responsabilidad real.

### 7.1 Reglas de dependencia

- El dominio no importa `DaVinciResolveScript`.
- La capa `resolve/` traduce objetos nativos a modelos internos.
- La clasificación no inserta clips ni conoce pistas físicas.
- El generador recibe un plan validado; no decide el significado del texto.
- La interfaz coordina casos de uso; no contiene lógica de análisis.
- El adaptador de lenguaje devuelve datos estructurados; nunca controla Resolve.

## 8. Modelo conceptual de datos

### 8.1 `SubtitleCue`

Ya existe. Representa texto, inicio, final e índice de pista.

### 8.2 `CaptionBlock`

Representará:

- identificador estable;
- subtítulos de origen;
- intervalo temporal;
- texto original intacto;
- texto normalizado;
- contexto;
- principal;
- complemento;
- intención narrativa;
- confianza de clasificación;
- estilo propuesto;
- propuesta SFX opcional;
- estado de revisión.

### 8.3 `GenerationPlan`

Representará una ejecución todavía no aplicada:

- identificador de ejecución;
- proyecto y línea de tiempo de origen;
- identificador estable de la línea de tiempo;
- pista y rango procesados;
- velocidad de fotogramas;
- resolución y orientación;
- tema seleccionado;
- asignación lógica de pistas;
- bloques ordenados;
- huella del contenido de origen;
- versión del formato del plan.

### 8.4 `ThemeTokens`

Contendrá exclusivamente valores oficiales:

- colores permitidos;
- tipografías permitidas;
- tamaños y jerarquías;
- posiciones y márgenes seguros;
- nombres de plantillas Fusion;
- límites de movimiento;
- comportamiento horizontal y vertical.

### 8.5 `AssetDescriptor`

Para cada SFX:

- identificador interno;
- ruta relativa al paquete;
- categoría y etiquetas;
- duración;
- ganancia recomendada;
- tiempo de reutilización;
- contextos permitidos y prohibidos;
- autoría, licencia y fuente.

### 8.6 `GenerationRecord`

Permitirá regenerar o retirar:

- ejecución que creó cada elemento;
- bloque de origen;
- pista, inicio y final;
- recurso o plantilla utilizada;
- identificador del elemento nativo cuando Resolve lo proporcione;
- estado aplicado, reemplazado o retirado.

## 9. Organización lógica de pistas

DaVinci Flow no debe asumir que V2, V3 o V4 están libres. Calculará posiciones disponibles por encima de las pistas existentes o utilizará una pista elegida por el usuario.

### Pistas visuales

- `DF_CONTEXT`: contexto y conectores.
- `DF_MAIN`: palabra o idea dominante.
- `DF_ACCENT`: complemento o segunda jerarquía.
- `DF_VISUAL_FX`: formas y decoraciones opcionales.

### Pista de audio

- `DF_SFX`: efectos sonoros generados por DaVinci Flow.

### Fuente

- La pista nativa de subtítulos permanece intacta.
- Ocultarla o conservarla visible será una decisión configurable, nunca una modificación irreversible.

## 10. Flujo funcional completo

### Paso 1 — Preflight

- Confirmar que Resolve está abierto.
- Confirmar proyecto y línea de tiempo activos.
- Leer velocidad de fotogramas, resolución e inicio de la línea de tiempo.
- Enumerar pistas de subtítulos.
- Detectar pistas bloqueadas y nombres reservados.
- Confirmar el rango que se procesará.
- Recomendar duplicar la línea de tiempo durante las primeras versiones.

### Paso 2 — Ingesta

- Leer la pista seleccionada.
- Conservar texto y tiempos originales.
- Ordenar por inicio.
- Detectar vacíos, solapamientos y duraciones anómalas.
- Crear una huella estable de los subtítulos y el rango.

### Paso 3 — Normalización

- Limpiar espacios sin destruir tildes, eñes, signos o números.
- Conservar nombres propios y negaciones.
- Evitar separar cantidades, fechas y expresiones cortas.
- Marcar bloques demasiado largos o demasiado breves para revisión.

### Paso 4 — Clasificación determinista

- Seleccionar la idea principal mediante reglas comprobables.
- Separar contexto y complemento solo cuando aporten jerarquía.
- Evitar la división mecánica cada cierto número de palabras.
- Permitir bloques de una, dos o tres capas.
- Registrar el motivo de cada clasificación.

La clasificación inicial debe funcionar sin conexión y sin API de lenguaje.

### Paso 5 — Clasificación opcional mediante API

La API de lenguaje se evaluará después de que las reglas locales funcionen. Si se activa:

- recibirá únicamente identificadores temporales y texto necesario;
- no recibirá rutas, nombres de proyecto, audio ni vídeo;
- responderá mediante un esquema estructurado y versionado;
- tendrá límite de tiempo, reintentos y presupuesto configurables;
- almacenará resultados reutilizables por huella de texto;
- tendrá un adaptador independiente del proveedor;
- nunca insertará elementos en Resolve;
- caerá automáticamente al motor local ante error o respuesta inválida.

El modelo y proveedor exactos solo se registrarán cuando esta función se active.

### Paso 6 — Aplicación del tema

- Elegir Aurora o Ely.
- Cargar únicamente tokens oficiales.
- Aplicar la plantilla correspondiente a cada rol.
- Validar orientación, márgenes y zona segura.
- Rechazar cualquier color, tipografía o plantilla no registrada.

El tema Ely puede partir de su paleta ya documentada. El tema Aurora no se implementará hasta identificar su fuente oficial de colores y tipografías.

### Paso 7 — Propuesta SFX

- Analizar intención narrativa, pausa posterior, signo de interrogación, contraste y cercanía a un corte.
- Asignar una categoría, no un archivo específico, durante la primera decisión.
- Aplicar límites de densidad y reutilización.
- Bloquear SFX cómicos en perfiles reflexivos o rangos protegidos.
- Seleccionar una variante disponible y mostrarla para revisión.

El tiempo funciona como límite de densidad, no como disparador automático.

### Paso 8 — Previsualización

- Crear un `GenerationPlan` sin modificar la línea de tiempo.
- Mostrar por bloque: tiempos, roles, plantilla, SFX y motivo.
- Permitir aprobar, desactivar o corregir cada bloque.
- Poder regenerar la clasificación sin releer subtítulos.
- Opcionalmente representar propuestas mediante marcadores propios.

### Paso 9 — Generación

- Crear o reutilizar pistas dedicadas.
- Insertar títulos Fusion en el tiempo exacto.
- Configurar texto, duración y tokens permitidos.
- Insertar SFX aprobados en `DF_SFX`.
- Registrar cada elemento creado.
- Interrumpir de forma segura ante un fallo y conservar el registro parcial.

### Paso 10 — Regeneración y retirada

- Comparar la huella de los subtítulos actuales con la ejecución anterior.
- Detectar bloques nuevos, modificados y eliminados.
- Reemplazar únicamente el rango seleccionado.
- Impedir duplicados en una segunda ejecución.
- Retirar solo elementos registrados por DaVinci Flow.
- No borrar pistas o clips ajenos aunque compartan una posición temporal.

## 11. Perfil editorial inicial

Los valores exactos se calibrarán con contenido real. El sistema debe ofrecer perfiles configurables:

- `Reflexivo`: movimiento suave, menor densidad y SFX muy limitados.
- `Natural`: jerarquía clara sin cambios constantes.
- `Dinámico`: mayor rotación visual y más oportunidades SFX.
- `Educativo`: prioridad para conceptos, datos y cifras.
- `Vídeo corto`: bloques breves y ritmo elevado.

Ningún perfil puede romper el Brand Guard ni superar los límites de seguridad.

## 12. Interfaz prevista

La interfaz se implementará después del motor y se limitará a coordinar casos de uso.

### Flujo por pasos

1. Fuente: línea de tiempo, pista y rango.
2. Tema: Aurora o Ely, orientación y perfil.
3. Análisis: bloques y jerarquía propuesta.
4. SFX: biblioteca, intensidad y exclusiones.
5. Revisión: correcciones y aprobación por bloque.
6. Generación: resumen, progreso y resultado.

### Acciones esenciales

- Analizar sin aplicar.
- Generar selección.
- Regenerar selección.
- Cambiar tema sin releer subtítulos.
- Desactivar un bloque.
- Retirar una ejecución.
- Abrir el registro de validación técnica.

La viabilidad de `UIManager` desde Python debe comprobarse en la instalación real antes de diseñar la interfaz final.

## 13. Seguridad, privacidad y rendimiento

- No modificar el vídeo, audio ni subtítulos originales.
- No almacenar claves en archivos versionados.
- No registrar texto completo si el modo privado lo desactiva.
- No enviar contenido a una API sin activación explícita.
- Procesar bloques de forma secuencial y acotada.
- No cargar modelos locales.
- Evitar una composición Fusion por palabra cuando una plantilla pueda animar internamente el bloque.
- Medir tiempo y memoria sobre una línea de tiempo real antes de fijar límites definitivos.
- Limpiar archivos temporales al finalizar o fallar.

## 14. Estrategia de ramas y commits

### Rama estable

- `main` conserva únicamente hitos verificados y documentados.

### Desarrollo propuesto

1. Cerrar la validación real de la base sobre `main`.
2. Crear `feature/dynamic-caption-mvp` al comenzar el motor de bloques.
3. Realizar checkpoints locales por fase verificable.
4. Integrar en `main` únicamente después de superar las pruebas del motor y la generación en una copia de la línea de tiempo.
5. Crear `feature/sfx-engine` después de estabilizar los títulos multicapa.
6. Crear la interfaz después de estabilizar ambos motores.

No se realizará push, publicación o lanzamiento sin una solicitud explícita.

## 15. Fases de implementación y puertas

### Fase 0 — Compatibilidad real de la base

Resultado: lectura real y reproducible de subtítulos.

Puerta G0:

- Resolve 21 responde.
- Se identifican proyecto, línea de tiempo y pista.
- Texto y tiempos coinciden con la interfaz.
- La operación es de solo lectura.

Sin G0 no se implementa escritura sobre la línea de tiempo.

### Fase 1 — Dominio y plan de generación

Resultado: `CaptionBlock` y `GenerationPlan` producidos sin Resolve.

Puerta G1:

- Reglas deterministas probadas.
- Casos en español con tildes y eñes correctos.
- Serialización y huellas estables.
- Ninguna dependencia del proveedor de IA.

### Fase 2 — Prueba vertical de Fusion

Resultado: un único bloque de prueba generado en una copia de la línea de tiempo.

Puerta G2:

- Inserción exacta dentro de un fotograma de tolerancia.
- Texto y duración correctos.
- Uso exclusivo de una plantilla propia mínima.
- Retirada segura del bloque creado.

### Fase 3 — Generación multicapa y Brand Guard

Resultado: contexto, principal y complemento en pistas lógicas.

Puerta G3:

- Una, dos y tres capas funcionan.
- Pistas existentes permanecen intactas.
- Solo aparecen colores y tipografías permitidos.
- Horizontal y vertical se revisan visualmente.
- Reejecución sin duplicados.

### Fase 4 — Previsualización y regeneración parcial

Resultado: revisar antes de aplicar y cambiar únicamente un intervalo.

Puerta G4:

- Un bloque corregido se regenera aisladamente.
- Los demás bloques conservan su identidad y posición.
- Una retirada elimina solo la ejecución seleccionada.
- Los fallos parciales son recuperables.

### Fase 5 — Motor SFX

Resultado: efectos sonoros propios, aprobables y limitados.

Puerta G5:

- Catálogo con licencia y metadatos completos.
- Preescucha y sustitución manual.
- Límites de densidad y repetición comprobados.
- Volumen razonable y sincronización visual revisada.
- Ningún SFX aparece en un rango bloqueado.

### Fase 6 — Interfaz guiada

Resultado: flujo completo accesible sin terminal.

Puerta G6:

- Navegación por pasos.
- Errores claros y recuperación.
- Progreso sin bloquear innecesariamente Resolve.
- La interfaz no contiene lógica del dominio.

### Fase 7 — Evaluación de API de lenguaje

Resultado: decisión informada de adoptar o descartar la clasificación remota.

Puerta G7:

- Mejora medible frente a reglas locales.
- Privacidad, coste, latencia y respaldo documentados.
- Esquema estructurado validado.
- Aprobación explícita de Biglex.

La API de lenguaje no es requisito para declarar funcional el MVP local.

## 16. Riesgos principales

### API de Resolve incompleta o inconsistente

Mitigación: crear pruebas verticales pequeñas antes de diseñar abstracciones grandes; conservar una capa de adaptación aislada.

### Plantillas Fusion demasiado pesadas

Mitigación: una composición por rol y bloque, animación interna cuando sea posible, caché y pruebas sobre el hardware real.

### División semántica incorrecta

Mitigación: reglas explicables, confianza visible, corrección manual y API opcional como mejora, no dependencia.

### Duplicados o eliminación accidental

Mitigación: identificadores de ejecución, pistas propias, huellas de origen, registro de elementos y pruebas de reejecución.

### Identidad visual contaminada

Mitigación: Brand Guard con lista permitida; ningún color o recurso puede entrar directamente desde una plantilla externa.

### Biblioteca SFX sin derechos claros

Mitigación: exigir licencia, autoría y fuente en cada descriptor; rechazar recursos incompletos.

### Coste o indisponibilidad de una API de lenguaje

Mitigación: motor determinista completo, caché, límites configurables y proveedor intercambiable.

### Consumo de RAM

Mitigación: procesamiento secuencial, dependencias mínimas, ninguna IA local y medición en cada fase vertical.

## 17. Criterios de finalización del proceso

- [ ] G0 a G6 aprobadas con evidencia reproducible.
- [ ] Títulos multicapa generados y revisados en una copia real de la línea de tiempo.
- [ ] Subtítulos, vídeo y audio originales intactos.
- [ ] Regeneración parcial e idempotencia demostradas.
- [ ] Retirada segura demostrada.
- [ ] Tema oficial completo sin valores inventados.
- [ ] Biblioteca SFX propia y documentada.
- [ ] Pruebas automatizadas y manuales registradas en `VALIDATION.md`.
- [ ] README y documentación de instalación actualizados.
- [ ] Decisión sobre API de lenguaje registrada, aunque sea aplazarla.
- [ ] Aprobación final de Biglex registrada en `APPROVAL.md`.

## 18. Protocolo de continuidad

Quien retome el proceso debe:

1. Leer `README.md` y `.agents/rules/core_profile.md`.
2. Leer los cuatro archivos de este proceso.
3. Revisar el proceso precedente y confirmar si G0 sigue pendiente.
4. Ejecutar pruebas antes de modificar código.
5. Consultar `git status` y el último commit.
6. Trabajar únicamente en la primera tarea pendiente de `TASKS.md`.
7. Registrar comandos, resultados y límites en `VALIDATION.md`.
8. No marcar una puerta como aprobada basándose solo en pruebas simuladas.
9. No saltar a SFX, interfaz o IA antes de estabilizar el generador multicapa.
10. Detenerse en toda decisión señalada en `APPROVAL.md`.

## 19. Autorización

- [ ] Plan aprobado para ejecución.

La aprobación autoriza comenzar por la Fase 0. No autoriza automáticamente todas las fases ni una publicación.
