import { join } from "node:path";

/** Comandos de la demo nativa; Flet conserva sus tareas actuales. */
export async function runGpuiTask(action: string, args: string[], root: string): Promise<number> {
    if (args.includes("--help")) {
        console.log("DaVinci Flow: mise <dev-gpui|build-gpui|check-gpui|test-gpui> [--plan]\n" +
            "dev-gpui admite además la ruta de un archivo .srt. Estas tareas no publican ni instalan la demo.");
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
        throw new Error("dev-gpui admite --plan y, opcionalmente, la ruta de un archivo .srt.");
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
    for (const cmd of commands) {
        console.log(cmd.join(" "));
        if (plan) continue;
        const child = Bun.spawn(cmd, { cwd: root, stdin: "inherit", stdout: "inherit", stderr: "inherit" });
        const code = await child.exited;
        if (code !== 0) return code;
    }
    return 0;
}
