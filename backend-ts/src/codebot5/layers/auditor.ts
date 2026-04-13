import { z } from "zod";
import { PlanBlueprintV1Schema, type PlanBlueprintV1 } from "./planner";
import { EngineerOutputV1Schema, type EngineerOutputV1 } from "./engineer";
import { parseStrictJson } from "../utils/straightjson";

/**
 * Auditor layer (CodeBot 5-layer system)
 * Role:
 * - Verify Engineer output matches the Planner blueprint and invariants.
 * - Detect "hallucination class" issues: extra files, missing content, scope drift.
 *
 * NOTE:
 * - This file does not run TypeScript compilation. It validates structure + intent.
 * - If you want deeper checks (tsc/eslint/import resolution), wire those in verifyCommands
 *   and/or extend Auditor with optional runner hooks later.
 */

export const AuditSeveritySchema = z.enum(["info", "warn", "error"]);

export const AuditIssueSchema = z.object({
  id: z.string().min(1), // stable identifier for corrector targeting
  severity: AuditSeveritySchema,
  title: z.string().min(1),
  detail: z.string().min(1),
  /**
   * Optional: which file this issue refers to
   */
  path: z.string().optional(),
  /**
   * Optional: which invariant or blueprint rule was violated
   */
  rule: z.string().optional(),
  /**
   * Optional: suggested action for corrector ("provide fullContent", "remove extra file", etc.)
   */
  suggestion: z.string().optional(),
});

export const AuditReportV1Schema = z.object({
  schema: z.literal("AuditReportV1"),
  ok: z.boolean(),
  blueprintHash: z.string().min(1),
  issues: z.array(AuditIssueSchema).default([]),
  /**
   * If not ok, Corrector should only touch these paths (surgical fix).
   */
  fixPaths: z.array(z.string()).default([]),
  /**
   * Commands that can be run to further verify after applying changes.
   */
  verifyCommands: z.array(z.string()).default([]),
});

export type AuditReportV1 = z.infer<typeof AuditReportV1Schema>;

type NormalizePath = (p: string) => string;

/**
 * Normalize paths to avoid false mismatches.
 * - strips leading "./"
 * - collapses consecutive slashes
 */
function normPath(p: string): string {
  return p.replace(/^\.\/+/, "").replace(/\/+/g, "/").trim();
}

function mkIssue(partial: Partial<z.infer<typeof AuditIssueSchema>> & { id: string; title: string; detail: string }) {
  return AuditIssueSchema.parse({
    severity: "error",
    ...partial,
  });
}

/**
 * Stable hash helper must match engineer/planner hashing strategy.
 * We keep it duplicated intentionally (no circular deps).
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

function expectedChangeSet(blueprint: PlanBlueprintV1): {
  allowedPaths: Set<string>;
  allowedActionsByPath: Map<string, Set<string>>;
} {
  const allowedPaths = new Set<string>();
  const allowedActionsByPath = new Map<string, Set<string>>();

  for (const fc of blueprint.fileChanges) {
    const p = normPath(fc.path);
    allowedPaths.add(p);
    const s = allowedActionsByPath.get(p) ?? new Set<string>();
    s.add(fc.action);
    allowedActionsByPath.set(p, s);
  }

  return { allowedPaths, allowedActionsByPath };
}

function isNonEmptyString(x: unknown): x is string {
  return typeof x === "string" && x.trim().length > 0;
}

function validateEngineerChangeShape(ch: EngineerOutputV1["changes"][number], normalize: NormalizePath, issues: AuditReportV1["issues"]) {
  const p = normalize(ch.path);

  // delete must not include content
  if (ch.action === "delete") {
    if (isNonEmptyString(ch.fullContent) || isNonEmptyString(ch.unifiedDiff)) {
      issues.push(
        mkIssue({
          id: `delete_has_payload:${p}`,
          path: p,
          title: "Delete includes payload",
          detail: "Delete actions must not include fullContent or unifiedDiff.",
          suggestion: "Remove the payload from this delete change.",
          rule: "engineer.change.delete_no_payload",
        })
      );
    }
    return;
  }

  // create/modify must have exactly one payload
  const hasFull = isNonEmptyString(ch.fullContent);
  const hasDiff = isNonEmptyString(ch.unifiedDiff);
  if (hasFull === hasDiff) {
    issues.push(
      mkIssue({
        id: `payload_missing_or_ambiguous:${p}`,
        path: p,
        title: "Missing or ambiguous file payload",
        detail: "create/modify must provide exactly one of fullContent or unifiedDiff.",
        suggestion: "Provide fullContent OR unifiedDiff (exactly one).",
        rule: "engineer.change.payload_required",
      })
    );
  }
}

export function auditEngineerOutput(args: {
  blueprint: PlanBlueprintV1;
  engineerOutput: EngineerOutputV1;
  repoRoot?: string;
}): AuditReportV1 {
  const blueprint = PlanBlueprintV1Schema.parse(args.blueprint);
  const out = EngineerOutputV1Schema.parse(args.engineerOutput);

  const expectedHash = blueprintHash(blueprint);
  const issues: AuditReportV1["issues"] = [];

  // 1) Hash match
  if (out.blueprintHash !== expectedHash) {
    issues.push(
      mkIssue({
        id: "blueprint_hash_mismatch",
        title: "Blueprint hash mismatch",
        detail: `Engineer output was generated for a different blueprint. expected=${expectedHash} got=${out.blueprintHash}`,
        rule: "auditor.hash_match",
        suggestion: "Re-run Engineer using the correct Planner blueprint.",
      })
    );
  }

  // 2) Invariants match (Engineer must include all Planner invariants)
  const missingInv = blueprint.invariants.filter((inv) => !out.invariants.includes(inv));
  if (missingInv.length > 0) {
    issues.push(
      mkIssue({
        id: "missing_invariants",
        title: "Engineer output missing invariants",
        detail: `Engineer did not echo all planner invariants: ${missingInv.join(" | ")}`,
        rule: "auditor.invariants_echo",
        suggestion: "Engineer must include every Planner invariant in output.invariants.",
      })
    );
  }

  // 3) Scope control: allowed files/actions come only from blueprint.fileChanges
  const { allowedPaths, allowedActionsByPath } = expectedChangeSet(blueprint);

  // If blueprint says "requiredUserInputs" and not empty, engineer should not implement.
  if (blueprint.requiredUserInputs.length > 0) {
    issues.push(
      AuditIssueSchema.parse({
        id: "planner_requires_user_inputs",
        severity: "warn",
        title: "Planner requires user inputs",
        detail:
          "Planner blueprint lists requiredUserInputs. Engineer should not implement code until inputs are provided.",
        rule: "auditor.required_inputs",
        suggestion: "Return a single change that requests the missing inputs, instead of generating code.",
      })
    );
  }

  // validate each engineer change
  for (const ch of out.changes) {
    const p = normPath(ch.path);

    // shape checks
    validateEngineerChangeShape(ch, normPath, issues);

    // must be planned path
    if (!allowedPaths.has(p)) {
      issues.push(
        mkIssue({
          id: `unplanned_path:${p}`,
          path: p,
          title: "Unplanned file path (scope drift)",
          detail: `Engineer produced a change for "${p}" which is not present in Planner blueprint.fileChanges.`,
          rule: "auditor.no_unplanned_files",
          suggestion: "Remove this change OR update Planner blueprint to include it explicitly.",
        })
      );
      continue;
    }

    // must be allowed action for this path
    const allowedActions = allowedActionsByPath.get(p) ?? new Set<string>();
    if (!allowedActions.has(ch.action)) {
      issues.push(
        mkIssue({
          id: `unplanned_action:${p}`,
          path: p,
          title: "Unplanned action for file",
          detail: `Engineer used action="${ch.action}" for "${p}" but Planner does not allow it. Allowed: ${Array.from(
            allowedActions
          ).join(", ")}`,
          rule: "auditor.no_unplanned_actions",
          suggestion: "Change action to match the Planner, or update the Planner to explicitly allow this action.",
        })
      );
    }
  }

  // 4) Ensure all planned changes are present (no missing files)
  const produced = new Set(out.changes.map((c) => normPath(c.path)));
  for (const planned of allowedPaths) {
    if (!produced.has(planned)) {
      issues.push(
        mkIssue({
          id: `missing_planned_change:${planned}`,
          path: planned,
          title: "Missing planned file change",
          detail: `Planner blueprint requires a change for "${planned}", but Engineer did not include it.`,
          rule: "auditor.missing_planned_changes",
          suggestion: "Engineer must output a change for every path in blueprint.fileChanges.",
        })
      );
    }
  }

  // 5) Invariant reminders (simple textual enforcement)
  // You said: do not hallucinate about global CSS patches and do not change company name/URL.
  // We enforce that by requiring Planner to include explicit invariants and by ensuring
  // Engineer echoes them. We DO NOT attempt to regex the file contents here to avoid false positives.

  const ok = issues.every((i) => i.severity !== "error");

  // fixPaths: only the paths implicated by errors
  const fixPaths = Array.from(
    new Set(
      issues
        .filter((i) => i.severity === "error")
        .map((i) => i.path)
        .filter((p): p is string => typeof p === "string" && p.length > 0)
    )
  );

  // Combine verification commands (blueprint + engineer)
  const verifyCommands = Array.from(
    new Set([...(blueprint.verifyCommands ?? []), ...(out.verifyCommands ?? [])])
  );

  return AuditReportV1Schema.parse({
    schema: "AuditReportV1",
    ok,
    blueprintHash: expectedHash,
    issues,
    fixPaths,
    verifyCommands,
  });
}

/**
 * Optional helper: parse model output if you ever run Auditor via LLM.
 * Right now we keep Auditor deterministic, but this can be useful later.
 */
export function parseAuditReport(rawText: string): AuditReportV1 {
  const json = parseStrictJson(rawText);
  return AuditReportV1Schema.parse(json);
}
