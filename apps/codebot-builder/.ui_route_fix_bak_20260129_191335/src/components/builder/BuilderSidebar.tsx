"use client";

import React, { useEffect, useMemo, useRef } from "react";

type Message = {
  role: "user" | "assistant";
  content: string;
};

function bubbleClass(role: Message["role"]) {
  if (role === "user") {
    return "bg-white text-black";
  }
  return "bg-white/5 border border-white/10 text-white";
}

export default function BuilderSidebar(props: {
  isThinking: boolean;
  messages: Message[];
  promptDraft: string;
  onPromptDraftChange: (v: string) => void;
  onRunBuild: () => void;
}) {
  const { isThinking, messages, promptDraft, onPromptDraftChange, onRunBuild } = props;

  const listRef = useRef<HTMLDivElement | null>(null);

  const canRun = useMemo(() => promptDraft.trim().length > 0 && !isThinking, [promptDraft, isThinking]);

  const inputLines = useMemo(() => promptDraft.split("\n").length, [promptDraft]);
  const inputRows = Math.min(8, Math.max(2, inputLines));

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages, isThinking]);

  return (
    <aside className="cb-sidebar cb-sidebar--full flex flex-col">
      {/* Header */}
      <div className="px-5 py-4 border-b border-white/10">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-sm font-extrabold text-white">Chat</div>
            <div className="text-xs text-white/50 mt-1">Describe what you want. We turn it into a build plan.</div>
          </div>

          <div className="text-[11px] font-extrabold text-white/60">
            {isThinking ? "Thinking…" : "Ready"}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div ref={listRef} className="flex-1 overflow-auto px-5 py-5 space-y-3">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="rounded-2xl border border-white/10 bg-black/20 p-5 text-center max-w-[420px]">
              <div className="text-base font-black text-white">CodeBot™ Builder</div>
              <div className="mt-2 text-sm text-white/65">
                Start with a clear request. Example:
                <div className="mt-2 rounded-xl border border-white/10 bg-black/20 p-3 text-xs text-white/70 text-left whitespace-pre-wrap">
                  Build a landing page for a mobile detailing business. Add booking, pricing, and a clean homepage.
                </div>
              </div>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <div key={i} className={msg.role === "user" ? "flex justify-end" : "flex justify-start"}>
                <div
                  className={[
                    "max-w-[92%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap leading-relaxed",
                    bubbleClass(msg.role),
                  ].join(" ")}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {isThinking ? (
              <div className="flex justify-start">
                <div className="max-w-[92%] rounded-2xl px-4 py-3 text-sm bg-white/5 border border-white/10 text-white/80">
                  Working…
                </div>
              </div>
            ) : null}
          </>
        )}
      </div>

      {/* Composer */}
      <div className="shrink-0 border-t border-white/10 p-4">
        <div className="flex items-end gap-2">
          <textarea
            className="flex-1 resize-none rounded-2xl bg-white/5 border border-white/10 px-4 py-3 text-sm text-white outline-none focus:border-white/20"
            value={promptDraft}
            rows={inputRows}
            placeholder="Describe what you want to build…"
            onChange={(e) => onPromptDraftChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (canRun) onRunBuild();
              }
            }}
          />

          <button
            type="button"
            className={[
              "h-[46px] px-5 rounded-2xl font-extrabold transition",
              canRun
                ? "bg-white text-black hover:opacity-90"
                : "bg-white/10 text-white/50 cursor-not-allowed",
            ].join(" ")}
            disabled={!canRun}
            onClick={onRunBuild}
            title={canRun ? "Run build" : isThinking ? "Busy" : "Type a prompt"}
          >
            {isThinking ? "Thinking…" : "Build now"}
          </button>
        </div>

        <div className="mt-3 text-center text-xs text-white/45">
          Enter to build • Shift+Enter for new line
        </div>
      </div>
    </aside>
  );
}
