"use client";

import React, { useMemo, useRef } from "react";

export default function BuilderChatInput(props: {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
}) {
  const { value, onChange, onSend } = props;

  const taRef = useRef<HTMLTextAreaElement | null>(null);
  const canSend = useMemo(() => value.trim().length > 0, [value]);

  return (
    <div>
      <div className="cb-chatbar-inner">
        <textarea
          ref={taRef}
          className="cb-chatbar-textarea"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Describe what you want to build…"
          rows={2}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              if (!canSend) return;
              onSend();
            }
          }}
        />

        <button
          type="button"
          className="cb-send"
          onClick={() => {
            if (!canSend) return;
            onSend();
            window.setTimeout(() => taRef.current?.focus(), 0);
          }}
          title="Send"
          aria-disabled={!canSend}
          disabled={!canSend}
        >
          
        </button>
      </div>

      <div className="cb-chatbar-hint"></div>
    </div>
  );
}
