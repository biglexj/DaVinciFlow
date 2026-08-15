# Plan — Base inicial de DaVinci Flow

## Objetivo

Crear una base Python pequeña, comprobable y no destructiva para conectarse con DaVinci Resolve 21 y leer los subtítulos existentes de la línea de tiempo activa.

## Alcance aprobado

- Inicializar el repositorio y la documentación compartida compatible.
- Aislar la API de Resolve en un adaptador.
- Modelar subtítulos sin depender de objetos nativos de Resolve.
- Proporcionar una entrada de diagnóstico de solo lectura.
- Validar la lógica mediante pruebas con objetos simulados.

## Fuera de alcance

- Generación de títulos Fusion.
- Inserción de efectos visuales o sonoros.
- Interfaz gráfica e instalación dentro del menú de Resolve.
- Integración con modelos de lenguaje.

## Riesgos y mitigaciones

- La API puede no responder si Resolve está cerrado o el scripting externo está deshabilitado: presentar un error controlado.
- Las pruebas simuladas no demuestran compatibilidad real: registrar la prueba dentro de Resolve como validación pendiente.
- Las pistas se numeran desde 1: validar el índice antes de consultar Resolve.

## Puertas de aprobación

1. Base y pruebas automatizadas correctas.
2. Lectura comprobada en una línea de tiempo real.
3. Aprobación humana antes de comenzar la generación multicapa.
