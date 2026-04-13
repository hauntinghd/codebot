import { z } from "zod";
import { PlanBlueprintV1Schema, type PlanBlueprintV1 } from "./planner";
import { EngineerOutputV1Schema, type EngineerOutputV1 } from "./engineer";
import { AuditReportV1Schema, type AuditReportV1 } from "./auditor";
import { parseStrictJson } from "../utils/straightjson";

/**
 * Corrector layer (CodeBot 5-layer system)
 * Role:
 * - Receive Auditor report
 * - Regenerate ONLY faulty parts (surgical edits)
 * - Output a new EngineerOutputV1 (same schema) for re-audit
 *
 * Corrector does NOT apply changes to disk. It generates patch payloads for the orchestrator to apply.
 */

export const CorrectorModeSchema = z.enum(["surgical"]);

export const CorrectorResultV1Schema = z.object({
  schema: z.literal("CorrectorResultV1"),
  ok: z.boolean(),
  mode: CorrectorModeSchema.default("surgical"),
  attempt: z.number().int().min(1),
  /**
   * The corrected engineer output (still EngineerOutputV1).
   * If ok=false, this may be omitted.
   */
  engineerOutput: EngineerOutputV1Schema.optional(),
  /**
   * Human-readable notes (for logging)
   */
  notes: z.array(z.string()).default([]),
});

export type CorrectorResultV1 = z.infer<typeof CorrectorResultV1Schema>;

/**
 * Minimal interface for whatever model/client you use.
 * (Could be Grok, OpenAI, local, etc.)
 * We keep this abstract so we don't bake in provider hallucinations.
 */
export interface LLMClient {
  generate(args: { prompt: string }): Promise<string>;
}

/**
 * Stable hash helper must match planner/engineer/auditor hashing.
 * Duplicated intentionally (avoid circular deps).
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

function normPath(p: string): string {
  return p.replace(/^\.\/+/, "").replace(/\/+/g, "/").trim();
}

function unique<T>(arr: T[]): T[] {
  return Array.from(new Set(arr));
}

function buildSurgicalTargets(audit: AuditReportV1): string[] {
  // Prefer explicit fixPaths. Fallback to error issue paths.
  const fromFixPaths = (audit.fixPaths ?? []).map(normPath).filter(Boolean);
  const fromIssues = audit.issues
    .filter((i) => i.severity === "error" && typeof i.path === "string" && i.path.trim().length > 0)
    .map((i) => normPath(i.path!));

  return unique([...fromFixPaths, ...fromIssues]).filter(Boolean);
}

function renderIssues(audit: AuditReportV1): string {
  const errs = audit.issues.filter((i) => i.severity === "error");
  if (errs.length === 0) return "NO_ERRORS";

  return errs
    .map((i, idx) => {
      const parts = [
        `#${idx + 1}`,
        `id=${i.id}`,
        `title=${i.title}`,
        i.path ? `path=${i.path}` : "",
        i.rule ? `rule=${i.rule}` : "",
        `detail=${i.detail}`,
        i.suggestion ? `suggestion=${i.suggestion}` : "",
      ].filter(Boolean);
      return parts.join(" | ");
    })
    .join("\n");
}

function buildCorrectorPrompt(args: {
  blueprint: PlanBlueprintV1;
  previous: EngineerOutputV1;
  audit: AuditReportV1;
}): string {
  const { blueprint, previous, audit } = args;
  const expectedHash = blueprintHash(blueprint);
  const targets = buildSurgicalTargets(audit);

  // IMPORTANT: corrector must not re-plan. It must patch within blueprint constraints.
  return [
    "You are CodeBot Layer 5: Corrector.",
    "",
    "GOAL:",
    "- Fix ONLY what Auditor flagged.",
    "- Produce a corrected EngineerOutputV1 JSON object.",
    "- Surgical changes only. No scope expansion.",
    "",
    "HARD RULES:",
    `- The blueprintHash MUST equal: ${expectedHash}`,
    "- DO NOT add new files not present in blueprint.fileChanges.",
    "- DO NOT delete files unless blueprint explicitly includes delete for that path.",
    "- ONLY modify changes for these target paths (surgical set):",
    ...targets.map((t) => `  - ${t}`),
    "",
    "OUTPUT FORMAT:",
    "- Output MUST be a single JSON object (no markdown, no code fences).",
    "- It MUST validate against EngineerOutputV1 schema.",
    "",
    "PLANNER BLUEPRINT (reference):",
    JSON.stringify(blueprint),
    "",
    "PREVIOUS ENGINEER OUTPUT (you must patch this, not rewrite everything):",
    JSON.stringify(previous),
    "",
    "AUDITOR ERROR REPORT:",
    renderIssues(audit),
    "",
    "INSTRUCTIONS:",
    "- Keep all unchanged changes exactly as-is.",
    "- Replace only the specific broken change entries for target paths.",
    "- Ensure create/modify changes include exactly one payload: fullContent OR unifiedDiff.",
    "- Ensure no unplanned paths or unplanned actions.",
  ].join("\n");
}

export async function runCorrectorOnce(args: {
  llm: LLMClient;
  blueprint: PlanBlueprintV1;
  previousEngineerOutput: EngineerOutputV1;
  audit: AuditReportV1;
  attempt?: number;
}): Promise<CorrectorResultV1> {
  const blueprint = PlanBlueprintV1Schema.parse(args.blueprint);
  const previous = EngineerOutputV1Schema.parse(args.previousEngineerOutput);
  const audit = AuditReportV1Schema.parse(args.audit);

  const attempt = args.attempt ?? 1;

  // If there are no errors, we don't touch anything.
  const hasErrors = audit.issues.some((i) => i.severity === "error");
  if (!hasErrors) {
    return CorrectorResultV1Schema.parse({
      schema: "CorrectorResultV1",
      ok: true,
      mode: "surgical",
      attempt,
      engineerOutput: previous,
      notes: ["No audit errors. Corrector returned previous EngineerOutput unchanged."],
    });
  }

  const prompt = buildCorrectorPrompt({ blueprint, previous, audit });

  let raw = "";
  try {
    raw = await args.llm.generate({ prompt });
  } catch (e: any) {
    return CorrectorResultV1Schema.parse({
      schema: "CorrectorResultV1",
      ok: false,
      mode: "surgical",
      attempt,
      notes: [`LLM call failed: ${String(e?.message ?? e)}`],
    });
  }

  let parsed: unknown;
  try {
    parsed = parseStrictJson(raw);
  } catch (e: any) {
    return CorrectorResultV1Schema.parse({
      schema: "CorrectorResultV1",
      ok: false,
      mode: "surgical",
      attempt,
      notes: [
        "Corrector output was not valid strict JSON.",
        `Parse error: ${String(e?.message ?? e)}`,
        "Raw output captured for debugging (truncated):",
        raw.slice(0, 800),
      ],
    });
  }

  try {
    const engineerOutput = EngineerOutputV1Schema.parse(parsed);

    // Defensive: ensure hash matches expected
    const expectedHash = blueprintHash(blueprint);
    if (engineerOutput.blueprintHash !== expectedHash) {
      return CorrectorResultV1Schema.parse({
        schema: "CorrectorResultV1",
        ok: false,
        mode: "surgical",
        attempt,
        notes: [
          `Corrector produced wrong blueprintHash. expected=${expectedHash} got=${engineerOutput.blueprintHash}`,
          "Do not apply these changes.",
        ],
      });
    }

    // Defensive: ensure targets were respected (no new paths)
    const targets = new Set(buildSurgicalTargets(audit));
    const plannedPaths = new Set(blueprint.fileChanges.map((c) => normPath(c.path)));

    for (const ch of engineerOutput.changes) {
      const p = normPath(ch.path);
      // must be planned, always
      if (!plannedPaths.has(p)) {
        return CorrectorResultV1Schema.parse({
          schema: "CorrectorResultV1",
          ok: false,
          mode: "surgical",
          attempt,
          notes: [`Corrector attempted to change unplanned path: ${p}`],
        });
      }
      // Corrector is allowed to keep non-target changes unchanged, but it must not introduce *new* modifications
      // outside targets. We can't diff contents here reliably, so we enforce a simpler rule:
      // If a path was not in targets, it must match exactly the previous Engineer change entry for that path.
      if (!targets.has(p)) {
        const prev = previous.changes.find((x) => normPath(x.path) === p);
        if (!prev || JSON.stringify(prev) !== JSON.stringify(ch)) {
          return CorrectorResultV1Schema.parse({
            schema: "CorrectorResultV1",
            ok: false,
            mode: "surgical",
            attempt,
            notes: [
              `Corrector modified a non-target path (${p}).`,
              "Corrector must be surgical: only modify paths in audit.fixPaths / error issue paths.",
            ],
          });
        }
      }
    }

    return CorrectorResultV1Schema.parse({
      schema: "CorrectorResultV1",
      ok: true,
      mode: "surgical",
      attempt,
      engineerOutput,
      notes: ["Corrector produced a candidate EngineerOutputV1 for re-audit."],
    });
  } catch (e: any) {
    return CorrectorResultV1Schema.parse({
      schema: "CorrectorResultV1",
      ok: false,
      mode: "surgical",
      attempt,
      notes: [
        "Corrector output failed EngineerOutputV1 schema validation.",
        `Validation error: ${String(e?.message ?? e)}`,
        "Raw output captured for debugging (truncated):",
        raw.slice(0, 800),
      ],
    });
  }
}
