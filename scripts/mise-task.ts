#!/usr/bin/env bun
import { join, resolve } from "node:path";
import { runGpuiTask } from "./gpui-task.ts";

const root = resolve(import.meta.dir, "..");
const cli = Bun.argv.slice(2);
const [action, ...args] = process.env.MISE_TASK_NAME ? [process.env.MISE_TASK_NAME, ...cli] : cli;

async function main(): Promise<number> {
    if (action !== "setup") {
        return runGpuiTask(action ?? "--help", args, root);
    }
    if (args.includes("--help")) {
        console.log("mise setup [--plan] prepara las dependencias de los adaptadores de Resolve y Aurora.");
        return 0;
    }
    if (args.some(arg => arg !== "--plan")) {
        throw new Error("Uso: mise setup [--plan]");
    }
    const script = join(root, "scripts", "setup-compat.ps1");
    if (args.includes("--plan")) {
        console.log(`powershell.exe -NoProfile -File "${script}"`);
        return 0;
    }
    const child = Bun.spawn(["powershell.exe", "-NoProfile", "-File", script], {
        cwd: root, stdin: "inherit", stdout: "inherit", stderr: "inherit",
    });
    return child.exited;
}

try {
    process.exitCode = await main();
} catch (error) {
    console.error(error instanceof Error ? error.message : error);
    process.exitCode = 1;
}
