CodeBot™ Architecture — High-level (MVP)

Goal
- Build CodeBot: an AI-first platform that generates production-grade SaaS apps from developer prompts.
- Target users: professional developers and small engineering teams building SaaS and automations.
- Constraint: Hugging Face only (HUGGINGFACEHUB_API_TOKEN / HF_TOKEN). No OpenAI.

Principles
- Simplicity: each file/module has one clear responsibility.
- Predictability: APIs and data models stable and documented.
- Auditability: BYOK for user-provided tokens; admin controls and logs.
- UX-first: generated projects look professional and are easy to deploy.

Core Components
- Frontend (SPA): simple professional UI for prompt input, project management, deploy, and logs.
- Backend (FastAPI): clear routers per domain (auth, projects, planning, build, deploy, usage).
- AI Layer (HF-only): `backend/utils/hf_client.py` wraps HF inference and planning models.
- BYOK: `backend/byok.py` encrypts/decrypts user tokens for ephemeral use.
- Storage: SQLite for MVP; layer with small ORM-like helpers in `backend/database.py`.
- CI/Deploy: container + systemd/unit and simple deploy scripts (start.sh, deploy.sh).

MVP Scope (First deliverable)
- Prompt → Architecture plan (SSE streaming) → Project scaffold generation → Zip download
- Authentication (email/Google OAuth), admin user assignment
- HF-only planning client; fallback to user's BYOK when available
- Minimal frontend: prompt UI, project list, project viewer, download/deploy

Developer conventions
- One router file per domain: `backend/routes/{auth,projects,architecture,build,deploy}`
- Services in `backend/services/*` for business logic, small pure functions
- AI-specific code in `backend/services/ai/*`
- Keep pure helpers in `backend/utils/*`

Next steps
1. Commit this doc and the persistent AI instructions.
2. Implement/verify HF-only client & BYOK flow.
3. Create skeletal routes for planning and build with clear interfaces.
4. Ship a minimal frontend using Vite + Tailwind with professional defaults.

