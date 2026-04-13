import { z } from "zod";

export const FilesResponseSchema = z.object({
  files: z.record(z.string(), z.string()).min(1),
  devCommand: z.string().optional(),
});

export type FilesResponse = z.infer<typeof FilesResponseSchema>;

/**
 * Implement in your server.ts:
 *   import { registerBuildFilesRoute } from "./files_endpoint";
 *   registerBuildFilesRoute(fastifyOrApp, buildFilesWithXai);
 *
 * buildFilesWithXai(prompt) must return:
 *   { files: { "package.json": "...", ... }, devCommand?: "pnpm dev -- --host 0.0.0.0 --port 3000" }
 */
export function registerBuildFilesRoute(app: any, buildFilesWithXai: (prompt: string) => Promise<any>) {
  app.post("/api/build/files", async (req: any, reply: any) => {
    const prompt = String(req.body?.prompt || "").trim();
    if (!prompt) return reply.code(400).send({ error: "Missing prompt" });

    const raw = await buildFilesWithXai(prompt);
    const parsed = FilesResponseSchema.safeParse(raw);

    if (!parsed.success) {
      return reply.code(500).send({
        error: "Invalid files payload from LLM",
        issues: parsed.error.issues,
      });
    }

    return reply.send(parsed.data);
  });
}
