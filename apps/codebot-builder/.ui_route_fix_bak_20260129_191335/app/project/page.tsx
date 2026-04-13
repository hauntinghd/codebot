import AuthGate from "@/components/AuthGate";

export default function ProjectPage({ params }: { params: { id: string } }) {
  return (
    <AuthGate>
      <main className="min-h-screen cb-bg">
        <div className="max-w-5xl mx-auto px-6 py-10">
          <div className="cb-panel p-6">
            <h1 className="text-2xl font-bold text-white">Project</h1>
            <p className="text-white/70 mt-2">
              Project ID: <code className="text-white">{params.id}</code>
            </p>
            <p className="text-white/70 mt-4">
              Next: load project files, mount into WebContainer, run preview.
            </p>
          </div>
        </div>
      </main>
    </AuthGate>
  );
}
