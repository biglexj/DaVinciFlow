# ==============================================================================
# build-release.ps1 — Pipeline Oficial de Release para DaVinci Flow
# Ecosistema biglexj — Documentación Core
# ==============================================================================

param(
    [string]$Version,
    [string]$ReleaseNotesFile = "RELEASE_MESSAGE.md",
    [switch]$LocalOnly,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
. (Join-Path $PSScriptRoot "ReleaseTools.ps1")

$repository = "biglexj/DaVinciFlow"
$appName = "DaVinci Flow"
$pyprojectPath = Join-Path $root "pyproject.toml"
$initPath = Join-Path $root "src\davinci_flow\__init__.py"
$releaseNotesPath = Join-Path $root $ReleaseNotesFile

if (-not (Test-Path -LiteralPath $pyprojectPath)) {
    throw "No se encontró el archivo de configuración: $pyprojectPath"
}
if (-not (Test-Path -LiteralPath $initPath)) {
    throw "No se encontró el archivo del módulo: $initPath"
}

# 1. Leer versión actual de pyproject.toml
$pyprojectContent = Get-Content -LiteralPath $pyprojectPath -Raw -Encoding UTF8
$versionMatch = [regex]::Match($pyprojectContent, '(?m)^version\s*=\s*"(\d+\.\d+\.\d+)"')
if (-not $versionMatch.Success) {
    throw "No se pudo leer la versión en $pyprojectPath."
}
$currentVersion = $versionMatch.Groups[1].Value

if (-not $Version) {
    $Version = $currentVersion
}

Assert-SemanticVersion $Version

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "🚀 Iniciando pipeline de release para $appName v$Version" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan

# 2. Preflight de publicación remota
$tag = "v$Version"
if (-not $LocalOnly) {
    Write-Host "🔍 Ejecutando preflight de Git y GitHub CLI..." -ForegroundColor Yellow
    Assert-PublishPreflight -Root $root -Repository $repository -Tag $tag
    if (-not (Test-Path -LiteralPath $releaseNotesPath)) {
        throw "No se encontró el archivo de notas de lanzamiento en '$releaseNotesPath'."
    }
}

# 3. Ejecución de pruebas automatizadas
$pythonExe = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonExe)) {
    $pythonExe = "python"
}

if (-not $SkipTests) {
    Write-Host "🧪 Ejecutando suite de pruebas unitarias..." -ForegroundColor Yellow
    Invoke-Checked $pythonExe @("-m", "unittest", "discover", "-s", "tests")
    Write-Host "✅ Pruebas superadas con éxito." -ForegroundColor Green
}

# 4. Actualizar versión en archivos fuente si es necesario
if ($Version -ne $currentVersion) {
    Write-Host "📝 Actualizando versión a $Version en pyproject.toml y __init__.py..." -ForegroundColor Yellow
    $updatedPyproject = [regex]::Replace($pyprojectContent, '(?m)^version\s*=\s*"(\d+\.\d+\.\d+)"', "version = `"$Version`"")
    Set-Content -LiteralPath $pyprojectPath -Value $updatedPyproject -Encoding UTF8

    $initContent = Get-Content -LiteralPath $initPath -Raw -Encoding UTF8
    $updatedInit = [regex]::Replace($initContent, '(?m)^__version__\s*=\s*"(\d+\.\d+\.\d+)"', "__version__ = `"$Version`"")
    Set-Content -LiteralPath $initPath -Value $updatedInit -Encoding UTF8
}

# 5. Generar empaquetado y artefactos en dist/
$distDir = Join-Path $root "dist"
if (Test-Path -LiteralPath $distDir) {
    Remove-Item -LiteralPath $distDir -Recurse -Force
}
New-Item -ItemType Directory -Path $distDir -Force | Out-Null

Write-Host "📦 Generando artefactos de distribución..." -ForegroundColor Yellow
$uvExe = Get-Command "uv" -ErrorAction SilentlyContinue
if ($uvExe) {
    Invoke-Checked uv @("build", "--out-dir", $distDir, $root)
} else {
    Invoke-Checked $pythonExe @("-m", "build", "--outdir", $distDir, $root)
}

# 6. Generar checksums SHA256SUMS.txt
$artifacts = Get-ChildItem -LiteralPath $distDir -File | Where-Object { $_.Name -ne "SHA256SUMS.txt" }
if ($artifacts.Count -gt 0) {
    Write-Host "🔒 Generando SHA256SUMS.txt..." -ForegroundColor Yellow
    $checksums = foreach ($file in $artifacts) {
        $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        "$hash  $($file.Name)"
    }
    $checksumsPath = Join-Path $distDir "SHA256SUMS.txt"
    Set-Content -LiteralPath $checksumsPath -Value $checksums -Encoding UTF8
}

# 7. Commit, Tag y Publicación en GitHub Releases
if (-not $LocalOnly) {
    Push-Location $root
    try {
        Write-Host "📤 Realizando commit y push de versión..." -ForegroundColor Yellow
        git add pyproject.toml src/davinci_flow/__init__.py
        git commit -m "release: $appName $tag"
        git tag -a $tag -m "$appName $tag"
        git push origin main --tags

        Write-Host "🌐 Publicando release en GitHub..." -ForegroundColor Yellow
        $distFiles = Get-ChildItem -LiteralPath $distDir -File | ForEach-Object { $_.FullName }
        $ghArgs = @("release", "create", $tag) + $distFiles + @("--title", "$appName $tag", "--notes-file", $releaseNotesPath)
        Invoke-Checked gh $ghArgs

        Write-Host "🎉 ¡Release $tag publicado exitosamente en GitHub!" -ForegroundColor Green
    } finally {
        Pop-Location
    }
} else {
    Write-Host "ℹ️ Modo local completado. Artefactos listos en 'dist/' sin publicar en GitHub." -ForegroundColor Cyan
}
