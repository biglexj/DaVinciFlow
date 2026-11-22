# Migración del diseño · estado al 2026-11-17

- [x] Asignación vigente: agente principal, según petición de Biglex de continuar también el diseño.
- [x] Mantener el sidebar y las once entradas actuales.
- [x] Reducir espaciado, tarjetas vacías y expansión innecesaria; formularios con ancho acotado.
- [x] Editor: fuente, opciones, propuesta directa/IA, mesa de revisión por bloque, buscador de plantillas y JSON.
- [x] Corrección y Biblioteca: integrar el motor nativo y las acciones existentes.
- [x] Asistente, catálogos, Ajustes y Acerca de: consolidar las vistas ya presentes y sus servicios reales.
- [x] Voz: selección, texto, consumo confirmado, generación/recuperación e importación; cuenta en Ajustes.
- [x] Luna Fetch: URL, formato, destino, descarga e importación explícita.
- [x] B-Rolls/Música/SFX: listas compactas y apertura en el reproductor del sistema; vista previa de imagen/fotograma en B-Rolls.
- [x] Comprobar apertura de un SRT de 20 bloques y propuesta directa en GPUI.
- [ ] Verificar guardado/reapertura de JSON desde el diálogo nativo completo.
- [ ] Verificar aplicación/deshacer reales en una secuencia de prueba y voz remota de Aurora.
- [x] Panel semántico/guion/marcadores de Corrección: alineación con el guion, glosario
      y marcadores en la línea de tiempo, con aplicación transaccional en el motor.
- [x] Presets, packs rápidos, lectura de proyecto y vista previa de títulos; tandas reanudables y modo Decisiones en el Editor.
- [x] Separación motor/voz en Voz, cuenta Aurora con Google/Discord y autodetección de retorno, e historial y metadatos en Luna Fetch.
- [ ] Validar alineación/guion y posición/inserción de marcadores reales en Resolve.
- [ ] Aceptación visual de Biglex, empaquetado y actualización del ejecutable nativo.

La matriz en src-gpui/README.md distingue interfaz nativa, servicios que aún pasan por Python y capacidades pendientes. No se confunden presencia de una vista, pruebas del contrato y funcionamiento real dentro de Resolve.
