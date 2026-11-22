import { existsSync } from "node:fs";
import { delimiter, join } from "node:path";

/** Comandos de la interfaz nativa Rust + GPUI. */
export async function runGpuiTask(action: string, args: string[], root: string): Promise<number> {
    if (args.includes("--help")) {
        console.log("DaVinci Flow: mise <dev|build-gpui|check-gpui|test-gpui> [--plan]\n" +
            "mise dev admite una ruta .srt. Usa mise dev py para abrir Python/Flet.");
        return 0;
    }
    const command = action.replace(/-gpui$/, "");
    if (!new Set(["dev", "build", "check", "test"]).has(command)) {
        throw new Error(`Tarea GPUI desconocida: ${action}`);
    }
    const plan = args.includes("--plan");
    const extras = args.filter(arg => arg !== "--plan");
    if (command !== "dev" && extras.length) throw new Error(`${action} solo admite --plan.`);
    if (extras.length > 1 || extras.some(arg => arg.startsWith("-") || !arg.toLowerCase().endsWith(".srt"))) {
        throw new Error("Uso: mise dev [archivo.srt] [--plan] o mise dev py [--plan].");
    }
    const manifest = ["--manifest-path", join(root, "src-gpui", "Cargo.toml"), "--locked"];
    const commands: string[][] = command === "dev"
        ? [["cargo", "run", ...manifest, ...(extras.length ? ["--", ...extras] : [])]]
        : command === "build"
            ? [["cargo", "build", ...manifest]]
            : command === "test"
                ? [["cargo", "test", ...manifest, "--lib"]]
                : [["cargo", "fmt", "--manifest-path", join(root, "src-gpui", "Cargo.toml"), "--", "--check"],
                   ["cargo", "clippy", ...manifest, "--all-targets", "--", "-D", "warnings"]];
    const home = process.env.USERPROFILE || process.env.HOME || "";
    const extraPath: string[] = [];
    if (home) {
        for (const candidate of [
            join(home, ".rustup", "toolchains", "stable-x86_64-pc-windows-gnullvm", "bin"),
            join(home, ".rustup", "toolchains", "stable-x86_64-pc-windows-msvc", "bin"),
            join(home, ".cargo", "bin"),
        ]) {
            if (existsSync(candidate)) extraPath.push(candidate);
        }
    }
    const env = {
        ...process.env,
        PATH: [...extraPath, process.env.PATH || ""].filter(Boolean).join(delimiter),
    };
    for (const cmd of commands) {
        console.log(cmd.join(" "));
        if (plan) continue;
        const child = Bun.spawn(cmd, { cwd: root, env, stdin: "inherit", stdout: "inherit", stderr: "inherit" });
        const code = await child.exited;
        if (code !== 0) return code;
    }
    return 0;
}
