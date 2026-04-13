import { z } from "zod";

/**
 * strictJson.ts
 *
 * Purpose:
 * - Parse LLM output into JSON without "best effort" guessing.
 * - Extract JSON from common wrappers (```json ... ```, leading prose, etc.) safely.
 * - Validate against a Zod schema and produce actionable error messages.
 *
 * RULES:
 * - If JSON cannot be extracted and parsed => throw.
 * - If schema validation fails => throw (with details).
 * - Never silently coerce into a "close enough" shape.
 */

export class StrictJsonError extends Error {
  public readonly code:
    | "NO_JSON_FOUND"
    | "JSON_PARSE_FAILED"
    | "SCHEMA_VALIDATION_FAILED"
    | "EMPTY_INPUT";

  public readonly details?: Record<string, unknown>;

  constructor(
    code: StrictJsonError["code"],
    message: string,
    details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "StrictJsonError";
    this.code = code;
    this.details = details;
  }
}

function normalizeInput(input: unknown): string {
  if (typeof input !== "string") {
    throw new StrictJsonError(
      "EMPTY_INPUT",
      "Model output was not a string (cannot parse).",
      { typeof: typeof input },
    );
  }
  const s = input.trim();
  if (!s) {
    throw new StrictJsonError("EMPTY_INPUT", "Model output was empty.");
  }
  return s;
}

/**
 * Extract a single JSON object/array from a string.
 * Supports:
 * - ```json ... ```
 * - ``` ... ```
 * - Raw JSON embedded in prose (we locate the first {/[ and match balanced brackets)
 */
export function extractJsonBlock(raw: string): string {
  const s = normalizeInput(raw);

  // 1) fenced code block ```json ... ``` or ``` ... ```
  const fence = s.match(/```(?:json)?\s*([\s\S]*?)\s*```/i);
  if (fence?.[1]) {
    const inner = fence[1].trim();
    // If inner starts with { or [, assume it's JSON.
    if (inner.startsWith("{") || inner.startsWith("[")) return inner;
  }

  // 2) find first "{" or "[" and then scan for balanced close
  const firstObj = s.indexOf("{");
  const firstArr = s.indexOf("[");

  let start = -1;
  let openChar: "{" | "[" | null = null;

  if (firstObj === -1 && firstArr === -1) {
    throw new StrictJsonError(
      "NO_JSON_FOUND",
      "No JSON object/array start found in model output.",
      { preview: s.slice(0, 400) },
    );
  }

  if (firstObj !== -1 && (firstArr === -1 || firstObj < firstArr)) {
    start = firstObj;
    openChar = "{";
  } else {
    start = firstArr;
    openChar = "[";
  }

  const closeChar = openChar === "{" ? "}" : "]";
  let depth = 0;
  let inString = false;
  let escaped = false;

  for (let i = start; i < s.length; i++) {
    const ch = s[i];

    if (inString) {
      if (escaped) {
        escaped = false;
        continue;
      }
      if (ch === "\\") {
        escaped = true;
        continue;
      }
      if (ch === '"') inString = false;
      continue;
    } else {
      if (ch === '"') {
        inString = true;
        continue;
      }
      if (ch === openChar) depth++;
      if (ch === closeChar) depth--;

      // Handle nested opposite bracket types too (so {"a":[1,2]} works)
      if (openChar === "{" && ch === "[") depth += 0; // tracked by closeChar only for primary
      if (openChar === "[" && ch === "{") depth += 0;

      if (depth === 0) {
        const candidate = s.slice(start, i + 1).trim();
        if (candidate.startsWith("{") || candidate.startsWith("[")) {
          return candidate;
        }
        break;
      }
    }
  }

  throw new StrictJsonError(
    "NO_JSON_FOUND",
    "Found JSON start, but could not find balanced end.",
    { startIndex: start, preview: s.slice(start, start + 500) },
  );
}

export function parseStrictJson(raw: string): unknown {
  const jsonText = extractJsonBlock(raw);
  try {
    return JSON.parse(jsonText);
  } catch (err) {
    throw new StrictJsonError(
      "JSON_PARSE_FAILED",
      "JSON.parse failed for extracted JSON block.",
      {
        extractedPreview: jsonText.slice(0, 600),
        error: err instanceof Error ? err.message : String(err),
      },
    );
  }
}

/**
 * Parse + validate output against a schema.
 * Returns strongly typed data.
 */
export function parseAndValidate<TSchema extends z.ZodTypeAny>(
  raw: string,
  schema: TSchema,
): z.infer<TSchema> {
  const parsed = parseStrictJson(raw);

  const result = schema.safeParse(parsed);
  if (!result.success) {
    const issues = result.error.issues.map((i) => ({
      path: i.path.join("."),
      message: i.message,
      code: i.code,
    }));

    throw new StrictJsonError(
      "SCHEMA_VALIDATION_FAILED",
      "Schema validation failed for model output.",
      {
        issues,
        parsedPreview: JSON.stringify(parsed, null, 2).slice(0, 1200),
      },
    );
  }

  return result.data;
}

/**
 * Utility: stringify an object to JSON for prompts/logs with stable formatting.
 * (No trailing commas, no weird markdown.)
 */
export function stableJson(obj: unknown): string {
  return JSON.stringify(obj, null, 2);
}
