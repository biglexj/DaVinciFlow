#!/usr/bin/env bun
import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { relative, resolve, join } from "node:path";

const root = resolve(import.meta.dir, "..");

function readTomlVersion(path: string): string {
    const content = readFileSync(path, "utf-8");
    const m = content.match(/^version\s*=\s*"([^"]+)"/m);
    if (!m) throw new Error("No se pudo leer la versión en " + path);
    return m[1];
}

function sha256(filePath: string): string {
    const buffer = readFileSync(filePath);
    return createHash("sha256").update(buffer).digest("hex");
}

function runCmdSync(cmd: string[], cwd = root): { stdout: string; stderr: string; code: number } {
    const res = Bun.spawnSync(cmd, { cwd, stdout: "pipe", stderr: "pipe" });
    return {
        stdout: res.stdout.toString().trim(),
        stderr: res.stderr.toString().trim(),
        code: res.exitCode ?? 0,
    };
}

// El stack del proyecto es uv con un único .venv (pyproject.toml + uv.lock).
// Se usa ese entorno cuando existe; si no, se delega en `uv run`, que lo
// prepara; como último recurso, el `python` del sistema.
function findUv(): string | null {
    const fromPath = Bun.which("uv");
    if (fromPath) return fromPath;
    const home = process.env.USERPROFILE;
    if (home) {
        const candidate = join(home, ".local", "bin", "uv.exe");
        if (existsSync(candidate)) return candidate;
    }
    return null;
}

function resolvePythonCmd(): string[] {
    const venvPython = join(root, ".venv", "Scripts", "python.exe");
    if (existsSync(venvPython)) return [venvPython];
    const uv = findUv();
    if (uv) return [uv, "run", "python"];
    return ["python"];
}

const pythonCmd = resolvePythonCmd();

// Los scripts de release y de empaquetado se invocan con Windows PowerShell
// 5.1 (`-NoProfile`), el motor que usa el pipeline del proyecto. Los scripts
// evitan los cmdlets que solo existen en PowerShell 7 o que desaparecen con
// `-NoProfile` (véase Docs/troubleshooting/tools/powershell-host-portability.md).
function powershellCmd(script: string, args: string[] = []): string[] {
    return [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", join(root, script), ...args,
    ];
}

const installerScript = join(root, "scripts", "packaging", "Build-Installer.ps1");
const releaseScript = join(root, "scripts", "release", "build-release.ps1");
const setupScript = join(root, "scripts", "setup-desktop.ps1");

const appVersion = readTomlVersion(join(root, "pyproject.toml"));
const appName = "DaVinci Flow";
const repository = "biglexj/DaVinciFlow";
const installerName = `DaVinciFlow-Setup-${appVersion}.exe`;

// Verificación de contratos del proyecto: los scripts de implementación no
// deben llevar rutas absolutas al disco local (estándar global de scripts).
function listarArchivos(dir: string): string[] {
    if (!existsSync(dir)) return [];
    const salida: string[] = [];
    for (const entrada of readdirSync(dir, { withFileTypes: true })) {
        const completo = join(dir, entrada.name);
        if (entrada.isDirectory()) salida.push(...listarArchivos(completo));
        else salida.push(completo);
    }
    return salida;
}

function rutasAbsolutasEnScripts(): string[] {
    const hallazgos: string[] = [];
    for (const archivo of listarArchivos(join(root, "scripts"))) {
        if (!/\.(ts|ps1|cmd|bat|py)$/i.test(archivo)) continue;
        const lineas = readFileSync(archivo, "utf-8").split(/\r?\n/);
        lineas.forEach((linea, indice) => {
            // Unidad de disco local (letra de unidad, dos puntos y barra o
            // barra invertida) sin falsos positivos con los "://" de una URL.
            if (/(?<![A-Za-z0-9_])[A-Za-z]:[\\/]/.test(linea)) {
                hallazgos.push(`${relative(root, archivo)}:${indice + 1}: ${linea.trim()}`);
            }
        });
    }
    return hallazgos;
}

// La importación no debe abrir la app ni hablar con Resolve: solo comprueba
// que motor e interfaz cargan sin efectos secundarios.
const IMPORT_SMOKE = [
    "import sys",
    "sys.path[:0] = ['src', 'src-flet']",
    "import davinci_flow",
    "import davinci_flow.mcp_server",
    "import app.app",
    "import features.editor.editor_view",
    "import features.catalog.catalog_view",
    "import features.settings.settings_view",
    "import shared.components",
    "print('importacion correcta')",
].join("; ");

const help = `DaVinci Flow: mise <setup|dev|build|check|test|release|publish> [opciones]
  setup    Preparar .venv con uv e instalar el lanzador en DaVinci Resolve.
  dev      Ejecutar en modo desarrollo (Flet Desktop).
  build    Verificar sintaxis y generar los paquetes Python en dist/.
  check    Verificar sintaxis, importacion y contratos, sin generar artefactos.
  test     Ejecutar las pruebas unitarias.
  release  Generar instalador Windows en release/ y paquetes Python en dist/.
  publish  [github] Publicar la release en GitHub Releases.
  --plan   Mostrar los comandos o el plan sin ejecutar acciones ni escribir.
  --check  Para publish: verificar requisitos locales y remotos sin escribir.
  --yes    Para publish: autoriza explicitamente la publicacion.

Ejemplos:
  mise setup
  mise dev --plan
  mise build --plan
  mise check --plan
  mise test --plan
  mise release --plan
  mise publish --plan
  mise publish --check
  mise publish --yes
`;

function assertOpciones(action: string, args: string[], permitidas: string[]): void {
    for (const arg of args) {
        if (arg.startsWith("-") && !permitidas.includes(arg)) {
            throw new Error(`Opción desconocida para '${action}': ${arg}. Opciones admitidas: ${permitidas.join(", ")}.`);
        }
    }
}

async function runPasos(pasos: { titulo: string; cmd: string[]; env?: Record<string, string> }[], isPlan: boolean): Promise<number> {
    for (const paso of pasos) {
        console.log(`\n==> ${paso.titulo}`);
        console.log(`    ${paso.cmd.join(" ")}`);
        if (isPlan) continue;
        const child = Bun.spawn(paso.cmd, {
            cwd: root,
            env: paso.env ? { ...process.env, ...paso.env } : process.env,
            stdin: "inherit",
            stdout: "inherit",
            stderr: "inherit",
        });
        const code = (await child.exited) ?? 0;
        if (code !== 0) {
            console.error(`\n❌ Falló: ${paso.titulo} (código ${code})`);
            return code;
        }
    }
    return 0;
}

async function handlePublish(args: string[]): Promise<number> {
    const isPlan = args.includes("--plan");
    const isCheck = args.includes("--check");
    const isYes = args.includes("--yes");
    const positional = args.filter((arg) => !arg.startsWith("-"));
    const channel = positional[0] ?? "github";

    if (channel === "all") {
        throw new Error(
            "El canal 'all' no está disponible: la sincronización de la ficha en Aurora no está automatizada en este proyecto. " +
            "Publica con 'mise publish github --yes' y sincroniza la ficha por el canal administrativo descrito en " +
            "Docs/global/releases/web-release-message-standard.md.",
        );
    }
    if (channel !== "github") {
        throw new Error(`Canal desconocido: ${channel}. El único canal disponible es 'github'.`);
    }

    console.log(`\n=== Publicación: ${appName} v${appVersion} ===`);
    console.log(`Repositorio : ${repository}`);
    console.log(`Canal       : GitHub Releases`);
    console.log(`Artefacto   : release/${installerName}`);

    if (isPlan) {
        console.log("\n[Plan de publicación]");
        console.log("1. Verificar que el repositorio está en la rama main, con el árbol limpio y sincronizado con origin/main.");
        console.log(`2. Comprobar el instalador local en release/: ${installerName} y su SHA-256 en release/SHA256SUMS.txt.`);
        console.log("3. Validar RELEASE_MESSAGE.md (notas de versión públicas sin secretos).");
        console.log("4. Ejecutar la suite de pruebas y generar los paquetes Python en dist/.");
        console.log(`5. Crear el tag git v${appVersion} y la GitHub Release vía gh, con el instalador .exe y SHA256SUMS.txt como assets.`);
        console.log("\n(--plan completado: no se realizaron cambios ni consultas de red)");
        return 0;
    }

    if (isCheck) {
        console.log("\n[Comprobación de preparación (--check)]");
        let hasErrors = false;

        // 1. Rama y estado del árbol
        const branch = runCmdSync(["git", "branch", "--show-current"]);
        if (branch.stdout !== "main") {
            console.warn(`⚠️  La rama activa es '${branch.stdout || "(ninguna)"}'; la publicación exige 'main'.`);
            hasErrors = true;
        } else {
            console.log("✅ Rama activa: main.");
        }
        const gitStatus = runCmdSync(["git", "status", "--porcelain"]);
        if (gitStatus.stdout) {
            console.warn("⚠️  Aviso: el repositorio tiene cambios locales sin confirmar.");
        } else {
            console.log("✅ Árbol Git limpio.");
        }

        // 2. Remoto y gh
        const origin = runCmdSync(["git", "remote", "get-url", "origin"]);
        console.log(`ℹ️  Remoto origin: ${origin.stdout || "(sin remoto)"}`);
        const auth = runCmdSync(["gh", "auth", "status"]);
        if (auth.code !== 0) {
            console.warn("⚠️  GitHub CLI no responde o no está autenticado.");
            hasErrors = true;
        } else {
            console.log("✅ GitHub CLI autenticado.");
        }

        // 3. Tag local
        const tagCheck = runCmdSync(["git", "tag", "-l", `v${appVersion}`]);
        if (tagCheck.stdout.includes(`v${appVersion}`)) {
            console.warn(`⚠️  El tag v${appVersion} ya existe localmente.`);
            hasErrors = true;
        } else {
            console.log(`✅ Tag v${appVersion} libre localmente.`);
        }

        // 4. Artefactos en release/
        const releaseDir = join(root, "release");
        const installerPath = join(releaseDir, installerName);
        if (existsSync(installerPath)) {
            const st = statSync(installerPath);
            const hash = sha256(installerPath);
            console.log(`✅ Instalador presente: ${installerName} (${(st.size / 1024 / 1024).toFixed(2)} MB)`);
            console.log(`   SHA-256: ${hash}`);
            const sumsPath = join(releaseDir, "SHA256SUMS.txt");
            if (!existsSync(sumsPath)) {
                console.warn("⚠️  Falta release/SHA256SUMS.txt con el checksum del instalador.");
                hasErrors = true;
            } else {
                console.log("✅ release/SHA256SUMS.txt presente.");
            }
        } else {
            console.warn(`❌ Instalador no encontrado en release/${installerName}. Ejecuta 'mise release' antes de publicar.`);
            hasErrors = true;
        }

        // 5. Notas de versión
        const notesPath = join(root, "RELEASE_MESSAGE.md");
        if (existsSync(notesPath)) {
            console.log("✅ RELEASE_MESSAGE.md presente.");
        } else {
            console.warn("⚠️  RELEASE_MESSAGE.md no encontrado en la raíz.");
            hasErrors = true;
        }

        console.log("\n(--check completado: modo de solo lectura, sin escrituras ni publicación)");
        return hasErrors ? 1 : 0;
    }

    if (!isYes) {
        console.error("\n❌ Publicación no ejecutada: falta la autorización explícita.");
        console.error("   Usa 'mise publish --plan' para revisar los pasos o 'mise publish --yes' para publicar en GitHub Releases.");
        return 1;
    }

    const pasos = [
        { titulo: "Publicación de la release (scripts/release/build-release.ps1)", cmd: powershellCmd("scripts/release/build-release.ps1") },
    ];
    return runPasos(pasos, false);
}

export async function main(args = Bun.argv.slice(2)): Promise<number> {
    const [action, ...rest] = args;
    if (!action || action === "--help" || rest.includes("--help")) {
        console.log(help);
        return 0;
    }

    if (action === "publish") {
        assertOpciones("publish", rest, ["--plan", "--check", "--yes"]);
        return handlePublish(rest);
    }

    assertOpciones(action, rest, ["--plan"]);
    const isPlan = rest.includes("--plan");

    if (action === "setup") {
        const cmd = powershellCmd("scripts/setup-desktop.ps1");
        console.log(`setup ${appName}\nDirectorio: ${root}\nComando: ${cmd.join(" ")}`);
        if (isPlan) return 0;
        const child = Bun.spawn(cmd, { cwd: root, stdin: "inherit", stdout: "inherit", stderr: "inherit" });
        return (await child.exited) ?? 0;
    }

    if (action === "dev") {
        const cmd = [...pythonCmd, join(root, "src-flet", "main.py")];
        const env = { PYTHONPATH: `${join(root, "src")};${join(root, "src-flet")}` };
        console.log(`dev ${appName}\nDirectorio: ${root}\nComando: ${cmd.join(" ")}\nEntorno   : PYTHONPATH=${env.PYTHONPATH}`);
        if (isPlan) return 0;
        const child = Bun.spawn(cmd, { cwd: root, env: { ...process.env, ...env }, stdin: "inherit", stdout: "inherit", stderr: "inherit" });
        return (await child.exited) ?? 0;
    }

    if (action === "check") {
        const pasos = [
            { titulo: "Verificando sintaxis de Python", cmd: [...pythonCmd, "-m", "compileall", "-q", "src", "src-flet", "tests"] },
            { titulo: "Verificando la importación de motor e interfaz", cmd: [...pythonCmd, "-c", IMPORT_SMOKE] },
        ];
        console.log(`check ${appName}\nDirectorio: ${root}`);
        if (isPlan) {
            for (const paso of pasos) console.log(`  ${paso.titulo}: ${paso.cmd.join(" ")}`);
            return 0;
        }
        const codigo = await runPasos(pasos, false);
        if (codigo !== 0) return codigo;

        console.log("\n==> Verificando que los scripts no fijen rutas absolutas al disco local");
        const hallazgos = rutasAbsolutasEnScripts();
        if (hallazgos.length) {
            console.error("❌ Rutas absolutas detectadas en scripts/:");
            for (const hallazgo of hallazgos) console.error(`   ${hallazgo}`);
            return 1;
        }
        console.log("   Sin rutas absolutas en scripts/.");
        console.log("\n✅ check completado");
        return 0;
    }

    if (action === "test") {
        const cmd = [...pythonCmd, "-m", "unittest", "discover", "-s", "tests", "-v"];
        console.log(`test ${appName}\nDirectorio: ${root}\nComando: ${cmd.join(" ")}`);
        if (isPlan) return 0;
        const child = Bun.spawn(cmd, { cwd: root, stdin: "inherit", stdout: "inherit", stderr: "inherit" });
        return (await child.exited) ?? 0;
    }

    if (action === "build") {
        const uv = findUv();
        const paquete = uv
            ? [uv, "build", "--out-dir", join(root, "dist"), root]
            : [...pythonCmd, "-m", "build", "--outdir", join(root, "dist"), root];
        const pasos = [
            { titulo: "Verificando sintaxis de Python", cmd: [...pythonCmd, "-m", "compileall", "-q", "src", "src-flet", "tests"] },
            { titulo: "Generando los paquetes Python en dist/ (sin instalador)", cmd: paquete },
        ];
        console.log(`build ${appName}\nDirectorio: ${root}`);
        if (isPlan) {
            for (const paso of pasos) console.log(`  ${paso.titulo}: ${paso.cmd.join(" ")}`);
            return 0;
        }
        return runPasos(pasos, false);
    }

    if (action === "release") {
        const pasos = [
            { titulo: "Compilando el instalador de Windows (Inno Setup) en release/", cmd: powershellCmd("scripts/packaging/Build-Installer.ps1") },
            { titulo: "Generando los paquetes Python y los checksums en dist/ y release/", cmd: powershellCmd("scripts/release/build-release.ps1", ["-LocalOnly"]) },
        ];
        console.log(`release ${appName}\nDirectorio: ${root}`);
        if (isPlan) {
            for (const paso of pasos) console.log(`  ${paso.titulo}: ${paso.cmd.join(" ")}`);
            return 0;
        }
        return runPasos(pasos, false);
    }

    throw new Error(`Acción desconocida: ${action}. Usa mise setup, mise dev, mise build, mise check, mise test, mise release o mise publish.`);
}

if (import.meta.main) {
    const args = process.env.MISE_TASK_NAME
        ? [process.env.MISE_TASK_NAME, ...Bun.argv.slice(2)]
        : Bun.argv.slice(2);
    try {
        process.exit(await main(args));
    } catch (err: any) {
        console.error(err?.message ?? err);
        process.exit(1);
    }
}
