# ==============================================================================
# ReleaseTools.ps1 — DaVinci Flow
# Ecosistema biglexj — Documentación Core
# ==============================================================================

Set-StrictMode -Version Latest

<#
.SYNOPSIS
Ejecuta un ejecutable externo y verifica que finalice con código de retorno 0.
#>
function Invoke-Checked {
    param(
        [Parameter(Mandatory)] [string]$Executable,
        [Parameter(Mandatory)] [AllowEmptyString()] [string[]]$ArgumentList
    )

    & $Executable @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw "El comando '$Executable' terminó con código de error $LASTEXITCODE."
    }
}

<#
.SYNOPSIS
Valida que una cadena cumpla la especificación de versión semántica (X.Y.Z)
y la Regla del .9 del ecosistema (el parche no debe ser mayor a 9).
#>
function Assert-SemanticVersion {
    param([Parameter(Mandatory)] [string]$Version)

    if ($Version -notmatch '^(\d+)\.(\d+)\.(\d+)$') {
        throw "La versión '$Version' no cumple el formato semántico estricto mayor.menor.parche (ej. 1.2.3)."
    }
    if ([int]$Matches[3] -gt 9) {
        throw "Regla del .9: El parche '$Version' excede 9. Avanza la versión menor (ej. de 1.0.9 pasa a 1.1.0)."
    }
}

<#
.SYNOPSIS
Verifica los requisitos previos de Git y GitHub CLI antes de publicar un release remoto.
#>
function Assert-PublishPreflight {
    param(
        [Parameter(Mandatory)] [string]$Root,
        [Parameter(Mandatory)] [string]$Repository,
        [Parameter(Mandatory)] [string]$Tag
    )

    Push-Location $Root
    try {
        # 1. Verificar rama activa main
        $branch = (& git branch --show-current).Trim()
        if ($LASTEXITCODE -ne 0 -or $branch -ne "main") {
            throw "La publicación oficial exige estar en la rama 'main' (rama actual: '$branch')."
        }

        # 2. Verificar que el remoto origin coincida con el repositorio esperado
        $origin = (& git remote get-url origin).Trim()
        if ($LASTEXITCODE -ne 0 -or $origin -notmatch "github\.com[/:]$([regex]::Escape($Repository))(\.git)?$") {
            throw "El remoto origin ('$origin') no corresponde al repositorio esperado '${Repository}'."
        }

        # 3. Sincronización con origin/main
        Invoke-Checked git @("fetch", "origin", "main", "--tags")
        if ((& git rev-parse HEAD).Trim() -ne (& git rev-parse origin/main).Trim()) {
            throw "La rama 'main' local no está sincronizada con 'origin/main'. Realiza git pull/push antes de publicar."
        }

        # 4. Autenticación en GitHub CLI
        Invoke-Checked gh @("auth", "status")

        # 5. Comprobar existencia de Tag o Release remoto previo (evitar sobrescrituras)
        $oldPreference = $ErrorActionPreference
        $ErrorActionPreference = "SilentlyContinue"

        & git rev-parse --quiet --verify "refs/tags/$Tag" *> $null
        $tagExists = ($LASTEXITCODE -eq 0)

        & gh release view $Tag --repo $Repository *> $null
        $releaseExists = ($LASTEXITCODE -eq 0)

        $ErrorActionPreference = $oldPreference

        if ($tagExists) {
            throw "El tag '$Tag' ya existe local o remotamente. No se permite re-etiquetar versiones ya creadas."
        }
        if ($releaseExists) {
            throw "El GitHub Release '$Tag' ya existe en '${Repository}'. Incrementa la versión antes de publicar."
        }
    } finally {
        Pop-Location
    }
}
