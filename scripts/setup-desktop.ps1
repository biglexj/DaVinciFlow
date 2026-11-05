# Preparar el entorno unificado CPython 3.13 con uv
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot

# uv puede no estar en el PATH de la sesion: se localiza en la instalacion
# habitual del usuario antes de fallar.
$uvCommand = Get-Command 'uv' -ErrorAction SilentlyContinue
$uv = if ($uvCommand) { $uvCommand.Source } else { Join-Path $env:USERPROFILE '.local\bin\uv.exe' }
if (-not (Test-Path -LiteralPath $uv)) {
    throw "No se encontro 'uv' (necesario para preparar el entorno). Buscalo en el PATH o en $env:USERPROFILE\.local\bin\uv.exe"
}

& $uv sync --project $taskRoot
if ($LASTEXITCODE -ne 0) { throw 'No se pudo sincronizar el entorno con uv.' }

& (Join-Path $taskRoot '.venv/Scripts/python.exe') -m davinci_flow --install
if ($LASTEXITCODE -ne 0) { throw 'No se pudo actualizar el acceso de Resolve.' }

Write-Host '✅ Entorno unificado y lanzador de DaVinci Resolve preparados correctamente.'
