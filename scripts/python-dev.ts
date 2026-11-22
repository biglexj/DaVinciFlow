import { existsSync } from "node:fs";
import { basename, dirname, join } from "node:path";

export async function runPythonDev(root: string, args: string[]): Promise<number> {
    if (args.some(arg => arg !== "--plan")) {
        throw new Error("Uso: mise dev py [--plan]");
    }
    const plan = args.includes("--plan");
    const branch = "v-python";
    const localRef = `refs/heads/${branch}`;
    const remoteRef = `refs/remotes/origin/${branch}`;

    function git(...argv: string[]): string {
        const result = Bun.spawnSync(["git", ...argv], { cwd: root, stderr: "pipe" });
        if (result.exitCode !== 0) {
            throw new Error(`git ${argv[0]}: ${result.stderr.toString().trim()}`);
        }
        return result.stdout.toString();
    }

    function hasRef(ref: string): boolean {
        return Bun.spawnSync(["git", "show-ref", "--verify", "--quiet", ref], { cwd: root }).exitCode === 0;
    }

    const existing = git("worktree", "list", "--porcelain", "-z")
        .split("\0\0")
        .map(record => record.split("\0"))
        .find(fields => fields.includes(`branch ${localRef}`))?.[0]
        ?.slice("worktree ".length);
    const directory = existing ?? join(dirname(root), `${basename(root)}-Flet`);
    if (!existing) {
        if (plan) {
            console.log(`mise dev py preparará la rama ${branch} en ${directory}.`);
            return 0;
        }
        if (hasRef(localRef)) {
            git("worktree", "add", directory, branch);
        } else {
            if (!hasRef(remoteRef)) git("fetch", "origin", `${localRef}:${remoteRef}`);
            git("worktree", "add", "--track", "-b", branch, directory, `origin/${branch}`);
        }
    }

    const script = join(directory, "scripts", "mise-task.ts");
    if (!existsSync(script)) throw new Error(`El lanzador Python no está disponible en ${directory}.`);
    const env = { ...process.env };
    delete env.MISE_TASK_NAME;
    const child = Bun.spawn([process.execPath, script, "dev", "py", ...args], {
        cwd: directory, env, stdin: "inherit", stdout: "inherit", stderr: "inherit",
    });
    return await child.exited;
}
