import { z } from "zod";
import { PlanBlueprintV1Schema, type PlanBlueprintV1 } from "./planner";
import { parseStrictJson } from "../utils/straightjson";

/**
 * Engineer layer (CodeBot 5-layer system)
 * Role:
 * - Convert Planner blueprint into explicit file-by-file changes.
 * - Must NOT change scope.
 * - Must NOT output freeform text between layers: strict JSON only.
 *
 * IMPORTANT:
 * - This file does NOT call an LLM directly; it defines schemas + parsing helpers.
 * - Your SSE/orchestrator layer can use buildEngineerPrompt() to call a model,
 *   then use parseEngineerOutput() to validate.
 */

export const EngineerFileActionSchema = z.enum(["create", "modify", "delete"]);

/**
 * Full-file payload: for small/medium files, safest and least ambiguous.
 * Patch payload: for surgical edits where you want minimal diffs.
 * You can support both; Auditor will enforce correctness.
 */
export const EngineerFileChangeSchema = z.object({
  path: z.string().min(1),
  action: EngineerFileActionSchema,

  /**
   * Choose ONE:
   * - fullContent: entire file content to write (preferred for "create", often for "modify")
   * - unifiedDiff: a standard unified diff to apply (preferred for surgical modifications)
   */
  fullContent: z.string().optional(),
  unifiedDiff: z.string().optional(),

  rationale: z.string().min(1),
  /**
   * Guardrails to prevent accidental breakage.
   * Example: "Do not change company name/URL literals"
   */
  constraintsChecked: z.array(z.string()).default([]),

  /**
   * Commands the user can run to apply/verify this single change.
   * You explicitly require commands for every update, so this stays per file.
   */
  commands: z.array(z.string()).default([]),
}).superRefine((val, ctx) => {
  const hasFull = typeof val.fullContent === "string" && val.fullContent.length > 0;
  const hasDiff = typeof val.unifiedDiff === "string" && val.unifiedDiff.length > 0;
  if (val.action === "delete") {
    if (hasFull || hasDiff) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Delete actions must not include fullContent/unifiedDiff.",
      });
    }
    return;
  }
  // create/modify: must include exactly one of fullContent or unifiedDiff
  if (hasFull === hasDiff) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Must provide exactly one of fullContent OR unifiedDiff for create/modify.",
    });
  }
});

export const EngineerOutputV1Schema = z.object({
  schema: z.literal("EngineerOutputV1"),
  blueprintHash: z.string().min(1),

  /**
   * Repeat the planner invariants here so Auditor can compare them.
   */
  invariants: z.array(z.string()).default([]),

  /**
   * Ordered changes. Auditor expects this order to match the plan’s intent.
   */
  changes: z.array(EngineerFileChangeSchema).min(1),

  /**
   * Optional: additional verification commands for the whole batch.
   */
  verifyCommands: z.array(z.string()).default([]),
});

export type EngineerOutputV1 = z.infer<typeof EngineerOutputV1Schema>;

export type EngineerInput = {
  blueprint: PlanBlueprintV1;
  /**
   * Optional: repository root (used only in commands, never assumed).
   */
  repoRoot?: string;
};

/**
 * Extremely simple stable hash so outputs can be correlated with a specific blueprint.
 * Not cryptographic. Deterministic.
 */
function blueprintHash(blueprint: PlanBlueprintV1): string {
  const s = JSON.stringify(blueprint);
  let h = 2166136261; // FNV-1a
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return `fnv1a_${(h >>> 0).toString(16)}`;
}

/**
 * Build the prompt you send to your model for the Engineer step.
 * This ensures the model stays locked to the Planner blueprint.
 */
export function buildEngineerPrompt(input: EngineerInput): string {
  const bp = PlanBlueprintV1Schema.parse(input.blueprint);
  const hash = blueprintHash(bp);

  return [
    "You are CodeBot Engineer.",
    "You MUST follow the provided Planner blueprint EXACTLY.",
    "You MUST output ONLY strict JSON matching EngineerOutputV1 schema.",
    "NO explanations, NO markdown, NO extra keys.",
    "",
    "Rules:",
    "- No scope creep. No new files unless explicitly required by blueprint.fileChanges.",
    "- If blueprint.requiredUserInputs is non-empty, you MUST return a single change that asks for missing inputs instead of coding.",
    "- Respect blueprint.invariants. Treat them as hard constraints.",
    "",
    "Return JSON with:",
    `{ "schema": "EngineerOutputV1", "blueprintHash": "${hash}", "invariants": [...], "changes": [...], "verifyCommands": [...] }`,
    "",
    "Planner blueprint:",
    JSON.stringify(bp),
  ].join("\n");
}

/**
 * Parse and validate raw model output for Engineer.
 * - extracts strict JSON (no markdown fences)
 * - validates schema
 * - ensures blueprintHash matches the blueprint we used
 */
export function parseEngineerOutput(args: {
  blueprint: PlanBlueprintV1;
  rawText: string;
}): EngineerOutputV1 {
  const bp = PlanBlueprintV1Schema.parse(args.blueprint);
  const expectedHash = blueprintHash(bp);

  const json = parseStrictJson(args.rawText);
  const out = EngineerOutputV1Schema.parse(json);

  if (out.blueprintHash !== expectedHash) {
    throw new Error(
      `EngineerOutput blueprintHash mismatch. expected=${expectedHash} got=${out.blueprintHash}`
    );
  }

  // Hard rule: Engineer must echo planner invariants (so Auditor can compare)
  // We do not require exact ordering, but must include all.
  const missing = bp.invariants.filter((inv) => !out.invariants.includes(inv));
  if (missing.length > 0) {
    throw new Error(`EngineerOutput missing invariants: ${missing.join(" | ")}`);
  }

  return out;
}
