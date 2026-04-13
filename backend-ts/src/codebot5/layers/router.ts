import { z } from "zod";

/**
 * Router layer (CodeBot 5-layer system)
 * Role:
 * - Classify request type + choose strategy (fast vs reasoning).
 * - Enforce hard invariants (no destructive ops, no unsafe output formats).
 * - Produce a strict JSON "RouteDecision" for Planner to follow.
 *
 * This file does NOT call any model. It only produces a decision object.
 */

export type RouteKind =
  | "coding"
  | "debugging"
  | "refactor"
  | "architecture"
  | "research"
  | "product"
  | "unknown";

export type ModelTier = "fast" | "reasoning";

export const RouteDecisionSchema = z.object({
  kind: z.enum([
    "coding",
    "debugging",
    "refactor",
    "architecture",
    "research",
    "product",
    "unknown",
  ]),
  modelTier: z.enum(["fast", "reasoning"]),
  confidence: z.number().min(0).max(1),

  // Safety + constraints
  allowed: z.boolean(),
  hardStops: z.array(z.string()).default([]),

  // What the Planner must output next
  nextSchema: z.enum([
    "PlanBlueprintV1", // file structure + tasks + constraints (no code)
  ]),

  // Context sizing hints
  context: z.object({
    needsRepoScan: z.boolean(),
    needsUserFiles: z.boolean(),
    needsLogs: z.boolean(),
    needsExactCommands: z.boolean(),
  }),

  // Minimal distilled intent for Planner
  intent: z.object({
    goal: z.string(),
    inputs: z.array(z.string()).default([]),
    outputs: z.array(z.string()).default([]),
    constraints: z.array(z.string()).default([]),
  }),
});

export type RouteDecision = z.infer<typeof RouteDecisionSchema>;

export type RouterInput = {
  userText: string;
  hasFiles?: boolean;
  hasLogs?: boolean;
  // optional: if your caller already knows this request is about codebase edits
  repoEdit?: boolean;
};

const LOWER_COMPLEXITY_HINTS = [
  "typo",
  "rename",
  "small change",
  "minor",
  "one line",
  "simple",
];

const HIGH_COMPLEXITY_HINTS = [
  "architecture",
  "orchestration",
  "schema",
  "design",
  "refactor",
  "migrate",
  "multi-step",
  "systemd",
  "nginx",
  "oauth",
  "stripe",
  "database",
  "production",
  "security",
];

function scoreComplexity(text: string): number {
  const t = text.toLowerCase();
  let score = 0;

  for (const w of HIGH_COMPLEXITY_HINTS) {
    if (t.includes(w)) score += 2;
  }
  for (const w of LOWER_COMPLEXITY_HINTS) {
    if (t.includes(w)) score -= 1;
  }

  // length as a weak signal
  if (t.length > 600) score += 1;
  if (t.length > 1400) score += 2;

  return score;
}

function detectKind(text: string): RouteKind {
  const t = text.toLowerCase();

  // strong signals first
  if (
    t.includes("bug") ||
    t.includes("error") ||
    t.includes("stack") ||
    t.includes("trace") ||
    t.includes("crash") ||
    t.includes("fails") ||
    t.includes("cannot") ||
    t.includes("issue")
  ) {
    return "debugging";
  }

  if (
    t.includes("refactor") ||
    t.includes("cleanup") ||
    t.includes("restructure") ||
    t.includes("rename") ||
    t.includes("move file")
  ) {
    return "refactor";
  }

  if (
    t.includes("architecture") ||
    t.includes("blueprint") ||
    t.includes("design") ||
    t.includes("system") ||
    t.includes("orchestration")
  ) {
    return "architecture";
  }

  if (
    t.includes("research") ||
    t.includes("look up") ||
    t.includes("compare") ||
    t.includes("sources") ||
    t.includes("citations")
  ) {
    return "research";
  }

  if (
    t.includes("pricing") ||
    t.includes("plan") ||
    t.includes("subscription") ||
    t.includes("stripe") ||
    t.includes("billing")
  ) {
    return "product";
  }

  // default: assume coding if it mentions files/code/tools
  if (
    t.includes("typescript") ||
    t.includes("ts") ||
    t.includes("node") ||
    t.includes("fastify") ||
    t.includes("fastapi") ||
    t.includes("react") ||
    t.includes("css") ||
    t.includes("tailwind") ||
    t.includes("endpoint") ||
    t.includes("router") ||
    t.includes("schema") ||
    t.includes("zod") ||
    t.includes("function") ||
    t.includes("file")
  ) {
    return "coding";
  }

  return "unknown";
}

/**
 * Minimal safety gate.
 * You can extend this later with your full "do not touch" and tenant safety rules.
 */
function safetyCheck(text: string): { allowed: boolean; hardStops: string[] } {
  const t = text.toLowerCase();
  const hardStops: string[] = [];

  // destructive system instructions (keep minimal and obvious)
  if (t.includes("rm -rf /") || t.includes("format disk") || t.includes("drop database")) {
    hardStops.push("Destructive system/database request detected.");
  }

  // disallowed output format: telling system to output non-JSON when schema requires JSON
  // (Router itself always returns structured object; this is about user trying to bypass)
  if (t.includes("ignore schema") || t.includes("no json") || t.includes("freeform only")) {
    hardStops.push("Attempt to bypass structured output constraints.");
  }

  return { allowed: hardStops.length === 0, hardStops };
}

/**
 * Main router entry.
 */
export function route(input: RouterInput): RouteDecision {
  const raw = (input.userText ?? "").trim();

  const { allowed, hardStops } = safetyCheck(raw);
  const kind = detectKind(raw);

  const complexity = scoreComplexity(raw);
  const modelTier: ModelTier = complexity >= 3 ? "reasoning" : "fast";

  // confidence is heuristic
  let confidence = 0.55;
  if (kind !== "unknown") confidence += 0.2;
  if (complexity >= 3) confidence += 0.1;
  if (raw.length > 80) confidence += 0.05;
  confidence = Math.max(0, Math.min(1, confidence));

  // context hints for Planner
  const needsLogs = Boolean(input.hasLogs) || kind === "debugging";
  const needsRepoScan = Boolean(input.repoEdit) || kind === "refactor" || kind === "architecture";
  const needsUserFiles = Boolean(input.hasFiles) || needsRepoScan;
  const needsExactCommands = kind === "debugging" || kind === "refactor" || Boolean(input.repoEdit);

  // distilled intent
  const goal =
    raw.length > 0
      ? raw.slice(0, 240) + (raw.length > 240 ? "…" : "")
      : "No goal provided";

  const decision: RouteDecision = {
    kind,
    modelTier,
    confidence,

    allowed,
    hardStops,

    nextSchema: "PlanBlueprintV1",

    context: {
      needsRepoScan,
      needsUserFiles,
      needsLogs,
      needsExactCommands,
    },

    intent: {
      goal,
      inputs: [],
      outputs: [],
      constraints: [
        "Return strict JSON only between layers.",
        "Planner must not emit code; blueprint only.",
        "No scope expansion without user approval.",
      ],
    },
  };

  // validate at runtime (fail fast if we ever break our own schema)
  return RouteDecisionSchema.parse(decision);
}
