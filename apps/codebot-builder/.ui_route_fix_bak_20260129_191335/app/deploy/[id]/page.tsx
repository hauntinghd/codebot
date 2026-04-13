export default async function DeployPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div style={{ minHeight: "100vh", background: "#0b0f14", color: "white", padding: 32 }}>
      <h1 style={{ fontSize: 24, fontWeight: 700 }}>Deployment</h1>
      <p style={{ marginTop: 12, opacity: 0.8 }}>
        Deployment ID: <code>{id}</code>
      </p>
      <p style={{ marginTop: 12, opacity: 0.6 }}>
        Phase 5 will map this to a real public URL and serve the built artifact.
      </p>
    </div>
  );
}
