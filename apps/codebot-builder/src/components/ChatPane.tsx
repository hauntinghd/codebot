"use client";

import React, { useMemo, useRef, useState } from "react";

type ChatMsg = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

function bubbleClass(role: ChatMsg["role"]) {
  if (role === "user") return "bg-white text-black";
  return "bg-white/5 border border-white/10 text-white";
}

export default function ChatPane({
  onSendPrompt,
}: {
  onSendPrompt: (prompt: string) => Promise<void>;
}) {
  const [messages, setMessages] = useState<ChatMsg[]>(() => [
    { id: "m0", role: "assistant", content: "Tell me what you want to build." },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const listRef = useRef<HTMLDivElement | null>(null);

  const canSend = useMemo(() => input.trim().length > 0 && !busy, [input, busy]);

  function scrollToBottom() {
    requestAnimationFrame(() => {
      const el = listRef.current;
      if (!el) return;
      el.scrollTop = el.scrollHeight;
    });
  }

  async function send() {
    const prompt = input.trim();
    if (!prompt || busy) return;

    const userMsg: ChatMsg = { id: crypto.randomUUID(), role: "user", content: prompt };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setBusy(true);
    scrollToBottom();

    const thinkingId = crypto.randomUUID();
    setMessages((m) => [...m, { id: thinkingId, role: "assistant", content: "Working…" }]);
    scrollToBottom();

    try {
      await onSendPrompt(prompt);

      // If sendPrompt succeeds but doesn’t return plan text yet, keep it simple for now:
      setMessages((m) =>
        m.map((x) => (x.id === thinkingId ? { ...x, content: "Plan received." } : x))
      );
    } catch (e: any) {
      setMessages((m) =>
        m.map((x) =>
          x.id === thinkingId ? { ...x, content: e?.message || "Request failed" } : x
        )
      );
    } finally {
      setBusy(false);
      scrollToBottom();
    }
  }

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-3 border-b border-white/10">
        <div className="text-sm font-semibold">Chat</div>
      </div>

      <div ref={listRef} className="flex-1 overflow-auto px-4 py-4 space-y-3">
        {messages.map((m) => (
          <div key={m.id} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
            <div
              className={[
                "max-w-[90%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap",
                bubbleClass(m.role),
              ].join(" ")}
            >
              {m.content}
            </div>
          </div>
        ))}
      </div>

      <div className="border-t border-white/10 p-3">
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            rows={2}
            placeholder="Message CodeBot…"
            className="flex-1 resize-none rounded-2xl bg-white/5 border border-white/10 px-4 py-3 text-sm outline-none focus:border-white/20"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
          />
          <button
            type="button"
            onClick={send}
            disabled={!canSend}
            className={[
              "h-[46px] px-4 rounded-2xl font-medium transition",
              canSend
                ? "bg-white text-black hover:opacity-90"
                : "bg-white/10 text-white/50 cursor-not-allowed",
            ].join(" ")}
          >
            Send now
          </button>
        </div>
      </div>
    </div>
  );
}
