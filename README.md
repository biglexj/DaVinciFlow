# DaVinci Flow

DaVinci Flow es una automatización en Python para transformar los subtítulos creados por DaVinci Resolve en una base estructurada para títulos dinámicos, énfasis visual y efectos sonoros.

## Estado actual

La versión `0.1.0` contiene únicamente una base técnica no destructiva:

- conexión local con DaVinci Resolve 21;
- detección del proyecto y la línea de tiempo activos;
- lectura de una pista de subtítulos;
- conversión de cada subtítulo a un modelo independiente de la API de Resolve;
- pruebas unitarias sin necesidad de abrir DaVinci.

DaVinci Flow todavía no crea títulos, no inserta efectos y no utiliza servicios de IA.

## Arquitectura modular

```text
src/davinci_flow/
├── __main__.py              Entrada de diagnóstico
├── application.py           Coordinación del caso de uso
├── errors.py                Errores controlados
├── resolve/                 Adaptación de la API de DaVinci Resolve
└── subtitles/               Modelo independiente de subtítulos
```

El futuro archivo que se instale en el menú de Resolve será un iniciador pequeño. La lógica continuará dentro de estos módulos y no crecerá como un archivo monolítico.

## Requisitos de desarrollo

- Windows 11;
- DaVinci Resolve 21;
- Python 3.11 de 64 bits;
- acceso externo al scripting habilitado en Resolve cuando se ejecute desde la terminal.

No existen dependencias externas de Python en esta etapa.

## Probar el lector

Con DaVinci Resolve abierto, un proyecto activo y una pista de subtítulos disponible:

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m davinci_flow --track 1
```

El comando solo imprime los subtítulos encontrados. No modifica la línea de tiempo.

## Ejecutar las pruebas

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m unittest discover -s tests -v
```

## Límites de esta validación

Las pruebas automatizadas validan la lógica con objetos simulados. La conexión, los permisos y la respuesta real de Resolve deben verificarse por separado con la aplicación abierta.
