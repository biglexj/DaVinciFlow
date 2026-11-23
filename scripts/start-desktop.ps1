# Iniciar DaVinci Flow Desktop
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot

$gpuiDebug = Join-Path $taskRoot 'target/debug/davinci-flow-gpui.exe'
$gpuiRelease = Join-Path $taskRoot 'target/release/davinci-flow-gpui.exe'
$env:PATH = "$env:USERPROFILE\.rustup\toolchains\stable-x86_64-pc-windows-gnullvm\bin;$env:USERPROFILE\.cargo\bin;$env:PATH"

if (Test-Path -LiteralPath $gpuiRelease) {
    & $gpuiRelease @args
    exit $LASTEXITCODE
}
if (Test-Path -LiteralPath $gpuiDebug) {
    & $gpuiDebug @args
    exit $LASTEXITCODE
}

cargo run --manifest-path (Join-Path $taskRoot 'Cargo.toml') --locked -- @args
exit $LASTEXITCODE
