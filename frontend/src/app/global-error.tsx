"use client";

import * as React from "react";

/**
 * Last-resort boundary: catches errors thrown by the root layout itself.
 *
 * This replaces the entire document, so it must render its own `<html>` and
 * `<body>` — the app's providers, fonts and Tailwind layer are all gone by the
 * time it runs. Deliberately styled inline for that reason.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  React.useEffect(() => {
    console.error("Fatal application error:", error);
  }, [error]);

  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily:
            "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
          background: "#fafafa",
          color: "#0a0a0a",
        }}
      >
        <div style={{ textAlign: "center", padding: "1rem", maxWidth: "28rem" }}>
          <h1 style={{ fontSize: "1.125rem", fontWeight: 500, margin: "0 0 .5rem" }}>
            Nexora failed to load
          </h1>
          <p style={{ fontSize: ".875rem", color: "#666", margin: "0 0 1.25rem" }}>
            A fatal error stopped the application from starting.
          </p>
          {error.digest && (
            <p style={{ fontSize: ".75rem", color: "#888", margin: "0 0 1.25rem" }}>
              Reference: <code>{error.digest}</code>
            </p>
          )}
          <button
            onClick={reset}
            style={{
              cursor: "pointer",
              borderRadius: ".5rem",
              border: "1px solid #0a0a0a",
              background: "#0a0a0a",
              color: "#fff",
              padding: ".5rem 1rem",
              fontSize: ".875rem",
            }}
          >
            Reload
          </button>
        </div>
      </body>
    </html>
  );
}
