# Preparar el entorno unificado CPython 3.13 con uv
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot

uv sync --project $taskRoot
if ($LASTEXITCODE -ne 0) { throw 'No se pudo sincronizar el entorno con uv.' }

& (Join-Path $taskRoot '.venv/Scripts/python.exe') -m davinci_flow --install
if ($LASTEXITCODE -ne 0) { throw 'No se pudo actualizar el acceso de Resolve.' }

Write-Host '✅ Entorno unificado y lanzador de DaVinci Resolve preparados correctamente.'
