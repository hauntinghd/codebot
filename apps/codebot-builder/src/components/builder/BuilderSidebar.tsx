"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

type Message = { role: "user" | "assistant"; content: string };
type BuildMode = "build" | "ask" | "plan";

const BASE = "/codebot";

type ModelEntry = { id: string; label: string; tier: "free" | "pro"; group: string; disabled?: boolean };

const MODELS: ModelEntry[] = [
  { id: "grok-3-mini",       label: "Grok 3 Mini",       tier: "free", group: "xAI — Free" },
  { id: "grok-3",            label: "Grok 3",             tier: "free", group: "xAI — Free" },
  { id: "grok-4-1-fast-reasoning",     label: "Grok 4.1 Fast Reasoning",     tier: "pro", group: "xAI Grok" },
  { id: "grok-4-1-fast-non-reasoning", label: "Grok 4.1 Fast Non-Reasoning", tier: "pro", group: "xAI Grok" },
  { id: "grok-code-fast-1",            label: "Grok Code Fast 1",            tier: "pro", group: "xAI Grok" },
  { id: "grok-4-fast-reasoning",       label: "Grok 4 Fast Reasoning",       tier: "pro", group: "xAI Grok" },
  { id: "grok-4-fast-non-reasoning",   label: "Grok 4 Fast Non-Reasoning",   tier: "pro", group: "xAI Grok" },
  { id: "claude-opus-4-6",             label: "Claude Opus 4.6",             tier: "pro", group: "Claude — Coming Soon", disabled: true },
  { id: "claude-sonnet-4-6",           label: "Claude Sonnet 4.6",           tier: "pro", group: "Claude — Coming Soon", disabled: true },
  { id: "claude-haiku-4-5",            label: "Claude Haiku 4.5",            tier: "pro", group: "Claude — Coming Soon", disabled: true },
  { id: "gpt-5.3-codex",              label: "GPT-5.3 Codex",               tier: "pro", group: "OpenAI — Coming Soon", disabled: true },
  { id: "gpt-5.2",                    label: "GPT-5.2",                     tier: "pro", group: "OpenAI — Coming Soon", disabled: true },
];

const MODE_META: Record<BuildMode, { label: string; desc: string; icon: string }> = {
  build: { label: "Build", desc: "Generate and run code", icon: "⚡" },
  ask: { label: "Ask", desc: "Ask questions about code", icon: "💬" },
  plan: { label: "Plan", desc: "Plan before building", icon: "📋" },
};

const TEMPLATES: { name: string; prompt: string }[] = [
  { name: "Landing page", prompt: "Build a modern single-page landing for a SaaS product. Include hero, features, pricing, testimonials, and CTA. Use clean typography and a professional color scheme." },
  { name: "E-commerce store", prompt: "Build a multi-page e-commerce website with home, products, product detail, cart, and contact. Include navigation, product grid, add to cart, and responsive layout." },
  { name: "Portfolio", prompt: "Build a personal portfolio site with hero, about, projects gallery, skills, and contact form. Minimal and professional design." },
  { name: "Blog / content", prompt: "Build a blog-style site with a homepage listing posts, article layout, and clean reading experience. Include header, footer, and navigation." },
  { name: "Luxury brand", prompt: "Build a high-end luxury brand landing (e.g. fashion or watches). Gray/silver theme, large imagery, minimal copy, premium feel. Include hero, collection strip, and footer." },
];

const thinkingKeyframes = `
@keyframes cb-think-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}`;

function renderMarkdownLite(text: string): React.ReactNode[] {
  const lines = text.split("\n");
  const nodes: React.ReactNode[] = [];
  let key = 0;

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith("### ")) {
      nodes.push(<div key={key++} style={{ fontSize: 13, fontWeight: 700, color: "rgba(56,189,248,0.95)", marginTop: 10, marginBottom: 2 }}>{trimmed.slice(4)}</div>);
    } else if (trimmed.startsWith("## ")) {
      nodes.push(<div key={key++} style={{ fontSize: 14, fontWeight: 700, color: "rgba(255,255,255,0.95)", marginTop: 12, marginBottom: 4 }}>{trimmed.slice(3)}</div>);
    } else if (trimmed.startsWith("# ")) {
      nodes.push(<div key={key++} style={{ fontSize: 15, fontWeight: 700, color: "rgba(255,255,255,0.95)", marginTop: 14, marginBottom: 4 }}>{trimmed.slice(2)}</div>);
    } else if (/^\d+\.\s/.test(trimmed)) {
      const match = trimmed.match(/^(\d+\.)\s(.*)$/);
      if (match) {
        nodes.push(
          <div key={key++} style={{ display: "flex", gap: 6, marginTop: 3, fontSize: 12.5, lineHeight: 1.5 }}>
            <span style={{ color: "rgba(56,189,248,0.7)", fontWeight: 700, minWidth: 18, flexShrink: 0 }}>{match[1]}</span>
            <span style={{ color: "rgba(230,238,247,0.8)" }}>{formatInline(match[2])}</span>
          </div>
        );
      }
    } else if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      nodes.push(
        <div key={key++} style={{ display: "flex", gap: 6, marginTop: 2, fontSize: 12.5, lineHeight: 1.5, paddingLeft: 4 }}>
          <span style={{ color: "rgba(34,197,94,0.7)", fontWeight: 700, flexShrink: 0 }}>•</span>
          <span style={{ color: "rgba(230,238,247,0.8)" }}>{formatInline(trimmed.slice(2))}</span>
        </div>
      );
    } else if (trimmed.startsWith("**") && trimmed.endsWith("**")) {
      nodes.push(<div key={key++} style={{ fontWeight: 700, color: "rgba(255,255,255,0.9)", marginTop: 8, fontSize: 13 }}>{trimmed.slice(2, -2)}</div>);
    } else if (trimmed === "") {
      nodes.push(<div key={key++} style={{ height: 6 }} />);
    } else {
      nodes.push(<div key={key++} style={{ fontSize: 12.5, lineHeight: 1.55, color: "rgba(230,238,247,0.8)", marginTop: 1 }}>{formatInline(trimmed)}</div>);
    }
  }
  return nodes;
}

function formatInline(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i} style={{ color: "rgba(255,255,255,0.95)", fontWeight: 600 }}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={i} style={{ background: "rgba(255,255,255,0.06)", padding: "1px 5px", borderRadius: 4, fontSize: "0.92em", color: "rgba(168,85,247,0.9)" }}>{part.slice(1, -1)}</code>;
    }
    return part;
  });
}

function isPlanMessage(content: string): boolean {
  const lower = content.toLowerCase();
  return (
    (lower.includes("**approach") || lower.includes("## approach") || lower.includes("### approach")) &&
    (lower.includes("**steps") || lower.includes("## steps") || lower.includes("### steps") || lower.includes("**files") || lower.includes("## files"))
  );
}

export default function BuilderSidebar(props: {
  isThinking: boolean;
  messages: Message[];
  promptDraft: string;
  onPromptDraftChange: (v: string) => void;
  onRunBuild: () => void;
  onCancel?: () => void;
  mode?: BuildMode;
  onModeChange?: (m: BuildMode) => void;
  selectedModel?: string;
  onModelChange?: (m: string) => void;
  onImplementPlan?: (planContent: string) => void;
}) {
  const {
    isThinking, messages, promptDraft, onPromptDraftChange, onRunBuild, onCancel,
    mode = "build", onModeChange, selectedModel = "grok-3-mini", onModelChange,
    onImplementPlan,
  } = props;

  const listRef = useRef<HTMLDivElement | null>(null);
  const modeRef = useRef<HTMLDivElement | null>(null);
  const modelRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const toolbarRef = useRef<HTMLDivElement | null>(null);
  const canRun = useMemo(() => promptDraft.trim().length > 0 && !isThinking, [promptDraft, isThinking]);

  const [modeOpen, setModeOpen] = useState(false);
  const [modelOpen, setModelOpen] = useState(false);
  const [toolbarOpen, setToolbarOpen] = useState(false);
  const [attachedFile, setAttachedFile] = useState<{ name: string; content: string } | null>(null);
  const [enhancing, setEnhancing] = useState(false);

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages, isThinking]);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (modeRef.current && !modeRef.current.contains(e.target as Node)) setModeOpen(false);
      if (modelRef.current && !modelRef.current.contains(e.target as Node)) setModelOpen(false);
      if (toolbarRef.current && !toolbarRef.current.contains(e.target as Node)) setToolbarOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const meta = MODE_META[mode];
  const currentModel = MODELS.find((m) => m.id === selectedModel) ?? MODELS[0];

  const modelGroups = useMemo(() => {
    const groups: { name: string; models: ModelEntry[] }[] = [];
    const seen = new Set<string>();
    for (const m of MODELS) {
      if (!seen.has(m.group)) { seen.add(m.group); groups.push({ name: m.group, models: [] }); }
      groups.find((g) => g.name === m.group)!.models.push(m);
    }
    return groups;
  }, []);

  const actionLabel = mode === "build" ? "Build now" : mode === "ask" ? "Ask" : "Plan";
  const placeholder = mode === "build"
    ? "Describe what you want to build..."
    : mode === "ask"
    ? "Ask a question about your code..."
    : "Describe what you want to plan...";

  const handleFileAttach = useCallback(() => {
    fileInputRef.current?.click();
    setToolbarOpen(false);
  }, []);

  const handleFileSelected = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      setAttachedFile({ name: file.name, content: reader.result as string });
    };
    if (file.size > 500_000) {
      setAttachedFile({ name: file.name, content: `[File too large: ${file.name} (${(file.size / 1024).toFixed(0)}KB)]` });
      return;
    }
    reader.readAsText(file);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, []);

  const handleEnhancePrompt = useCallback(async () => {
    const raw = promptDraft.trim();
    if (!raw || enhancing) return;
    setEnhancing(true);
    setToolbarOpen(false);
    try {
      const res = await fetch(`${BASE}/api/builder/run`, {
        method: "POST",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          prompt: `Enhance this prompt to be more detailed and specific for an AI code builder. Return ONLY the enhanced prompt text, nothing else. Original: "${raw}"`,
          mode: "ask",
          model: selectedModel,
          messages: [],
          projectId: "enhance",
          projectName: "enhance",
        }),
      });
      if (!res.ok) { setEnhancing(false); return; }
      const reader = res.body?.getReader();
      if (!reader) { setEnhancing(false); return; }
      const decoder = new TextDecoder();
      let buf = "";
      let result = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() || "";
        for (const line of lines) {
          if (!line.startsWith("data:")) continue;
          const j = line.slice(5).trim();
          if (!j) continue;
          try {
            const evt = JSON.parse(j);
            if (evt.type === "code_chunk") result += (evt.data || "");
            if (evt.type === "complete" && evt.content) result = evt.content;
          } catch { /* skip */ }
        }
      }
      if (result.trim()) onPromptDraftChange(result.trim());
    } catch { /* silent */ }
    setEnhancing(false);
  }, [promptDraft, enhancing, selectedModel, onPromptDraftChange]);

  const btnStyle = (disabled = false): React.CSSProperties => ({
    display: "flex", alignItems: "center", gap: 8, width: "100%",
    padding: "9px 12px", border: "none",
    background: "transparent", color: disabled ? "rgba(255,255,255,0.25)" : "rgba(255,255,255,0.85)",
    fontSize: 12.5, cursor: disabled ? "default" : "pointer",
    textAlign: "left" as const, fontFamily: "inherit",
  });

  const comingSoonBadge: React.CSSProperties = {
    fontSize: 9, fontWeight: 700, padding: "1px 5px", borderRadius: 4,
    background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.3)",
    marginLeft: "auto", flexShrink: 0, letterSpacing: "0.03em",
  };

  return (
    <div style={{ height: "100%", padding: 12 }}>
      <style dangerouslySetInnerHTML={{ __html: thinkingKeyframes }} />
      <input type="file" ref={fileInputRef} onChange={handleFileSelected} style={{ display: "none" }} accept=".txt,.ts,.tsx,.js,.jsx,.json,.css,.html,.py,.md,.csv,.yaml,.yml,.xml,.svg,.sql,.env,.sh,.toml" />
      <div style={{ height: "100%", display: "flex", flexDirection: "column", borderRadius: 14, background: "rgba(255,255,255,0.02)", boxShadow: "0 4px 24px -4px rgba(0,0,0,0.3)", overflow: "hidden" }}>

        {/* Header with mode + model */}
        <div style={{ padding: "14px 14px 12px", borderBottom: "1px solid rgba(255,255,255,0.04)", display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: "white" }}>Chat</div>
            <div style={{ fontSize: 11, fontWeight: 500, color: isThinking ? "rgba(34,197,94,0.9)" : "rgba(255,255,255,0.4)", animation: isThinking ? "cb-think-pulse 1.5s ease-in-out infinite" : "none" }}>
              {isThinking ? "Working..." : "Ready"}
            </div>
          </div>

          {/* Mode + Model row */}
          <div style={{ display: "flex", gap: 6 }}>
            {/* Mode dropdown */}
            <div style={{ position: "relative", flex: "1 1 0" }} ref={modeRef}>
              <button type="button" onClick={() => { setModeOpen((s) => !s); setModelOpen(false); }} style={{ width: "100%", height: 34, borderRadius: 8, border: "none", background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.85)", fontSize: 12, fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 10px", fontFamily: "inherit" }}>
                <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                  <span style={{ fontSize: 13 }}>{meta.icon}</span> {meta.label}
                </span>
                <span style={{ fontSize: 9, opacity: 0.5 }}>▾</span>
              </button>
              {modeOpen && (
                <div style={{ position: "absolute", top: 38, left: 0, right: 0, borderRadius: 10, background: "rgba(16,20,28,0.98)", border: "1px solid rgba(255,255,255,0.08)", boxShadow: "0 12px 40px rgba(0,0,0,0.5)", zIndex: 50, overflow: "hidden" }}>
                  {(["build", "ask", "plan"] as BuildMode[]).map((m) => {
                    const mm = MODE_META[m];
                    const active = m === mode;
                    return (
                      <button key={m} type="button" onClick={() => { onModeChange?.(m); setModeOpen(false); }} style={{ width: "100%", display: "flex", alignItems: "center", gap: 8, padding: "10px 12px", border: "none", background: active ? "rgba(255,255,255,0.06)" : "transparent", color: "rgba(255,255,255,0.85)", fontSize: 12, cursor: "pointer", textAlign: "left", fontFamily: "inherit" }}>
                        <span style={{ fontSize: 14, width: 20, textAlign: "center" }}>{mm.icon}</span>
                        <div>
                          <div style={{ fontWeight: 600 }}>{mm.label}</div>
                          <div style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", marginTop: 1 }}>{mm.desc}</div>
                        </div>
                        {active && <span style={{ marginLeft: "auto", fontSize: 11, color: "rgba(34,197,94,0.8)" }}>✓</span>}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Model dropdown */}
            <div style={{ position: "relative", flex: "1 1 0" }} ref={modelRef}>
              <button type="button" onClick={() => { setModelOpen((s) => !s); setModeOpen(false); }} style={{ width: "100%", height: 34, borderRadius: 8, border: "none", background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.85)", fontSize: 12, fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 10px", fontFamily: "inherit" }}>
                <span style={{ display: "flex", alignItems: "center", gap: 5, overflow: "hidden" }}>
                  <span style={{ fontSize: 10, padding: "1px 5px", borderRadius: 4, background: currentModel.tier === "free" ? "rgba(34,197,94,0.15)" : "rgba(168,85,247,0.15)", color: currentModel.tier === "free" ? "rgba(134,239,172,1)" : "rgba(216,180,254,1)", fontWeight: 700, flexShrink: 0 }}>
                    {currentModel.tier === "free" ? "FREE" : "PRO"}
                  </span>
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{currentModel.label}</span>
                </span>
                <span style={{ fontSize: 9, opacity: 0.5, flexShrink: 0 }}>▾</span>
              </button>
              {modelOpen && (
                <div style={{ position: "absolute", top: 38, left: 0, width: "max-content", minWidth: "100%", maxWidth: 280, maxHeight: 420, overflowY: "auto", borderRadius: 10, background: "rgba(16,20,28,0.98)", border: "1px solid rgba(255,255,255,0.08)", boxShadow: "0 12px 40px rgba(0,0,0,0.5)", zIndex: 50 }}>
                  {modelGroups.map((g, gi) => (
                    <div key={g.name}>
                      <div style={{ padding: "8px 12px 4px", fontSize: 10, fontWeight: 700, color: "rgba(255,255,255,0.3)", letterSpacing: "0.05em", textTransform: "uppercase", ...(gi > 0 ? { borderTop: "1px solid rgba(255,255,255,0.06)" } : {}) }}>{g.name}</div>
                      {g.models.map((m) => {
                        const active = m.id === selectedModel;
                        const isFree = m.tier === "free";
                        const off = !!m.disabled;
                        return (
                          <button key={m.id} type="button" disabled={off} onClick={() => { if (!off) { onModelChange?.(m.id); setModelOpen(false); } }} style={{ width: "100%", display: "flex", alignItems: "center", gap: 8, padding: "7px 12px", border: "none", background: active ? "rgba(255,255,255,0.06)" : "transparent", color: off ? "rgba(255,255,255,0.3)" : "rgba(255,255,255,0.85)", fontSize: 12, cursor: off ? "not-allowed" : "pointer", textAlign: "left", fontFamily: "inherit", opacity: off ? 0.5 : 1 }}>
                            <span style={{ fontSize: 9, padding: "1px 5px", borderRadius: 4, background: isFree ? "rgba(34,197,94,0.15)" : "rgba(168,85,247,0.15)", color: isFree ? "rgba(134,239,172,1)" : "rgba(216,180,254,1)", fontWeight: 700, flexShrink: 0 }}>{isFree ? "FREE" : "PRO"}</span>
                            <span style={{ fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.label}</span>
                            {off && <span style={{ marginLeft: "auto", fontSize: 9, color: "rgba(255,255,255,0.3)", flexShrink: 0 }}>SOON</span>}
                            {!off && active && <span style={{ marginLeft: "auto", fontSize: 11, color: "rgba(34,197,94,0.8)", flexShrink: 0 }}>✓</span>}
                          </button>
                        );
                      })}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Messages */}
        <div ref={listRef} style={{ flex: "1 1 auto", minHeight: 0, overflow: "auto", padding: 14 }}>
          {messages.length === 0 ? (
            <div style={{ height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 16 }}>
              <div style={{ maxWidth: 320, textAlign: "center", padding: 20, borderRadius: 14, background: "rgba(0,0,0,0.2)" }}>
                <img src={`${BASE}/logo.png`} alt="CodeBot" width={48} height={48} style={{ borderRadius: "50%", margin: "0 auto 12px", display: "block", opacity: 0.8 }} />
                <div style={{ fontSize: 15, fontWeight: 600, color: "rgba(255,255,255,0.9)" }}>CodeBot™ Builder</div>
                <div style={{ fontSize: 12, color: "rgba(255,255,255,0.5)", marginTop: 6, lineHeight: 1.5 }}>
                  {mode === "build" ? "Describe what you want to build. CodeBot turns it into code."
                    : mode === "ask" ? "Ask anything about your project or code."
                    : "Describe a plan. CodeBot will outline the approach before building."}
                </div>
                {mode === "build" && (
                  <div style={{ marginTop: 14, textAlign: "left" }}>
                    <div style={{ fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.4)", marginBottom: 8, letterSpacing: "0.04em" }}>TEMPLATES</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {TEMPLATES.map((t, i) => (
                        <button key={i} type="button" onClick={() => onPromptDraftChange(t.prompt)} style={{ padding: "6px 10px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.1)", background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.85)", fontSize: 11, fontWeight: 500, cursor: "pointer", fontFamily: "inherit" }} title={t.prompt.slice(0, 80) + "…"}>{t.name}</button>
                      ))}
                    </div>
                  </div>
                )}
                <div style={{ marginTop: 12, padding: 12, borderRadius: 10, background: "rgba(255,255,255,0.03)", fontSize: 12, color: "rgba(255,255,255,0.6)", textAlign: "left", lineHeight: 1.5 }}>
                  {mode === "build"
                    ? "Or type your own: e.g. Build a landing page for a mobile detailing business with booking and pricing."
                    : mode === "ask"
                    ? "What does the handleSubmit function do in the checkout component?"
                    : "Plan a multi-page e-commerce app with auth, product catalog, and checkout flow."}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {messages.map((msg, i) => {
                const isUser = msg.role === "user";
                const isLastAssistant = !isUser && i === messages.length - 1 && !isThinking;
                const showPlanBtn = isLastAssistant && mode === "plan" && isPlanMessage(msg.content) && onImplementPlan;
                return (
                  <div key={i}>
                    <div style={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start" }}>
                      <div style={{ maxWidth: "92%", borderRadius: 14, padding: isUser ? "10px 14px" : "12px 16px", fontSize: 13, lineHeight: 1.5, wordBreak: "break-word", background: isUser ? "rgba(56,189,248,0.15)" : "rgba(255,255,255,0.04)", color: isUser ? "rgba(255,255,255,0.92)" : "rgba(230,238,247,0.8)", ...(isUser ? { whiteSpace: "pre-wrap" as const } : {}) }}>
                        {isUser ? msg.content : renderMarkdownLite(msg.content)}
                      </div>
                    </div>
                    {showPlanBtn && (
                      <div style={{ display: "flex", justifyContent: "flex-start", marginTop: 8, paddingLeft: 4 }}>
                        <button
                          type="button"
                          onClick={() => onImplementPlan!(msg.content)}
                          style={{
                            display: "flex", alignItems: "center", gap: 6,
                            height: 36, padding: "0 16px", borderRadius: 10,
                            border: "1px solid rgba(34,197,94,0.3)",
                            background: "linear-gradient(135deg, rgba(34,197,94,0.15), rgba(56,189,248,0.1))",
                            color: "rgba(34,197,94,0.95)", fontWeight: 600, fontSize: 13,
                            cursor: "pointer", fontFamily: "inherit",
                            transition: "all 0.15s",
                          }}
                        >
                          <span style={{ fontSize: 15 }}>⚡</span> Implement Plan
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
              {isThinking && (
                <div style={{ display: "flex", justifyContent: "flex-start" }}>
                  <div style={{ maxWidth: "88%", borderRadius: 14, padding: "12px 16px", fontSize: 13, lineHeight: 1.5, background: "rgba(255,255,255,0.04)", color: "rgba(34,197,94,0.9)", display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: "rgba(34,197,94,0.8)", animation: "cb-think-pulse 1s ease-in-out infinite" }} />
                    CodeBot is working...
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Attached file chip */}
        {attachedFile && (
          <div style={{ padding: "0 14px 4px", display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "5px 10px", borderRadius: 8, background: "rgba(56,189,248,0.1)", border: "1px solid rgba(56,189,248,0.2)", fontSize: 11, color: "rgba(56,189,248,0.9)" }}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              {attachedFile.name}
              <button type="button" onClick={() => setAttachedFile(null)} style={{ background: "none", border: "none", color: "rgba(56,189,248,0.7)", cursor: "pointer", fontSize: 14, padding: 0, lineHeight: 1 }}>×</button>
            </div>
          </div>
        )}

        {/* Composer */}
        <div style={{ flexShrink: 0, padding: "10px 14px 14px", borderTop: "1px solid rgba(255,255,255,0.04)" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <textarea
              data-testid="builder-prompt"
              value={promptDraft}
              rows={5}
              placeholder={placeholder}
              onChange={(e) => onPromptDraftChange(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (canRun) onRunBuild(); } }}
              style={{ width: "100%", resize: "vertical", minHeight: 80, maxHeight: 200, borderRadius: 12, border: "none", background: "rgba(0,0,0,0.24)", padding: "12px 14px", fontSize: 13, color: "rgba(255,255,255,0.9)", outline: "none", fontFamily: "inherit", lineHeight: 1.5, boxSizing: "border-box" }}
            />

            {/* Toolbar row: attach, enhance, etc + submit */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 2, position: "relative" }} ref={toolbarRef}>
                {/* + button to open toolbar popover */}
                <button type="button" onClick={() => setToolbarOpen((s) => !s)} style={{ width: 30, height: 30, borderRadius: 8, border: "none", background: toolbarOpen ? "rgba(255,255,255,0.1)" : "transparent", color: "rgba(255,255,255,0.5)", fontSize: 16, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "inherit", transition: "background 0.15s" }}>
                  {toolbarOpen ? "×" : "+"}
                </button>

                {/* Model pill (inline, always visible) */}
                <button type="button" onClick={() => { setModelOpen((s) => !s); setToolbarOpen(false); }} style={{ display: "flex", alignItems: "center", gap: 4, padding: "3px 8px", borderRadius: 6, border: "none", background: "transparent", color: "rgba(255,255,255,0.35)", fontSize: 11, cursor: "pointer", fontFamily: "inherit" }}>
                  <span style={{ fontSize: 11 }}>❄</span>
                  <span>{currentModel.label.split(" ").slice(-2).join(" ")}</span>
                </button>

                {/* Toolbar popover */}
                {toolbarOpen && (
                  <div style={{ position: "absolute", bottom: 36, left: 0, width: 220, borderRadius: 12, background: "rgba(16,20,28,0.98)", border: "1px solid rgba(255,255,255,0.08)", boxShadow: "0 12px 40px rgba(0,0,0,0.5)", zIndex: 50, overflow: "hidden", padding: "4px 0" }}>
                    <button type="button" onClick={handleFileAttach} style={btnStyle()}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
                      Attach file
                    </button>
                    <button type="button" onClick={handleEnhancePrompt} disabled={!promptDraft.trim() || enhancing} style={btnStyle(!promptDraft.trim() || enhancing)}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
                      {enhancing ? "Enhancing..." : "Enhance prompt"}
                    </button>
                    <div style={{ height: 1, background: "rgba(255,255,255,0.06)", margin: "4px 0" }} />
                    <button type="button" disabled style={btnStyle(true)}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 21l-6-6m2-5a7 7 0 1 1-14 0 7 7 0 0 1 14 0z"/></svg>
                      Search Help Center
                      <span style={comingSoonBadge}>SOON</span>
                    </button>
                    <button type="button" disabled style={btnStyle(true)}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3M21 5v14c0 1.66-4 3-9 3s-9-1.34-9-3V5"/></svg>
                      Database
                      <span style={comingSoonBadge}>SOON</span>
                    </button>
                  </div>
                )}
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                {isThinking && onCancel && (
                  <button type="button" onClick={onCancel} style={{ height: 34, padding: "0 14px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.1)", background: "transparent", color: "rgba(255,255,255,0.5)", fontWeight: 500, fontSize: 12, cursor: "pointer", fontFamily: "inherit" }}>
                    Cancel
                  </button>
                )}
                <button
                  type="button"
                  data-testid="builder-build-now"
                  disabled={!canRun}
                  onClick={onRunBuild}
                  title={canRun ? actionLabel : isThinking ? "Working..." : "Type a prompt"}
                  style={{ height: 34, padding: "0 18px", borderRadius: 8, border: "none", background: canRun ? "rgba(255,255,255,0.92)" : "rgba(255,255,255,0.06)", color: canRun ? "rgba(0,0,0,0.95)" : "rgba(255,255,255,0.35)", fontWeight: 600, fontSize: 13, cursor: canRun ? "pointer" : "not-allowed", fontFamily: "inherit", whiteSpace: "nowrap" }}
                >
                  {isThinking ? "Working..." : actionLabel}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
