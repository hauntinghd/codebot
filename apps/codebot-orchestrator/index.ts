import Fastify from "fastify";
import cors from "@fastify/cors";

const app = Fastify();
app.register(cors, { origin: true, credentials: true });

app.get("/health", async () => ({ ok: true }));

app.listen({ port: 9100, host: "0.0.0.0" }, () => {
  console.log("[CodeBot Builder Orchestrator] running on :9100");
});
