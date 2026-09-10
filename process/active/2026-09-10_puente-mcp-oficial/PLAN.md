# Puente oficial de Resolve 21.1

## Objetivo y autorización

Biglex solicita conectar DaVinci Flow al nuevo puente oficial de Resolve y aprovecharlo en el flujo existente. Esta solicitud autoriza la implementación y las pruebas reversibles; no autoriza generar una propuesta editorial ni aplicarla a su montaje sin revisión.

## Alcance

- Cliente MCP local por stdin/stdout para el ejecutable de Blackmagic; sin servidor de red ni dependencias adicionales.
- Captura, catálogo, aplicación revisada y reversión usan el puente oficial cuando está instalado. La conexión CPython anterior queda seleccionable para compatibilidad; ningún fallo de MCP reintenta por otro transporte.
- Reutilizar las operaciones editoriales y sus validaciones dentro del Python integrado de Resolve. El acceso al sistema se limita al script fijo que importa el paquete local y lee/escribe propuestas, plantillas y registros.
- Adaptar la captura a transiciones devueltas por Resolve 21.1, conservándolas en la huella del montaje.
- Comprobar protocolo, fallos, protección de revisión y captura real desde el controlador de DaVinci Flow. Probar escritura/reversión únicamente en una secuencia temporal aislada.

## Límites

El MCP impone un tiempo máximo por script. Una escritura sin respuesta confirmada se informa como incierta y nunca se repite automáticamente. No cambia el proveedor LLM ni el montaje editorial preparado. No se publica una versión en este trabajo.
