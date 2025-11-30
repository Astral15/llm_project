import type { ReactNode } from "react";
import "../styles/globals.css";

export const metadata = {
  title: "LLM Structured Output",
  description: "Prompt + Image → Structured fields",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          background: "#020617",
          color: "#e5e5e5",
          fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        }}
      >
        <div
          style={{
            maxWidth: 960,
            margin: "0 auto",
            padding: "24px 16px 48px",
          }}
        >
          <header
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 24,
            }}
          >
            <div style={{ fontWeight: 600 }}>LLM Structured Output</div>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
