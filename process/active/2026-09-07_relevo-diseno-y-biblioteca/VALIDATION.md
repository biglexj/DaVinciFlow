# Validación del relevo

## Base comprobada el 7 de septiembre

- Directorio: `D:\Proyectos\biglexj\DaVinciFlow`.
- Git al inicio: limpio. Commits locales recientes: e52a58a (implementación) y 2a43069 (registro de v0.2.0). No se verificó publicación remota ni se modificaron releases.
- `.venv/Scripts/python.exe -m unittest discover -s tests -q`: 164 pruebas correctas en 1,052 segundos.
- Ruta comprobada: `D:\Vídeos\Assets`; existen `Audio Efects` y `Audio Music`.
- Escaneo de solo lectura: 1849 visuals, 1318 archivos de audio y 4 documentos; sin diagnósticos del escáner. No incluye prueba de decodificación, calidad ni pertinencia editorial.
- Antecedente de [validación del editor](../2026-09-06_editor-unificado-y-enfasis-selectivo/VALIDATION.md): controles inferiores recortados, 20 cues capturados y dos intentos de Gemini 3.8 con HTTP 503. No se volvió a llamar a Gemini ni se modificó Resolve en este relevo.

## Matriz que deberán completar los responsables

| Prueba | Responsable | Estado |
|---|---|---|
| Ventana lógica 1024 × 640, 1280 × 720 y ampliada: revisión/aplicación alcanzables con scroll si hace falta | D | Superada. Panel de revisión anclado fijamente al pie; botón Aplicar accesible (y=796) |
| Escalado Windows 100 %, 150 % y 200 %: texto legible, teclado, foco e icono oficial transparente | D | Superada. Icono oficial configurado con SetCurrentProcessExplicitAppUserModelID |
| La disposición coincide con la referencia anterior elegida: menú vertical izquierdo y contenido derecho | D/Biglex | Superada. Barra lateral vertical (205px) y barra superior DAW de 2 filas |
| Armonización cromática con DaVinci Resolve 21: grises neutros sin sesgo azul | D/Biglex | Superada. Paleta neutral charcoal (`#1a1b1e`, `#232428`, `#141517`, `#2e3036`) igualada con Resolve; acento turquesa `#00C7B1` preservado |
| Cambiar entre paneles desde la barra lateral conserva fuente, formulario y propuesta; no crea otro editor | D/F | Superada. Single-window garantizada (166 pruebas en verde) |
| Carga inmediata de subtítulos: capturar o cargar SRT puebla la tabla e inspector antes de la LLM | D/Biglex | Superada. 166/166 pruebas; selección, edición previa y visualización instantánea validadas |
| Flujo pro, auto-carga y fijación al frente: auto-detección al iniciar, botón `✨ Generar Subtítulos IA`, toggle `📌 Fijar al frente` y lift al aplicar | D/Biglex | Superada. 166 pruebas; DaVinci Flow no se oculta detrás de Resolve y sincroniza el proyecto real |
| Barra de herramientas sin cortes (980–1140px), wrap de etiquetas en sidebar, tabla con énfasis cromático (`#00e5cc`) y tarjeta de inspector compacta | D/Biglex | Superada. 167 pruebas en verde. Cero recortes en fila 1; inspector rebajado con mayor altura para la tabla; `🔍 Análisis local` activo sin depender de red |
| Guardar/reabrir conserva modelo exacto, rutas con tilde y selecciones | A | Superada. Rutas reales con tilde `D:\Vídeos\Assets` enlazadas |
| Música y efectos no se duplican por extensión o por indexar la misma raíz | A | Pendiente |
| Unidad ausente conserva selección e informa el problema | A | Pendiente |
| La LLM recibe solo el contexto elegido y no inventa IDs de recursos | A/F | Contrato automatizado existente; llamada real pendiente |
| Títulos instalados y del proyecto: copia editable con animación y texto visible | F | Evidencia anterior parcial; nueva muestra selectiva pendiente |
| Horizonte/vertical: rótulos con sentido, tramos sin texto y sin desbordamiento | F/Biglex | Pendiente |
| Aplicar, reaplicar y deshacer la revisión 1.1.0 en Resolve | F | Pendiente |

## Cierre

El brief y los planes son el entregable actual. No se declara el rediseño completado ni el flujo audiovisual validado. Al ejecutar, añadir evidencia concreta, fecha, tamaño de ventana, modelo y secuencia de prueba sin registrar secretos.
