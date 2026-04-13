"use client";

import React, { Component, type ErrorInfo, type ReactNode } from "react";

type Props = { children: ReactNode; fallback?: ReactNode };
type State = { hasError: boolean; error: Error | null };

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error("[CodeBot ErrorBoundary]", error, errorInfo);
  }

  render(): ReactNode {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div
          style={{
            padding: 24,
            textAlign: "center",
            maxWidth: 480,
            margin: "40px auto",
            background: "rgba(255,255,255,0.04)",
            borderRadius: 12,
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          <div style={{ fontSize: 18, fontWeight: 600, color: "#f87171", marginBottom: 8 }}>
            Something went wrong
          </div>
          <div style={{ fontSize: 13, color: "rgba(255,255,255,0.7)", marginBottom: 16 }}>
            {this.state.error.message}
          </div>
          <button
            type="button"
            onClick={() => this.setState({ hasError: false, error: null })}
            style={{
              padding: "8px 16px",
              borderRadius: 8,
              border: "none",
              background: "rgba(255,255,255,0.1)",
              color: "white",
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
