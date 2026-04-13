"use client";

import React, { useCallback, useMemo, useState } from "react";
import dynamic from "next/dynamic";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

type FileEntry = { path: string; content: string };

const LANGUAGE_MAP: Record<string, string> = {
  ".js": "javascript",
  ".jsx": "javascript",
  ".ts": "typescript",
  ".tsx": "typescript",
  ".html": "html",
  ".htm": "html",
  ".css": "css",
  ".json": "json",
  ".md": "markdown",
  ".py": "python",
  ".yaml": "yaml",
  ".yml": "yaml",
  ".sh": "shell",
  ".sql": "sql",
};

function getLanguage(path: string): string {
  const ext = path.includes(".") ? path.replace(/^.*\./, ".") : "";
  return LANGUAGE_MAP[ext.toLowerCase()] ?? "plaintext";
}

export default function CodeEditorPanel({
  files,
  onFilesChange,
  onAddPackage,
}: {
  files: FileEntry[];
  onFilesChange: (next: FileEntry[]) => void;
  onAddPackage?: () => void;
}) {
  const [selectedPath, setSelectedPath] = useState<string | null>(files[0]?.path ?? null);
  const selectedFile = useMemo(() => files.find((f) => f.path === selectedPath), [files, selectedPath]);

  const handleEditorChange = useCallback(
    (value: string | undefined) => {
      if (!selectedPath) return;
      onFilesChange(
        files.map((f) => (f.path === selectedPath ? { path: f.path, content: value ?? "" } : f))
      );
    },
    [selectedPath, files, onFilesChange]
  );

  if (files.length === 0) {
    return (
      <div style={{ padding: 24, textAlign: "center", color: "rgba(255,255,255,0.5)", fontSize: 13 }}>
        No files yet. Run a build to generate code.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", height: "100%", minHeight: 0 }}>
      {/* File list */}
      <div
        style={{
          width: 220,
          flexShrink: 0,
          borderRight: "1px solid rgba(255,255,255,0.06)",
          overflow: "auto",
          background: "rgba(0,0,0,0.15)",
        }}
      >
        <div style={{ padding: "10px 12px", fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.4)" }}>
          FILES
        </div>
        {files.map((f) => (
          <button
            key={f.path}
            type="button"
            onClick={() => setSelectedPath(f.path)}
            style={{
              width: "100%",
              padding: "8px 12px",
              textAlign: "left",
              border: "none",
              background: selectedPath === f.path ? "rgba(255,255,255,0.08)" : "transparent",
              color: selectedPath === f.path ? "white" : "rgba(255,255,255,0.75)",
              fontSize: 12,
              fontFamily: "ui-monospace, monospace",
              cursor: "pointer",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {f.path}
          </button>
        ))}
        {onAddPackage && files.some((f) => f.path === "package.json" || f.path.endsWith("/package.json")) && (
          <div style={{ padding: 12, borderTop: "1px solid rgba(255,255,255,0.06)" }}>
            <button
              type="button"
              onClick={onAddPackage}
              style={{
                width: "100%",
                padding: "8px 12px",
                borderRadius: 8,
                border: "1px solid rgba(255,255,255,0.15)",
                background: "rgba(34,197,94,0.1)",
                color: "rgba(134,239,172,1)",
                fontSize: 12,
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              + Add npm package
            </button>
          </div>
        )}
      </div>
      {/* Editor */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {selectedFile ? (
          <MonacoEditor
            height="100%"
            language={getLanguage(selectedFile.path)}
            value={selectedFile.content}
            onChange={handleEditorChange}
            theme="vs-dark"
            options={{
              minimap: { enabled: false },
              fontSize: 13,
              lineNumbers: "on",
              wordWrap: "on",
              scrollBeyondLastLine: false,
              automaticLayout: true,
              padding: { top: 12 },
            }}
          />
        ) : (
          <div style={{ padding: 24, color: "rgba(255,255,255,0.5)", fontSize: 13 }}>
            Select a file
          </div>
        )}
      </div>
    </div>
  );
}
