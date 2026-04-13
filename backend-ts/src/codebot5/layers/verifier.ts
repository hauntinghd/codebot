/**
 * CodeBot Layer 5: Verifier
 *
 * Purpose:
 * - Runs deterministic checks on a generated workspace before anything is shipped.
 * - Produces a strict, machine-readable report (no vibes, no "seems fine").
 *
 * This is the hard gate for the "perfect first delivery" invariant:
 * If verification fails -> NO OUTPUT -> trigger Corrector loop.
 */

import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { readFileSync } from "node:fs";
import * as path from "node:path";

export type VerifyCommand = {
  name: string;              // e.g. "typecheck", "lint", "test", "build"
  cmd: string;               // e.g. "npm"
  args: string[];            // e.g. ["run", "typecheck"]
  cwd?: string;              // optional override
  timeoutMs?: number;        // optional override per command
  required?: boolean;        // default true
};

export type VerifyRequest = {
  workspaceRoot: string;     // absolute or relative path to generated project
  commands?: VerifyCommand[];// optional override; otherwise auto-defaults
  env?: Record<string, string | undefined>;
  timeoutMs?: number;        // default 120000 (2 min) per command
  maxOutputChars?: number;   // default 60k per command (prevents log bombs)
};

export type VerifyCommandResult = {
  name: string;
  ok: boolean;
  exitCode: number | null;
  signal: NodeJS.Signals | null;
  durationMs: number;
  stdout: string;
  stderr: string;
  timedOut: boolean;
  required: boolean;
  commandLine: string;
};

export type VerifyReport = {
  ok: boolean;
  workspaceRoot: string;
  packageManager: "npm" | "pnpm" | "yarn" | "unknown";
  detected: {
    hasPackageJson: boolean;
    hasTsconfig: boolean;
    hasNext: boolean;
    hasVite: boolean;
  };
  results: VerifyCommandResult[];
  summary: {
    requiredTotal: number;
    requiredPassed: number;
    failedRequired: string[];
  };
};

function clamp(s: string, maxChars: number): string {
  if (s.length <= maxChars) return s;
  return s.slice(0, maxChars) + `\n… (truncated ${s.length - maxChars} chars)`;
}

function detectPackageManager(root: string): "npm" | "pnpm" | "yarn" | "unknown" {
  // lockfile priority
  if (existsSync(path.join(root, "pnpm-lock.yaml"))) return "pnpm";
  if (existsSync(path.join(root, "yarn.lock"))) return "yarn";
  if (existsSync(path.join(root, "package-lock.json"))) return "npm";
  if (existsSync(path.join(root, "package.json"))) return "npm";
  return "unknown";
}

function detectProject(root: string) {
  const pkgPath = path.join(root, "package.json");
  const hasPackageJson = existsSync(pkgPath);
  let pkgRaw = "";
  let pkg: any = null;

  if (hasPackageJson) {
    try {
      pkgRaw = readFileSync(pkgPath, "utf8");
      pkg = JSON.parse(pkgRaw);
    } catch {
      // leave pkg null
    }
  }

  const deps = {
    ...(pkg?.dependencies || {}),
    ...(pkg?.devDependencies || {}),
  };

  return {
    hasPackageJson,
    hasTsconfig: existsSync(path.join(root, "tsconfig.json")),
    hasNext: Boolean(deps["next"]),
    hasVite: Boolean(deps["vite"]),
  };
}

function defaultCommands(pm: "npm" | "pnpm" | "yarn" | "unknown", root: string): VerifyCommand[] {
  // We keep defaults conservative and deterministic.
  // - Always install (if needed) + typecheck + lint + test + build where applicable.
  // - If scripts are missing, we still run what we can.
  //
  // NOTE: The Corrector can add/modify commands for specific stacks.

  const run = (script: string) => {
    if (pm === "pnpm") return { cmd: "pnpm", args: ["run", script] };
    if (pm === "yarn") return { cmd: "yarn", args: [script] };
    return { cmd: "npm", args: ["run", script] };
  };

  const install = () => {
    if (pm === "pnpm") return { cmd: "pnpm", args: ["install", "--frozen-lockfile"] };
    if (pm === "yarn") return { cmd: "yarn", args: ["install", "--immutable"] };
    return { cmd: "npm", args: ["ci"] };
  };

  // If there's no lockfile, npm ci will fail. Fallback to npm install.
  const hasLock =
    existsSync(path.join(root, "pnpm-lock.yaml")) ||
    existsSync(path.join(root, "yarn.lock")) ||
    existsSync(path.join(root, "package-lock.json"));

  const installCmd =
    !hasLock && pm === "npm"
      ? { name: "install", cmd: "npm", args: ["install"], required: true }
      : { name: "install", ...install(), required: true };

  // Standard CodeBot expectations (you can add scripts in generated projects)
  return [
    installCmd,
    { name: "typecheck", ...run("typecheck"), required: true },
    { name: "lint", ...run("lint"), required: false },   // optional in some templates
    { name: "test", ...run("test"), required: false },   // optional if no tests
    { name: "build", ...run("build"), required: true },
  ];
}

function commandLine(cmd: string, args: string[]) {
  return [cmd, ...args].join(" ");
}

async function runCommand(opts: {
  name: string;
  cmd: string;
  args: string[];
  cwd: string;
  env: Record<string, string | undefined>;
  timeoutMs: number;
  maxOutputChars: number;
  required: boolean;
}): Promise<VerifyCommandResult> {
  const started = Date.now();

  return await new Promise((resolve) => {
    const child = spawn(opts.cmd, opts.args, {
      cwd: opts.cwd,
      env: { ...process.env, ...opts.env },
      shell: process.platform === "win32", // allows npm/pnpm/yarn on windows
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";
    let timedOut = false;

    const killTimer = setTimeout(() => {
      timedOut = true;
      try {
        child.kill("SIGKILL");
      } catch {
        // ignore
      }
    }, opts.timeoutMs);

    child.stdout?.on("data", (d) => {
      stdout += d.toString();
      if (stdout.length > opts.maxOutputChars * 2) stdout = clamp(stdout, opts.maxOutputChars * 2);
    });

    child.stderr?.on("data", (d) => {
      stderr += d.toString();
      if (stderr.length > opts.maxOutputChars * 2) stderr = clamp(stderr, opts.maxOutputChars * 2);
    });

    child.on("close", (code, signal) => {
      clearTimeout(killTimer);

      const durationMs = Date.now() - started;

      resolve({
        name: opts.name,
        ok: code === 0 && !timedOut,
        exitCode: code,
        signal,
        durationMs,
        stdout: clamp(stdout, opts.maxOutputChars),
        stderr: clamp(stderr, opts.maxOutputChars),
        timedOut,
        required: opts.required,
        commandLine: commandLine(opts.cmd, opts.args),
      });
    });

    child.on("error", (err) => {
      clearTimeout(killTimer);
      const durationMs = Date.now() - started;

      resolve({
        name: opts.name,
        ok: false,
        exitCode: null,
        signal: null,
        durationMs,
        stdout: "",
        stderr: String(err),
        timedOut,
        required: opts.required,
        commandLine: commandLine(opts.cmd, opts.args),
      });
    });
  });
}

/**
 * Main Verifier entrypoint.
 */
export async function verifyWorkspace(req: VerifyRequest): Promise<VerifyReport> {
  const workspaceRoot = path.resolve(req.workspaceRoot);

  const detected = detectProject(workspaceRoot);
  const pm = detectPackageManager(workspaceRoot);

  const timeoutMs = req.timeoutMs ?? 120_000;
  const maxOutputChars = req.maxOutputChars ?? 60_000;

  const commands = (req.commands && req.commands.length > 0)
    ? req.commands
    : defaultCommands(pm, workspaceRoot);

  // If no package.json, verification cannot proceed.
  if (!detected.hasPackageJson) {
    const fail: VerifyReport = {
      ok: false,
      workspaceRoot,
      packageManager: pm,
      detected,
      results: [{
        name: "precheck",
        ok: false,
        exitCode: null,
        signal: null,
        durationMs: 0,
        stdout: "",
        stderr: "Missing package.json in workspaceRoot. Verifier cannot run.",
        timedOut: false,
        required: true,
        commandLine: "precheck",
      }],
      summary: {
        requiredTotal: 1,
        requiredPassed: 0,
        failedRequired: ["precheck"],
      },
    };
    return fail;
  }

  const env = req.env ?? {};

  const results: VerifyCommandResult[] = [];
  for (const c of commands) {
    const res = await runCommand({
      name: c.name,
      cmd: c.cmd,
      args: c.args,
      cwd: c.cwd ? path.resolve(c.cwd) : workspaceRoot,
      env,
      timeoutMs: c.timeoutMs ?? timeoutMs,
      maxOutputChars,
      required: c.required ?? true,
    });
    results.push(res);

    // Hard stop: if a required command fails, don't waste time.
    if (!res.ok && res.required) break;
  }

  const required = results.filter(r => r.required);
  const requiredPassed = required.filter(r => r.ok);
  const failedRequired = required.filter(r => !r.ok).map(r => r.name);

  return {
    ok: failedRequired.length === 0,
    workspaceRoot,
    packageManager: pm,
    detected,
    results,
    summary: {
      requiredTotal: required.length,
      requiredPassed: requiredPassed.length,
      failedRequired,
    },
  };
}
