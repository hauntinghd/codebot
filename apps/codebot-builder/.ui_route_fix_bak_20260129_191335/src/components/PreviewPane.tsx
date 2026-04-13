"use client";

export default function PreviewPane({
  mode,
  device,
  deployedUrl,
}: {
  mode: "preview" | "code";
  device: "desktop" | "tablet" | "mobile";
  deployedUrl?: string | null;
}) {
  const frameClass =
    device === "desktop"
      ? "w-full h-full"
      : device === "tablet"
        ? "w-[820px] max-w-[92%] h-[92%]"
        : "w-[420px] max-w-[92%] h-[92%]";

  return (
    <div className="h-full w-full p-4">
      <div className={"cb-panel h-full flex items-center justify-center " + frameClass}>
        <div className="text-center max-w-[520px] px-6">
          <div className="mx-auto h-14 w-14 rounded-xl bg-white/5 ring-1 ring-white/10 flex items-center justify-center mb-4">
            🖥
          </div>
          <div className="text-xl font-semibold">Your website will appear here</div>
          <div className="mt-2 text-sm text-white/55 leading-relaxed">
            Describe what you want to build in the chat and watch it come to life.
          </div>
          {deployedUrl ? (
            <div className="mt-3 text-xs text-white/60">
              Deployed: <span className="text-cyan-200/85">{deployedUrl}</span>
            </div>
          ) : null}
          <div className="mt-4 text-xs text-white/40">
            Mode: {mode} • Device: {device}
          </div>
        </div>
      </div>
    </div>
  );
}
