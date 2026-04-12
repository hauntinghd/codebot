"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import AuthGate from "@/components/AuthGate";
import ErrorBoundary from "@/components/ErrorBoundary";
import BuilderTopBar from "@/components/builder/BuilderTopBar";
import BuilderSidebar from "@/components/builder/BuilderSidebar";
import CodeEditorPanel from "@/components/builder/CodeEditorPanel";

type DeviceMode = "desktop" | "tablet" | "mobile";
type ViewMode = "preview" | "code";

type ChatRole = "user" | "assistant";
type ChatMessage = {
  role: ChatRole;
  content: string;
};

function safeId(): string {
  try {
    const c: any = globalThis.crypto;
    if (c?.randomUUID) return c.randomUUID();
  } catch {
    // ignore
  }
  return `proj_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

const API_BASE = process.env.NEXT_PUBLIC_CODEBOT_API_BASE || "/codebot/api";
const BASE = "/codebot";

const builderKeyframes = `
@keyframes cb-think-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}
`;

function EmptyPreview({ error }: { error?: string | null }) {
  return (
    <div style={{ textAlign: "center", maxWidth: 340, padding: 24 }}>
      <img
        src={`${BASE}/logo.png`}
        alt="CodeBot"
        width={56}
        height={56}
        style={{ borderRadius: "50%", margin: "0 auto 16px", display: "block", opacity: 0.7 }}
      />
      <div style={{ fontSize: 18, fontWeight: 600, color: "rgba(255,255,255,0.9)" }}>Preview Ready</div>
      <div style={{ fontSize: 13, color: "rgba(255,255,255,0.45)", marginTop: 8, lineHeight: 1.5 }}>
        Run a build to see your project here. CodeBot will generate the code and render a live preview.
      </div>
      {error ? <div style={{ marginTop: 12, fontSize: 13, color: "#ff4d4d" }}>{error}</div> : null}
    </div>
  );
}

type RunBuildPayload = {
  projectId: string;
  projectName: string;
  device: DeviceMode;
  view: ViewMode;
  prompt: string;
  messages: ChatMessage[];
  mode: string;
  model: string;
};

type RunBuildJsonResponse = {
  ok?: boolean;
  assistant?: string;
  previewUrl?: string;
  files?: Array<{ path: string; content: string }>;
  error?: string;
};

const LEFT_W_KEY = "cb_builder_left_w_v2";
const STATE_KEY = "cb_builder_state_v2";

const MIN_LEFT = 320;
const MAX_LEFT = 560;

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

function readSearchParams() {
  try {
    const url = new URL(window.location.href);
    const project = url.searchParams.get("project") || "";
    const name = url.searchParams.get("name") || "";
    return { project, name };
  } catch {
    return { project: "", name: "" };
  }
}

function stripBuilderSearchParamsFromUrl() {
  try {
    const url = new URL(window.location.href);
    const had = url.searchParams.has("project") || url.searchParams.has("name");
    if (!had) return;

    url.searchParams.delete("project");
    url.searchParams.delete("name");
    window.history.replaceState({}, "", url.toString());
  } catch {
    // ignore
  }
}

function tryParseJson<T>(s: string): T | null {
  try {
    return JSON.parse(s) as T;
  } catch {
    return null;
  }
}

function sanitizeMessages(arr: any): ChatMessage[] {
  if (!Array.isArray(arr)) return [];
  const out: ChatMessage[] = [];
  for (const m of arr) {
    if (!m || typeof m !== "object") continue;
    const role = m.role === "assistant" ? "assistant" : m.role === "user" ? "user" : null;
    const content = typeof m.content === "string" ? m.content : null;
    if (!role || content === null) continue;
    out.push({ role, content });
  }
  return out.slice(-200);
}

export default function BuilderPage() {
  const [device, setDevice] = useState<DeviceMode>("desktop");
  const [view, setView] = useState<ViewMode>("preview");

  const [promptDraft, setPromptDraft] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [buildMode, setBuildMode] = useState<"build" | "ask" | "plan">("build");
  const [selectedModel, setSelectedModel] = useState<string>("grok-3-mini");

  const [isThinking, setIsThinking] = useState(false);
  const [projectId, setProjectId] = useState<string>(() => safeId());
  const [activeProjectName, setActiveProjectName] = useState<string>("Untitled Project");

  const [previewUrl, setPreviewUrl] = useState<string>("");
  const [generatedFiles, setGeneratedFiles] = useState<Array<{ path: string; content: string }>>([]);
  const [lastError, setLastError] = useState<string>("");
  const [npmModalOpen, setNpmModalOpen] = useState(false);
  const [npmPackageName, setNpmPackageName] = useState("");
  const [npmInstalling, setNpmInstalling] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const receivedFilesInStreamRef = useRef(false);

  const [leftW, setLeftW] = useState<number>(() => {
    try {
      const raw = localStorage.getItem(LEFT_W_KEY);
      const n = raw ? Number(raw) : 380;
      return clamp(Number.isFinite(n) ? n : 380, MIN_LEFT, MAX_LEFT);
    } catch {
      return 380;
    }
  });

  const draggingRef = useRef(false);
  const dragStartXRef = useRef(0);
  const dragStartWRef = useRef(380);

  // Restore persisted state once
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STATE_KEY);
      if (raw) {
        const s = tryParseJson<any>(raw);
        if (s && typeof s === "object") {
          if (typeof s.projectId === "string" && s.projectId) setProjectId(s.projectId);
          if (typeof s.projectName === "string" && s.projectName) setActiveProjectName(s.projectName);

          if (s.device === "desktop" || s.device === "tablet" || s.device === "mobile") setDevice(s.device);
          if (s.view === "preview" || s.view === "code") setView(s.view);

          if (typeof s.promptDraft === "string") setPromptDraft(s.promptDraft);
          if (s.buildMode === "build" || s.buildMode === "ask" || s.buildMode === "plan") setBuildMode(s.buildMode);
          if (typeof s.selectedModel === "string" && s.selectedModel) setSelectedModel(s.selectedModel);

          const cleaned = sanitizeMessages(s.messages);
          if (cleaned.length) setMessages(cleaned);

          if (typeof s.previewUrl === "string") setPreviewUrl(s.previewUrl);

          if (Array.isArray(s.generatedFiles)) {
            const gf = s.generatedFiles
              .filter((f: any) => f && typeof f.path === "string" && typeof f.content === "string")
              .slice(0, 200);
            setGeneratedFiles(gf);
          }
        }
      }
    } catch {
      // ignore
    }

    // Override from share-link params (highest priority)
    const { project, name } = readSearchParams();
    if (project) setProjectId(project);
    if (name) setActiveProjectName(name);

    // Clean URL after consuming share params
    if (project || name) stripBuilderSearchParamsFromUrl();
  }, []);

  // Persist width + state
  useEffect(() => {
    try {
      localStorage.setItem(LEFT_W_KEY, String(leftW));
    } catch {
      // ignore
    }
  }, [leftW]);

  useEffect(() => {
    try {
      const snapshot = {
        projectId,
        projectName: activeProjectName,
        device,
        view,
        promptDraft,
        messages: messages.slice(-200),
        previewUrl,
        generatedFiles: generatedFiles.slice(0, 200),
        buildMode,
        selectedModel,
      };
      localStorage.setItem(STATE_KEY, JSON.stringify(snapshot));
    } catch {
      // ignore
    }
  }, [projectId, activeProjectName, device, view, promptDraft, messages, previewUrl, generatedFiles, buildMode, selectedModel]);

  // Resizer listeners
  useEffect(() => {
    function onMove(e: MouseEvent) {
      if (!draggingRef.current) return;
      const dx = e.clientX - dragStartXRef.current;
      const next = clamp(dragStartWRef.current + dx, MIN_LEFT, MAX_LEFT);
      setLeftW(next);
    }

    function onUp() {
      if (!draggingRef.current) return;
      draggingRef.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    }

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, []);

  function startDrag(e: React.MouseEvent) {
    draggingRef.current = true;
    dragStartXRef.current = e.clientX;
    dragStartWRef.current = leftW;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }

  function resizeBy(delta: number) {
    setLeftW((w) => clamp(w + delta, MIN_LEFT, MAX_LEFT));
  }

  function newProjectLocal() {
    try {
      abortRef.current?.abort();
    } catch {
      // ignore
    }
    abortRef.current = null;

    setProjectId(safeId());
    setActiveProjectName("Untitled Project");
    setPromptDraft("");
    setMessages([]);
    setIsThinking(false);
    setView("preview");
    setDevice("desktop");
    setPreviewUrl("");
    setGeneratedFiles([]);
    setLastError("");
  }

  async function shareProject() {
    const url = new URL(window.location.href);
    url.pathname = url.pathname.replace(/\/+$/, "");
    if (!url.pathname.endsWith("/builder")) {
      url.pathname = url.pathname.replace(/\/builder.*$/, "/builder");
    }
    url.searchParams.set("project", projectId);
    url.searchParams.set("name", activeProjectName);
    const shareUrl = url.toString();

    try {
      await navigator.clipboard.writeText(shareUrl);
    } catch {
      window.prompt("Copy this link:", shareUrl);
    }
  }

  function exportProject() {
    const payload = {
      version: 3,
      exported_at: new Date().toISOString(),
      project: { id: projectId, name: activeProjectName },
      ui_state: { view, device, leftW },
      previewUrl,
      generatedFiles,
      messages,
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });

    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);

    const safeName =
      activeProjectName
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9\-_]+/g, "-")
        .replace(/-+/g, "-")
        .replace(/(^-|-$)/g, "") || "project";

    a.download = `${safeName}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.setTimeout(() => URL.revokeObjectURL(a.href), 2500);
  }

  async function exportProjectAsZip() {
    if (generatedFiles.length === 0) {
      setLastError("No files to export. Run a build first.");
      return;
    }
    try {
      const JSZip = (await import("jszip")).default;
      const zip = new JSZip();
      for (const f of generatedFiles) {
        const path = f.path.replace(/^\/+/, "").replace(/\\/g, "/");
        zip.file(path, f.content);
      }
      const blob = await zip.generateAsync({ type: "blob" });
      const safeName =
        activeProjectName
          .trim()
          .toLowerCase()
          .replace(/[^a-z0-9\-_]+/g, "-")
          .replace(/-+/g, "-")
          .replace(/(^-|-$)/g, "") || "project";
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `${safeName}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(a.href);
    } catch (e: unknown) {
      setLastError(e instanceof Error ? e.message : "Failed to create ZIP");
    }
  }

  function upsertAssistantProgress(nextText: string) {
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.role === "assistant") {
        const copy = prev.slice();
        copy[copy.length - 1] = { role: "assistant", content: nextText };
        return copy;
      }
      return [...prev, { role: "assistant", content: nextText }];
    });
  }

  function cancelRun() {
    if (!isThinking) return;
    try {
      abortRef.current?.abort();
    } catch {
      // ignore
    }
    abortRef.current = null;
    setIsThinking(false);
    setLastError("Cancelled.");
    upsertAssistantProgress("Cancelled.");
  }

  async function runNpmInstall() {
    const pkg = npmPackageName.trim();
    if (!pkg || generatedFiles.length === 0) return;
    setNpmInstalling(true);
    setLastError("");
    try {
      const res = await fetch(`${BASE}/api/builder/npm-install`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ files: generatedFiles, package: pkg }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setLastError(data.detail || data.npm_error || "npm install failed");
        return;
      }
      const updated = (data.files || []) as Array<{ path: string; content: string }>;
      if (updated.length > 0) {
        setGeneratedFiles((prev) => {
          const byPath = new Map(prev.map((f) => [f.path, f]));
          for (const f of updated) byPath.set(f.path, f);
          return Array.from(byPath.values());
        });
        setNpmModalOpen(false);
        setNpmPackageName("");
      }
    } catch (e: unknown) {
      setLastError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setNpmInstalling(false);
    }
  }

  async function saveProjectAsNew() {
    if (generatedFiles.length === 0) {
      setLastError("No files to save. Run a build first.");
      return;
    }
    const name = window.prompt("Project name", activeProjectName)?.trim() || activeProjectName;
    if (!name) return;
    setLastError("");
    try {
      const res = await fetch(`${BASE}/api/projects/from-files`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, files: generatedFiles }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setLastError(data.detail || "Save failed");
        return;
      }
      setProjectId(data.id);
      setActiveProjectName(data.name);
      upsertAssistantProgress(`Project saved as "${data.name}".`);
    } catch (e: unknown) {
      setLastError(e instanceof Error ? e.message : "Save failed");
    }
  }

  const [openProjectModalOpen, setOpenProjectModalOpen] = useState(false);
  const [projectList, setProjectList] = useState<Array<{ id: string; name: string }>>([]);

  async function openProjectList() {
    setOpenProjectModalOpen(true);
    setLastError("");
    try {
      const res = await fetch(`${BASE}/api/projects`, { credentials: "include" });
      const list = (await res.json().catch(() => [])) as Array<{ id: string; name: string }>;
      setProjectList(Array.isArray(list) ? list : []);
    } catch {
      setProjectList([]);
    }
  }

  async function loadProject(projectIdToLoad: string) {
    setOpenProjectModalOpen(false);
    setLastError("");
    try {
      const res = await fetch(`${BASE}/api/projects/${projectIdToLoad}/export`, { credentials: "include" });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setLastError(data.detail || "Load failed");
        return;
      }
      const files = (data.files || []) as Array<{ path: string; content: string }>;
      if (files.length > 0) {
        setGeneratedFiles(files);
        setActiveProjectName(data.name || "Project");
        setProjectId(projectIdToLoad);
        upsertAssistantProgress(`Loaded "${data.name}" (${files.length} files).`);
      }
    } catch (e: unknown) {
      setLastError(e instanceof Error ? e.message : "Load failed");
    }
  }

  function implementPlan(planContent: string) {
    setBuildMode("build");
    const instruction = `Implement the following plan. Build the full project with all the files:\n\n${planContent}`;
    setPromptDraft(instruction);
    setTimeout(() => {
      const msg = instruction.trim();
      if (!msg || isThinking) return;
      setLastError("");
      setPromptDraft("");
      const userMsg: ChatMessage = { role: "user" as const, content: msg };
      const nextMsgs: ChatMessage[] = [...messages, userMsg].slice(-200);
      setMessages(nextMsgs);
      setIsThinking(true);
      const ac = new AbortController();
      abortRef.current = ac;
      const payload: RunBuildPayload = {
        projectId, projectName: activeProjectName, device, view,
        prompt: msg, messages: nextMsgs, mode: "build", model: selectedModel,
      };
      const endpoint = `${API_BASE.replace(/\/+$/, "")}/builder/run`;
      fetch(endpoint, {
        method: "POST", credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload), signal: ac.signal,
      }).then(async (res) => {
        if (!res.ok) {
          const text = await res.text().catch(() => "");
          setLastError(`Build failed (${res.status}). ${text}`);
          upsertAssistantProgress(`Build failed (${res.status}). ${text}`);
          setIsThinking(false);
          return;
        }
        const ct = res.headers.get("content-type") || "";
        if (ct.includes("text/plain") || ct.includes("text/event-stream")) {
          receivedFilesInStreamRef.current = false;
          const reader = res.body?.getReader();
          if (!reader) return;
          const decoder = new TextDecoder();
          let buffer = "", codeAcc = "", finalContent = "";
          const ipFileAcc: Array<{ path: string; content: string }> = [];
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";
            for (const line of lines) {
              if (!line.startsWith("data:")) continue;
              const jsonStr = line.slice(5).trim();
              if (!jsonStr) continue;
              let evt: any;
              try { evt = JSON.parse(jsonStr); } catch { continue; }
              const t = evt.type || "";
              if (t === "code_chunk") {
                codeAcc += (evt.data || "");
                if (!(codeAcc.trim().startsWith("{") && codeAcc.includes('"files"'))) upsertAssistantProgress(codeAcc);
              } else if (t === "file") {
                receivedFilesInStreamRef.current = true;
                if (evt.path) ipFileAcc.push({ path: String(evt.path), content: String(evt.content || "") });
                upsertAssistantProgress(`Generating files… (${ipFileAcc.length} so far)`);
              } else if (t === "files") {
                receivedFilesInStreamRef.current = true;
                const fl = evt.files || [];
                if (Array.isArray(fl)) fl.forEach((f: any) => { if (f?.path) ipFileAcc.push({ path: String(f.path), content: String(f.content || "") }); });
              } else if (t === "complete") {
                if (ipFileAcc.length > 0) {
                  setGeneratedFiles(ipFileAcc.slice(0, 200));
                  upsertAssistantProgress("Your project is ready. Check the **Preview** and **Code** tabs on the right.");
                } else {
                  finalContent = evt.content || codeAcc || "Completed.";
                  upsertAssistantProgress(finalContent.length > 500 ? "Build complete." : finalContent);
                }
              } else if (t === "error") { setLastError(evt.message || "Error"); upsertAssistantProgress(codeAcc ? `${codeAcc}\n\n${evt.message}` : evt.message); }
            }
          }
          if (ipFileAcc.length > 0 && generatedFiles.length === 0) {
            setGeneratedFiles(ipFileAcc.slice(0, 200));
            upsertAssistantProgress("Your project is ready. Check the **Preview** and **Code** tabs on the right.");
          }
          if (!finalContent && codeAcc && !receivedFilesInStreamRef.current && !(codeAcc.trim().startsWith("{") && codeAcc.includes('"files"'))) upsertAssistantProgress(codeAcc);
        }
        setIsThinking(false);
        abortRef.current = null;
      }).catch((e: any) => {
        if (e?.name !== "AbortError") { setLastError(String(e?.message || e)); upsertAssistantProgress(String(e?.message || e)); }
        setIsThinking(false);
        abortRef.current = null;
      });
    }, 50);
  }

  function isFrameworkProject(files: Array<{ path: string; content: string }>): boolean {
    const hasPackageJson = files.some(f => /package\.json$/i.test(f.path));
    const hasReactEntry = files.some(f => /src\/main\.(tsx|jsx)$/i.test(f.path) || /src\/App\.(tsx|jsx)$/i.test(f.path));
    const hasViteConfig = files.some(f => /vite\.config\./i.test(f.path));
    return !!(hasPackageJson && (hasReactEntry || hasViteConfig));
  }

  function buildPreviewBlobUrl(files: Array<{ path: string; content: string }>): string {
    // React/Vite/Node projects can't run in a blob iframe; show a clear message instead
    if (isFrameworkProject(files)) {
      const msg = `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{font-family:system-ui,sans-serif;margin:0;padding:2rem;background:#0f1419;color:#e6eef7;display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center;} .card{max-width:420px;padding:2rem;border-radius:12px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);} h1{font-size:1.25rem;margin:0 0 0.75rem;} p{font-size:0.9rem;line-height:1.5;color:rgba(230,238,247,0.8);margin:0;} .tabs{font-weight:600;color:#38bdf8;}</style></head><body><div class="card"><h1>Project generated</h1><p>This is a React/Vite or Node project. View all ${files.length} files in the <span class="tabs">Code</span> tab. Deploy to Netlify or Vercel to run it live.</p></div></body></html>`;
      const blob = new Blob([msg], { type: "text/html" });
      return URL.createObjectURL(blob);
    }

    const htmlFile = files.find(f => /index\.html?$/i.test(f.path));
    const cssFiles = files.filter(f => /\.css$/i.test(f.path));
    const jsFiles = files.filter(f => /\.(js|jsx)$/i.test(f.path) && !/node_modules|package|config/.test(f.path));

    if (htmlFile) {
      let html = htmlFile.content;

      // Remove link tags that reference local CSS files and inject inline styles (match full path or basename)
      for (const css of cssFiles) {
        const escapedPath = css.path.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const basename = css.path.split("/").pop() || css.path;
        const escapedBasename = basename.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const linkPattern = new RegExp(`<link[^>]*href=["'](?:\\.?\\/)?(?:${escapedPath}|${escapedBasename})["'][^>]*\\/?>`, "gi");
        html = html.replace(linkPattern, "");
        html = html.replace("</head>", `<style>\n${css.content}\n</style>\n</head>`);
      }

      // Remove script tags that reference local JS files and inject inline scripts (match full path or basename)
      for (const js of jsFiles) {
        const escapedPath = js.path.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const basename = js.path.split("/").pop() || js.path;
        const escapedBasename = basename.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const scriptPattern = new RegExp(`<script[^>]*src=["'](?:\\.?\\/)?(?:${escapedPath}|${escapedBasename})["'][^>]*>\\s*<\\/script>`, "gi");
        html = html.replace(scriptPattern, "");
        html = html.replace("</body>", `<script>\n${js.content}\n</script>\n</body>`);
      }

      const blob = new Blob([html], { type: "text/html" });
      return URL.createObjectURL(blob);
    }

    let assembledHtml = "<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>";
    for (const css of cssFiles) {
      assembledHtml += `<style>\n${css.content}\n</style>`;
    }
    assembledHtml += "</head><body>";
    const bodySnippets = files.filter(f => /\.(html?)$/i.test(f.path) && !/index/i.test(f.path));
    for (const s of bodySnippets) {
      assembledHtml += s.content;
    }
    if (bodySnippets.length === 0) {
      assembledHtml += `<div style="font-family:system-ui;padding:40px;color:#333"><h1>Project Generated</h1><p>${files.length} files created. Switch to the Code tab to view them.</p></div>`;
    }
    for (const js of jsFiles) {
      assembledHtml += `<script>\n${js.content}\n</script>`;
    }
    assembledHtml += "</body></html>";
    const blob = new Blob([assembledHtml], { type: "text/html" });
    return URL.createObjectURL(blob);
  }

  useEffect(() => {
    if (generatedFiles.length > 0) {
      try {
        const url = buildPreviewBlobUrl(generatedFiles);
        setPreviewUrl(url);
        return () => { try { URL.revokeObjectURL(url); } catch {} };
      } catch {
        setPreviewUrl("");
      }
    } else {
      setPreviewUrl("");
    }
  }, [generatedFiles]);

  async function runBuild() {
    const msg = promptDraft.trim();
    if (!msg || isThinking) return;

    setLastError("");
    setPromptDraft("");

    const userMsg: ChatMessage = { role: "user" as const, content: msg };
    const nextMsgs: ChatMessage[] = [...messages, userMsg].slice(-200);

    setMessages(nextMsgs);
    setIsThinking(true);
    receivedFilesInStreamRef.current = false;

    // Don't pre-fill assistant slot — the "CodeBot is working..." indicator handles it

    const ac = new AbortController();
    abortRef.current = ac;

    const payload: RunBuildPayload = {
      projectId,
      projectName: activeProjectName,
      device,
      view,
      prompt: msg,
      messages: nextMsgs,
      mode: buildMode,
      model: selectedModel,
    };

    const endpoint = `${API_BASE.replace(/\/+$/, "")}/builder/run`;

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
        signal: ac.signal,
      });

      if (!res.ok) {
        const text = await res.text().catch(() => "");
        const detail = text?.trim() ? ` ${text.trim()}` : "";
        const err = `Build request failed (${res.status}).${detail}`;
        setLastError(err);
        upsertAssistantProgress(err);
        setIsThinking(false);
        abortRef.current = null;
        return;
      }

      const ct = res.headers.get("content-type") || "";

      // Streaming SSE
      if (ct.includes("text/plain") || ct.includes("text/event-stream")) {
        const reader = res.body?.getReader();
        if (!reader) {
          const err = "Backend returned streaming response but no body reader was available.";
          setLastError(err);
          upsertAssistantProgress(err);
          setIsThinking(false);
          abortRef.current = null;
          return;
        }

        const decoder = new TextDecoder();
        let buffer = "";
        let codeAcc = "";
        let finalContent = "";
        const fileAcc: Array<{ path: string; content: string }> = [];

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data:")) continue;
            const jsonStr = line.slice(5).trim();
            if (!jsonStr) continue;

            let evt: any;
            try { evt = JSON.parse(jsonStr); } catch { continue; }

            const t = evt.type || "";

            if (t === "status" || t === "layer_start" || t === "layer_complete") {
              // Pipeline progress — handled by the "CodeBot is working..." indicator
            } else if (t === "code_chunk") {
              codeAcc += (evt.data || "");
              const looksLikeProjectJson = codeAcc.trim().startsWith("{") && codeAcc.includes('"files"');
              if (!looksLikeProjectJson) upsertAssistantProgress(codeAcc);
            } else if (t === "file") {
              receivedFilesInStreamRef.current = true;
              if (evt.path) fileAcc.push({ path: String(evt.path), content: String(evt.content || "") });
              upsertAssistantProgress(`Generating files… (${fileAcc.length} so far)`);
            } else if (t === "files") {
              receivedFilesInStreamRef.current = true;
              const filesList = evt.files || [];
              if (Array.isArray(filesList)) filesList.forEach((f: any) => { if (f?.path) fileAcc.push({ path: String(f.path), content: String(f.content || "") }); });
              upsertAssistantProgress("Your project is ready. Check the **Preview** and **Code** tabs on the right.");
            } else if (t === "complete") {
              if (fileAcc.length > 0) {
                setGeneratedFiles(fileAcc.slice(0, 200));
                upsertAssistantProgress("Your project is ready. Check the **Preview** and **Code** tabs on the right.");
              } else {
                finalContent = evt.content || codeAcc || "Completed.";
                upsertAssistantProgress(finalContent.length > 500 ? "Build complete." : finalContent);
              }
            } else if (t === "error") {
              const errMsg = evt.message || "Unknown pipeline error";
              setLastError(errMsg);
              upsertAssistantProgress(codeAcc ? `${codeAcc}\n\n❌ ${errMsg}` : `❌ ${errMsg}`);
            }
          }
        }

        // Flush accumulated files even if no 'complete' event arrived
        if (fileAcc.length > 0 && generatedFiles.length === 0) {
          setGeneratedFiles(fileAcc.slice(0, 200));
          upsertAssistantProgress("Your project is ready. Check the **Preview** and **Code** tabs on the right.");
        }

        if (!finalContent && codeAcc && !receivedFilesInStreamRef.current) {
          const looksLikeJson = codeAcc.trim().startsWith("{") && codeAcc.includes('"files"');
          if (!looksLikeJson) upsertAssistantProgress(codeAcc);
        }

        // Fallback: if we never got a "files" event but accumulated content looks like project JSON, extract files so Code/Preview tabs show output
        if (!receivedFilesInStreamRef.current && codeAcc.trim().startsWith("{") && codeAcc.includes('"files"')) {
          try {
            const parsed = JSON.parse(codeAcc.trim());
            const list = parsed?.files;
            if (Array.isArray(list) && list.length > 0) {
              const normalized = list
                .slice(0, 200)
                .filter((f: any) => f && typeof f.path === "string")
                .map((f: any) => ({ path: String(f.path).replace(/^\/+/, ""), content: typeof f.content === "string" ? f.content : "" }));
              if (normalized.length) setGeneratedFiles(normalized);
              upsertAssistantProgress("Your project is ready. Check the **Preview** and **Code** tabs on the right.");
            }
          } catch {
            try {
              const filesMatch = codeAcc.match(/"files"\s*:\s*\[/);
              if (filesMatch) {
                const start = codeAcc.indexOf("[", filesMatch.index);
                let depth = 0;
                let end = start;
                for (let i = start; i < codeAcc.length; i++) {
                  if (codeAcc[i] === "[") depth++;
                  else if (codeAcc[i] === "]") { depth--; if (depth === 0) { end = i; break; } }
                }
                const arr = JSON.parse(codeAcc.slice(start, end + 1));
                if (Array.isArray(arr)) {
                  const normalized = arr.slice(0, 200).filter((f: any) => f && typeof f.path === "string").map((f: any) => ({ path: String(f.path).replace(/^\/+/, ""), content: typeof f.content === "string" ? f.content : "" }));
                  if (normalized.length) setGeneratedFiles(normalized);
                  upsertAssistantProgress("Your project is ready. Check the **Preview** and **Code** tabs on the right.");
                }
              }
            } catch {
              // Malformed JSON (e.g. unescaped quotes in content); avoid showing raw parser error
              setLastError("Output was partially malformed. Backend recovered what it could; try another build if preview is incomplete.");
            }
          }
        }

        setIsThinking(false);
        abortRef.current = null;
        return;
      }

      // JSON response
      if (ct.includes("application/json")) {
        const data = (await res.json().catch(() => null)) as RunBuildJsonResponse | null;

        if (!data) {
          const err = "Backend returned JSON but parsing failed.";
          setLastError(err);
          upsertAssistantProgress(err);
          setIsThinking(false);
          abortRef.current = null;
          return;
        }

        if (data.error) {
          setLastError(data.error);
          upsertAssistantProgress(data.error);
        } else {
          if (typeof data.assistant === "string" && data.assistant.trim()) {
            upsertAssistantProgress(data.assistant.trim());
          } else {
            upsertAssistantProgress("Completed.");
          }

          if (typeof data.previewUrl === "string") setPreviewUrl(data.previewUrl);
          if (Array.isArray(data.files)) setGeneratedFiles(data.files.slice(0, 200));
        }

        setIsThinking(false);
        abortRef.current = null;
        return;
      }

      // Unknown content-type
      const fallback = await res.text().catch(() => "");
      const out = fallback?.trim() || "Completed.";
      upsertAssistantProgress(out);
      setIsThinking(false);
      abortRef.current = null;
    } catch (e: any) {
      const aborted = e?.name === "AbortError";
      const err = aborted ? "Cancelled." : `Build request errored: ${String(e?.message || e)}`;
      setLastError(err);
      upsertAssistantProgress(err);
      setIsThinking(false);
      abortRef.current = null;
    }
  }

  const deviceShell = useMemo(() => {
    if (device === "mobile") return { width: 390, height: 844 };
    if (device === "tablet") return { width: 820, height: 1060 };
    return null;
  }, [device]);

  return (
    <AuthGate redirectTo="/login" allowCookieSessionFallback={true}>
      <ErrorBoundary>
      <style dangerouslySetInnerHTML={{ __html: builderKeyframes }} />
      <div style={{ minHeight: "100vh", background: "var(--cb-bg, #0b0f14)", color: "white" }}>
        <BuilderTopBar
          projectName={activeProjectName}
          onProjectRename={(name) => setActiveProjectName(name)}
          onNewProject={newProjectLocal}
          onShareProject={shareProject}
          onExportProject={exportProject}
          onExportProjectAsZip={exportProjectAsZip}
          onSaveProject={saveProjectAsNew}
          onOpenProject={openProjectList}
          onDeploy={async (target, customDomain) => {
            if (generatedFiles.length === 0) {
              alert("No files to deploy. Run a build first.");
              return;
            }
            const msg = target === "vm"
              ? "Deploying to NYPTID Server..."
              : "Deploying to Netlify...";
            setLastError("");
            upsertAssistantProgress(msg);
            try {
              const res = await fetch(`${BASE}/api/deploy`, {
                method: "POST",
                credentials: "include",
                headers: { "content-type": "application/json" },
                body: JSON.stringify({
                  target: target === "vm" ? "server" : target,
                  projectId,
                  projectName: activeProjectName,
                  files: generatedFiles,
                  customDomain: customDomain || "",
                }),
              });
              const data = await res.json();
              if (data.error) {
                setLastError(data.error);
                upsertAssistantProgress(`Deploy failed: ${data.error}`);
              } else if (data.url) {
                upsertAssistantProgress(`Deployed successfully! ${data.url}`);
                window.open(data.url, "_blank");
              }
            } catch (e: any) {
              setLastError(String(e?.message || e));
              upsertAssistantProgress(`Deploy error: ${e?.message || e}`);
            }
          }}
          view={view}
          onViewChange={setView}
          device={device}
          onDeviceChange={setDevice}
        />

        <div
          style={{
            display: "grid",
            gridTemplateColumns: `${leftW}px 10px minmax(0, 1fr)`,
            height: "calc(100vh - 56px)",
            minHeight: 0,
            minWidth: 0,
          }}
        >
          {/* Sidebar */}
          <aside style={{ height: "100%", minHeight: 0, overflow: "hidden", background: "linear-gradient(180deg, rgba(12,16,22,0.7), rgba(10,13,18,0.7))" }}>
            <BuilderSidebar
              isThinking={isThinking}
              messages={messages}
              promptDraft={promptDraft}
              onPromptDraftChange={setPromptDraft}
              onRunBuild={runBuild}
              onCancel={cancelRun}
              mode={buildMode}
              onModeChange={setBuildMode}
              selectedModel={selectedModel}
              onModelChange={setSelectedModel}
              onImplementPlan={implementPlan}
            />
          </aside>

          {/* Resizer */}
          <div
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize panels"
            tabIndex={0}
            onMouseDown={startDrag}
            onKeyDown={(e) => {
              if (e.key === "ArrowLeft") resizeBy(-12);
              if (e.key === "ArrowRight") resizeBy(12);
            }}
            title="Drag to resize"
            style={{ height: "100%", cursor: "col-resize", position: "relative", userSelect: "none" }}
          >
            <div style={{ position: "absolute", inset: 0, margin: "auto", width: 3, height: 48, borderRadius: 999, background: "rgba(255,255,255,0.08)" }} />
          </div>

          {/* Main preview area */}
          <main style={{ minWidth: 0, overflow: "hidden", padding: 12, height: "100%", minHeight: 0 }}>
            <div
              style={{
                height: "100%",
                display: "grid",
                gridTemplateRows: "auto 1fr auto",
                borderRadius: 14,
                background: "rgba(255,255,255,0.02)",
                boxShadow: "0 4px 24px -4px rgba(0,0,0,0.3)",
                overflow: "hidden",
              }}
            >
              {/* Stage header */}
              <div
                style={{
                  padding: "12px 16px",
                  borderBottom: "1px solid rgba(255,255,255,0.04)",
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                }}
              >
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: "white" }}>{view === "preview" ? "Preview" : "Code"}</div>
                  <div style={{ fontSize: 12, color: "rgba(255,255,255,0.45)", marginTop: 2 }}>
                    {isThinking ? "Building your project..." : view === "preview" ? "Live preview" : "Generated files"}
                  </div>
                </div>
                {isThinking ? (
                  <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ width: 6, height: 6, borderRadius: "50%", background: "rgba(34,197,94,0.8)", animation: "cb-think-pulse 1s ease-in-out infinite" }} />
                    <span style={{ fontSize: 12, color: "rgba(34,197,94,0.8)" }}>Working</span>
                    <button
                      type="button"
                      onClick={cancelRun}
                      style={{ height: 28, padding: "0 10px", borderRadius: 6, border: "none", background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.7)", fontSize: 12, fontWeight: 500, cursor: "pointer" }}
                    >
                      Cancel
                    </button>
                  </div>
                ) : null}
              </div>

              {/* Stage body */}
              <div style={{ overflow: "hidden", minHeight: 0, display: "grid", placeItems: "center", padding: 14 }}>
                {view === "preview" ? (
                  deviceShell ? (
                    <div
                      style={{
                        width: deviceShell.width,
                        height: deviceShell.height,
                        maxWidth: "100%",
                        maxHeight: "100%",
                        borderRadius: 14,
                        background: "rgba(0,0,0,0.15)",
                        overflow: "hidden",
                        display: "grid",
                        placeItems: "center",
                      }}
                    >
                      {previewUrl ? (
                        <iframe title="Preview" src={previewUrl} style={{ width: "100%", height: "100%", border: 0 }} sandbox="allow-scripts allow-same-origin allow-forms allow-modals" />
                      ) : (
                        <EmptyPreview error={lastError} />
                      )}
                    </div>
                  ) : (
                    <div style={{ width: "100%", height: "100%", minHeight: 0, display: "grid", placeItems: "center" }}>
                      {previewUrl ? (
                        <iframe title="Preview" src={previewUrl} style={{ width: "100%", height: "100%", border: 0 }} sandbox="allow-scripts allow-same-origin allow-forms allow-modals" />
                      ) : (
                        <EmptyPreview error={lastError} />
                      )}
                    </div>
                  )
                ) : (
                  <div style={{ width: "100%", height: "100%", minHeight: 400, display: "flex", flexDirection: "column", overflow: "hidden" }}>
                    <CodeEditorPanel
                      files={generatedFiles}
                      onFilesChange={setGeneratedFiles}
                      onAddPackage={() => setNpmModalOpen(true)}
                    />
                    {lastError ? <div style={{ padding: 8, fontSize: 12, color: "#ff4d4d" }}>{lastError}</div> : null}
                  </div>
                )}
              </div>

              {/* Footer */}
              <div
                style={{
                  padding: "10px 16px",
                  borderTop: "1px solid rgba(255,255,255,0.04)",
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  fontSize: 12,
                }}
              >
                <span style={{ padding: "2px 8px", borderRadius: 6, background: "rgba(255,255,255,0.06)", fontWeight: 600, fontSize: 11, color: "rgba(255,255,255,0.7)" }}>
                  Project
                </span>
                <span style={{ color: "rgba(255,255,255,0.6)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {activeProjectName} • {projectId.slice(0, 8)}
                </span>
                <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
                  <button type="button" onClick={() => resizeBy(-20)} title="Narrow sidebar" style={{ width: 28, height: 28, borderRadius: 6, border: "none", background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.6)", fontSize: 12, cursor: "pointer" }}>◀</button>
                  <button type="button" onClick={() => resizeBy(20)} title="Widen sidebar" style={{ width: 28, height: 28, borderRadius: 6, border: "none", background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.6)", fontSize: 12, cursor: "pointer" }}>▶</button>
                </div>
              </div>
            </div>
          </main>
        </div>

        {/* NPM install modal */}
        {npmModalOpen && (
          <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }} onClick={() => !npmInstalling && setNpmModalOpen(false)}>
            <div style={{ background: "var(--cb-bg, #0b0f14)", borderRadius: 14, padding: 24, minWidth: 320, border: "1px solid rgba(255,255,255,0.1)" }} onClick={(e) => e.stopPropagation()}>
              <div style={{ fontSize: 16, fontWeight: 600, color: "white", marginBottom: 12 }}>Add npm package</div>
              <input
                type="text"
                value={npmPackageName}
                onChange={(e) => setNpmPackageName(e.target.value)}
                placeholder="e.g. lodash or react@18"
                style={{ width: "100%", padding: "10px 12px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.15)", background: "rgba(255,255,255,0.06)", color: "white", fontSize: 14, marginBottom: 16 }}
                onKeyDown={(e) => e.key === "Enter" && runNpmInstall()}
              />
              <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                <button type="button" onClick={() => !npmInstalling && setNpmModalOpen(false)} style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.2)", background: "transparent", color: "rgba(255,255,255,0.8)", cursor: "pointer" }}>Cancel</button>
                <button type="button" onClick={runNpmInstall} disabled={npmInstalling || !npmPackageName.trim()} style={{ padding: "8px 16px", borderRadius: 8, border: "none", background: "rgba(34,197,94,0.2)", color: "#86efac", fontWeight: 600, cursor: npmInstalling ? "wait" : "pointer" }}>{npmInstalling ? "Installing…" : "Install"}</button>
              </div>
            </div>
          </div>
        )}

        {/* Open project modal */}
        {openProjectModalOpen && (
          <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }} onClick={() => setOpenProjectModalOpen(false)}>
            <div style={{ background: "var(--cb-bg, #0b0f14)", borderRadius: 14, padding: 24, minWidth: 360, maxHeight: "80vh", overflow: "auto", border: "1px solid rgba(255,255,255,0.1)" }} onClick={(e) => e.stopPropagation()}>
              <div style={{ fontSize: 16, fontWeight: 600, color: "white", marginBottom: 12 }}>Open project</div>
              {projectList.length === 0 ? (
                <div style={{ color: "rgba(255,255,255,0.5)", fontSize: 13 }}>No saved projects. Save a project from the Project menu first.</div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {projectList.map((p) => (
                    <button key={p.id} type="button" onClick={() => loadProject(p.id)} style={{ padding: "12px 14px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.03)", color: "white", fontSize: 13, textAlign: "left", cursor: "pointer" }}>{p.name}</button>
                  ))}
                </div>
              )}
              <button type="button" onClick={() => setOpenProjectModalOpen(false)} style={{ marginTop: 16, padding: "8px 16px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.2)", background: "transparent", color: "rgba(255,255,255,0.8)", cursor: "pointer" }}>Close</button>
            </div>
          </div>
        )}
      </div>
      </ErrorBoundary>
    </AuthGate>
  );
}
