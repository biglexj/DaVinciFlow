# Iniciar DaVinci Flow Desktop (Flet) con el entorno unificado
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $taskRoot '.venv/Scripts/python.exe'
$script = Join-Path $taskRoot 'src-flet/main.py'

$env:PYTHONPATH = "$taskRoot/src;$taskRoot/src-flet"
& $python $script
exit $LASTEXITCODE
