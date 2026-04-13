import { z } from "zod";
import type { RouteDecision } from "./router";

/**
 * Planner layer (CodeBot 5-layer system)
 * Role:
 * - Produce a strict blueprint (file changes + responsibilities + steps).
 * - NO code output. Only a plan that Engineer must implement verbatim.
 */

export const PlanFileChangeSchema = z.object({
  path: z.string().min(1),
  changeType: z.enum(["create", "modify", "delete"]),
  purpose: z.string().min(1),
  // guardrails: what NOT to do inside this file
  doNotTouch: z.array(z.string()).default([]),
});

export const PlanStepSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  description: z.string().min(1),
  // which layer primarily executes it
  owner: z.enum(["planner", "engineer", "auditor", "corrector", "verifier"]),
  // command hints (optional, because you require explicit commands per step)
  commands: z.array(z.string()).default([]),
  // what success looks like
  acceptance: z.array(z.string()).default([]),
});

export const PlanBlueprintV1Schema = z.object({
  schema: z.literal("PlanBlueprintV1"),

  // High-level
  goal: z.string().min(1),
  route: z.object({
    kind: z.string().min(1),
    modelTier: z.enum(["fast", "reasoning"]),
    confidence: z.number().min(0).max(1),
  }),

  // Inputs / constraints
  assumptions: z.array(z.string()).default([]),
  requiredUserInputs: z.array(z.string()).default([]),
  invariants: z.array(z.string()).default([]),

  // What will change
  fileChanges: z.array(PlanFileChangeSchema).default([]),

  // Execution plan
  steps: z.array(PlanStepSchema).min(1),

  // Risk control
  risks: z.array(
    z.object({
      risk: z.string().min(1),
      mitigation: z.string().min(1),
    })
  ).default([]),
});

export type PlanBlueprintV1 = z.infer<typeof PlanBlueprintV1Schema>;

export type PlannerInput = {
  userText: string;
  routeDecision: RouteDecision;
  // Optional: known invariants from caller (ex: "Do not touch OAuth cookie path /codebot")
  pinnedInvariants?: string[];
};

/**
 * Planner entry point:
 * returns a strict PlanBlueprintV1 JSON object (validated by zod).
 */
export function plan(input: PlannerInput): PlanBlueprintV1 {
  const text = (input.userText ?? "").trim();
  const rd = input.routeDecision;

  const pinned = input.pinnedInvariants ?? [];

  // Base invariants (global to CodeBot system)
  const invariants: string[] = [
    "Planner outputs blueprint only (no code).",
    "Engineer must follow blueprint exactly (no scope creep).",
    "All outputs are strict JSON between layers.",
    "Changes must be file-by-file with explicit commands.",
    ...pinned,
  ];

  // Minimal assumptions (keep conservative, avoid hallucination)
  const assumptions: string[] = [
    "Repository paths provided by caller are correct.",
    "Caller will run commands manually and paste errors/logs back if any.",
  ];

  // Require user inputs when ambiguous (Planner should not guess)
  const requiredUserInputs: string[] = [];
  if (text.length === 0) requiredUserInputs.push("Describe what you want to accomplish.");

  // Infer likely fileChanges ONLY when user explicitly requests file work.
  // Otherwise leave empty and let the next turn specify.
  const fileChanges: Array<z.infer<typeof PlanFileChangeSchema>> = [];

  // Core steps: plan -> engineer -> auditor -> corrector -> verifier
  const steps: Array<z.infer<typeof PlanStepSchema>> = [
    {
      id: "S1",
      title: "Confirm scope + invariants",
      description:
        "Restate the exact objective, list what will NOT be touched, and identify any required inputs before code generation.",
      owner: "planner",
      commands: [],
      acceptance: [
        "Objective is unambiguous.",
        "Invariants are explicit and acknowledged.",
        "Any missing info is listed (not guessed).",
      ],
    },
    {
      id: "S2",
      title: "Engineer implements blueprint file-by-file",
      description:
        "Engineer creates/edits only the files listed in fileChanges, matching responsibilities exactly.",
      owner: "engineer",
      commands: ["# commands are provided per file by Engineer output in later layer"],
      acceptance: [
        "Only listed files are changed.",
        "No placeholder logic added unless explicitly allowed.",
      ],
    },
    {
      id: "S3",
      title: "Auditor checks imports, reachability, and invariants",
      description:
        "Auditor validates that code matches plan, uses real imports, and does not violate pinned invariants.",
      owner: "auditor",
      commands: ["# run lint/typecheck/tests as applicable"],
      acceptance: [
        "No undefined symbols / fabricated packages.",
        "No invariant violations.",
      ],
    },
    {
      id: "S4",
      title: "Corrector applies surgical fixes only where Auditor flags issues",
      description:
        "Corrector patches only the faulty sections without rewriting unrelated code.",
      owner: "corrector",
      commands: [],
      acceptance: ["Audit issues are resolved with minimal diffs."],
    },
    {
      id: "S5",
      title: "Verifier runs final checks (typecheck/tests/schema)",
      description:
        "Verifier runs the final command set and confirms outputs meet constraints (JSON validity, build passes, etc.).",
      owner: "verifier",
      commands: ["# e.g. pnpm -C backend-ts test / typecheck / lint"],
      acceptance: [
        "Commands pass cleanly (or failures are fully explained with next actions).",
      ],
    },
  ];

  // Risks (generic but useful)
  const risks = [
    {
      risk: "Planner makes assumptions about file paths or architecture.",
      mitigation: "Planner only uses paths explicitly provided by caller/user.",
    },
    {
      risk: "Engineer adds scope creep or changes invariants.",
      mitigation: "Auditor enforces invariants and fileChanges list strictly.",
    },
  ];

  const blueprint: PlanBlueprintV1 = {
    schema: "PlanBlueprintV1",
    goal:
      text.length > 0
        ? text.slice(0, 280) + (text.length > 280 ? "…" : "")
        : "Unspecified goal",
    route: {
      kind: rd.kind,
      modelTier: rd.modelTier,
      confidence: rd.confidence,
    },
    assumptions,
    requiredUserInputs,
    invariants,
    fileChanges,
    steps,
    risks,
  };

  return PlanBlueprintV1Schema.parse(blueprint);
}
