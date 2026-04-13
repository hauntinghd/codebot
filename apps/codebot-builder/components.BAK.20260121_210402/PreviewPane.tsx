"use client";

type Props = {
  viewMode: "preview" | "code";
  device: "desktop" | "tablet" | "mobile";
};

export default function PreviewPane({ viewMode, device }: Props) {
  const frameClass =
    device === "desktop"
      ? "w-full h-full"
      : device === "tablet"
      ? "w-[820px] max-w-full h-[980px]"
      : "w-[420px] max-w-full h-[860px]";

  return (
    <div className="h-full w-full flex flex-col">
      <div className="flex-1 overflow-auto p-6">
        <div className="mx-auto flex flex-col items-center justify-center gap-4 rounded-3xl border border-white/10 bg-white/5 min-h-[520px]">
          <div className="opacity-80 text-sm">
            {viewMode === "preview" ? "Your website will appear here" : "Code view will appear here"}
          </div>
          <div className="text-xs text-white/50">
            Next step: after plan → we wire file creation + live preview.
          </div>

          <div className="mt-3 rounded-2xl border border-white/10 bg-black/30 p-3">
            <div className={frameClass} />
          </div>
        </div>
      </div>
    </div>
  );
}
