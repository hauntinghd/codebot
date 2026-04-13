import { z } from "zod";

/**
 * CodeBot 5-Layer Hallucination Prevention System (CodeBot5)
 *
 * Canonical rule:
 * - Layer files (router/planner/engineer/auditor/corrector/verifier) own their schemas.
 * - This file MUST NOT re-declare/export colliding schema names (ex: AuditIssueSchema).
 * - This file provides:
 *    1) A centralized registry ("CodeBot5Schemas") for consumers
 *    2) A stable "PipelineResult" envelope schema for orchestration persistence/telemetry
 *
 * Why: prevents TS2308 “already exported member …” errors when index.ts does `export *`.
 */

// --------- Import the canonical schemas from each layer ----------
import {
  RouteDecisionSchema,
  type RouteDecision,
} from "../layers/router";

import {
  PlanBlueprintV1Schema,
  type PlanBlueprintV1,
} from "../layers/planner";

import {
  EngineerOutputV1Schema,
  type EngineerOutputV1,
} from "../layers/engineer";

import {
  AuditIssueSchema,
  AuditReportV1Schema,
  type AuditReportV1,
} from "../layers/auditor";

import {
  CorrectorResultV1Schema,
  type CorrectorResultV1,
} from "../layers/corrector";

// NOTE: verifier.ts exports types + verifyWorkspace(). It returns VerifyReport.
// We *do not* redefine VerifyReport here. If you want it in the pipeline envelope,
// we keep it as `unknown` unless verifier exports a schema (it currently doesn't).
// (verifier.ts in your repo exports types, not zod schemas.)

/**
 * Central schema registry (for any consumer that wants "one import").
 * Do NOT add keys here that create naming collisions in index.ts star-exports.
 */
export const CodeBot5Schemas = {
  router: RouteDecisionSchema,
  planner: PlanBlueprintV1Schema,
  engineer: EngineerOutputV1Schema,
  auditIssue: AuditIssueSchema,
  auditor: AuditReportV1Schema,
  corrector: CorrectorResultV1Schema,
} as const;

// ---------- Non-colliding alias exports (safe for `export *`) ----------
// These names will NOT collide with layer exports.
export const RouterDecisionOutSchema = RouteDecisionSchema;
export const PlanBlueprintOutSchema = PlanBlueprintV1Schema;
export const EngineerOutputOutSchema = EngineerOutputV1Schema;
export const AuditIssueOutSchema = AuditIssueSchema;
export const AuditReportOutSchema = AuditReportV1Schema;
export const CorrectorResultOutSchema = CorrectorResultV1Schema;

// ---------- Orchestration / pipeline envelope ----------

/**
 * A stable “pipeline output” shape you can persist/log.
 * This matches your intent:
 * Prompt → Router → Planner → Engineer → Auditor → Corrector → (Auditor loop) → Final
 *
 * IMPORTANT:
 * - `corrector` is optional (only exists when auditor fails)
 * - `auditAfter` is optional (only exists if corrector ran and you audited again)
 * - `finalEngineerOutput` is the authoritative final change-set (post-correction if any)
 */
export const PipelineResultSchema = z.object({
  router: RouteDecisionSchema,
  blueprint: PlanBlueprintV1Schema,
  engineer: EngineerOutputV1Schema,

  auditBefore: AuditReportV1Schema,

  // Corrector runs only if auditBefore fails / requires fixes
  corrector: CorrectorResultV1Schema.optional(),

  // Optional second pass audit after corrections were applied
  auditAfter: AuditReportV1Schema.optional(),

  // Authoritative final output the rest of the system should apply
  finalEngineerOutput: EngineerOutputV1Schema,

  // Minimal traceability / UX
  finalSummary: z.string().min(1),

  // Optional telemetry / bookkeeping
  meta: z
    .object({
      // e.g. request id, conversation id, user id, etc.
      runId: z.string().min(1).optional(),
      startedAt: z.string().min(1).optional(),
      finishedAt: z.string().min(1).optional(),
      modelTier: z.string().min(1).optional(),
      iterations: z.number().int().min(1).optional(),
    })
    .optional(),
});

export type PipelineResult = z.infer<typeof PipelineResultSchema>;

// ---------- Convenience types (do not collide with schema const names) ----------
export type CodeBot5RouterDecision = RouteDecision;
export type CodeBot5Blueprint = PlanBlueprintV1;
export type CodeBot5EngineerOutput = EngineerOutputV1;
export type CodeBot5AuditReport = AuditReportV1;
export type CodeBot5CorrectorResult = CorrectorResultV1;
