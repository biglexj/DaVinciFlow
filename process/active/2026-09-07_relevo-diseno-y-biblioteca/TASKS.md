# Tareas y responsables

## Preparación de este relevo

- [x] Confirmar el proyecto, los commits locales de la versión previa y la copia limpia al retomar.
- [x] Repetir las pruebas de la base: 164 correctas.
- [x] Documentar el recorte de controles, las llamadas 503 y la falta de validación selectiva real.
- [x] Localizar e inventariar la carpeta real con tilde; definir separación lógica de recursos.
- [x] Entregar brief de diseño y límites de archivos para otro responsable.

## D — Diseñador por asignar

- [x] D01 — Leer DESIGN_BRIEF y reproducir controles ocultos en ventana pequeña (resuelto fijando panel de revisión al fondo de la ventana).
- [x] D02 — Recuperar la estructura anterior de navegación vertical izquierda y panel principal derecho, según la captura elegida; conservar las funciones nuevas y quitar accesos duplicados.
- [x] D03 — Integrar componentes compartidos y distribución adaptable; preservar una sola ventana con Notebook sin pestañas visibles en cabecera.
- [x] D04 — Validar teclado, escalado, legibilidad, icono nativo oficial y revisión/aplicación siempre alcanzables (164 pruebas en verde).
- [x] D05 — Entregar evidencia visual a Biglex y resolver feedback directo: eliminar saturación de botones (toolbar compacta de 2 filas tipo DAW), unificar fuentes en dropbox `Origen: [DaVinci Resolve / Archivo SRT]`, remover campo redundante `Modelo exacto` del editor, desplegar columnas cronológicas multicapa en la tabla (`Contexto`, `Principal`, `Énfasis`, `Plantilla`), y solucionar comboboxes vacíos en el inspector mediante asignación inteligente por rol.
- [x] D06 — Carga y renderizado inmediato de subtítulos en la tabla al capturar o cargar SRT: poblar filas con fotogramas, texto principal capturado y plantilla por defecto antes de invocar la LLM; habilitar selección e inspección inmediata en el formulario inferior (165 pruebas en verde).
- [x] D07 — Experiencia pro y prevención de pérdida de foco: detección y carga automática al iniciar si Resolve tiene línea de tiempo activa con subtítulos; renombrar botón a `✨ Generar Subtítulos IA` con terminología profesional; incorporar toggle `📌 Fijar al frente` (Always On Top) y restauración de foco tras aplicar para evitar que la ventana se oculte detrás de Resolve (166 pruebas en verde).
- [x] D08 — Alineación milimétrica con sidebar-elegido.png y feedback de audio de Biglex:
  1. **Eliminación de desbordamientos / cortes en toolbar**: comboboxes compactados (`source_combo` 16, `mode` 14, `density` 11); `📂 Abrir` y `💾 Guardar` integrados limpiamente en Fila 1; botón redundante `🗂️ Plantillas` retirado de Fila 1 en Workbench (ya reside en el sidebar). Cero cortes en Fila 1.
  2. **Wrap de títulos en sidebar**: `self.project_label` y `self.timeline_label` con `wraplength=180, justify="left"` para evitar truncamientos bruscos.
  3. **Énfasis visual y Análisis Local**: incorporación de `🔍 Análisis local` en Fila 2 que ejecuta `classify_text_layers` determinista; etiquetas cromáticas configuradas en Treeview (`layer3` -> `#00e5cc` turquesa Ely vibrante, `layer2` -> `#5eead4`, `layer1` -> `#e2e4e8`, `excluded` -> `#8e929a`); desglosa subtítulos en capas y énfasis de inmediato sin depender de LLM ni sufrir por errores 503.
  4. **Inspector compacto**: reducción del padding de la tarjeta de revisión inferior (`(10, 4, 10, 6)`) y espaciados verticales (`pady=1`), bajando el inspector y otorgando 45-55px adicionales de altura a la tabla de subtítulos (167 pruebas en verde).

## A — Integración de biblioteca

- [x] A01 — Configurar la raíz real `D:\Vídeos\Assets` (con tilde) y las carpetas independientes de SFX/música (`Audio Efects` y `Audio Music`); conservar las demás rutas que ya haya elegido el usuario.
- [ ] A02 — Resolver rutas solapadas, duplicados por categoría y selección persistente ante errores o unidades desconectadas.
- [ ] A03 — Conectar la carpeta de títulos con el catálogo y mostrar las fuentes con claridad.
- [ ] A04 — Verificar el contexto de recursos enviado a la LLM; mostrar nombre, categoría, selección y límites de lectura de documentos.
- [ ] A05 — Entregar datos y estados al diseñador sin cambios simultáneos en el mismo panel.

## F — Cierre del flujo selectivo

- [ ] F01 — Obtener una respuesta real del modelo exacto seleccionado. Un 503 no valida el modelo ni justifica cambiarlo silenciosamente.
- [ ] F02 — Evaluar si una decisión por subtítulo fragmenta ideas: hoy no se agrupan frases entre cues. Diseñar agrupación temporal y de significado si la muestra lo requiere, con huella y revisión auditables.
- [ ] F03 — Probar rótulos selectivos de una, dos y tres capas, y tramos sin texto, en horizontal y vertical. Revisar negaciones y sentido; la validación léxica actual no prueba equivalencia semántica.
- [ ] F04 — Corregir conservación de ediciones al recapturar, cargar o generar de nuevo; sincronizar el estado del catálogo al abrir una propuesta guardada.
- [ ] F05 — Recuperar configuración avanzada de nodo/control en el panel Plantillas para títulos ambiguos; no volver al editor en otra ventana.
- [ ] F06 — Aplicar en una copia de Resolve; comprobar texto, tiempos, animación, ausencia de duplicados, errores parciales y deshacer sin tocar originales.
- [ ] F07 — Actualizar validación y entregar la muestra a Biglex. Después continuar fase 2 y, tras su cierre, fase 3.

## Estado de ejecución

Se ha completado la reestructuración completa de la interfaz según la captura de referencia (`sidebar-elegido.png`) y el feedback continuo del usuario: barra de herramientas DAW en 2 filas limpias, dropdown unificado de origen, renombre profesional a `✨ Generar Subtítulos IA`, auto-carga de subtítulos de Resolve al iniciar, toggle `📌 Fijar al frente` (Always On Top) en la barra superior para evitar que Resolve oculte la ventana al aplicar, columnas multicapa en la tabla y tarjeta de inspección sincronizada. 166/166 pruebas unitarias en verde.
