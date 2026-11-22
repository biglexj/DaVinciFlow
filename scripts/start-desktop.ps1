# Iniciar DaVinci Flow Desktop (Rust + GPUI por defecto; usa -Flet para la versión Python)
param(
    [switch]$Flet
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot

if ($Flet) {
    $python = Join-Path $taskRoot '.venv/Scripts/python.exe'
    $script = Join-Path $taskRoot 'src-flet/main.py'
    $env:PYTHONPATH = "$taskRoot/src;$taskRoot/src-flet"
    & $python $script
    exit $LASTEXITCODE
}

$gpuiDebug = Join-Path $taskRoot 'src-gpui/target/debug/davinci-flow-gpui.exe'
$gpuiRelease = Join-Path $taskRoot 'src-gpui/target/release/davinci-flow-gpui.exe'
$env:PATH = "$env:USERPROFILE\.rustup\toolchains\stable-x86_64-pc-windows-gnullvm\bin;$env:USERPROFILE\.cargo\bin;$env:PATH"

if (Test-Path -LiteralPath $gpuiRelease) {
    & $gpuiRelease @args
    exit $LASTEXITCODE
}
if (Test-Path -LiteralPath $gpuiDebug) {
    & $gpuiDebug @args
    exit $LASTEXITCODE
}

cargo run --manifest-path (Join-Path $taskRoot 'src-gpui/Cargo.toml') --locked -- @args
exit $LASTEXITCODE
