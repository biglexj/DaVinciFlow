# Preparar las dependencias de los adaptadores de Resolve y Aurora.
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot

# uv puede no estar en el PATH de la sesion: se localiza en la instalacion
# habitual del usuario antes de fallar.
$uvCommand = Get-Command 'uv' -ErrorAction SilentlyContinue
$uv = if ($uvCommand) { $uvCommand.Source } else { Join-Path $env:USERPROFILE '.local\bin\uv.exe' }
if (-not (Test-Path -LiteralPath $uv)) {
    throw "No se encontro 'uv' (necesario para preparar el entorno). Buscalo en el PATH o en $env:USERPROFILE\.local\bin\uv.exe"
}

$env:UV_PROJECT_ENVIRONMENT = Join-Path $taskRoot '.venv'
& $uv sync --project (Join-Path $taskRoot 'compat/python') --locked --inexact --python 3.13
if ($LASTEXITCODE -ne 0) { throw 'No se pudo sincronizar el entorno con uv.' }

Write-Host 'Entorno de compatibilidad preparado.'
