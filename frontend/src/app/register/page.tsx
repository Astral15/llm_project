"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { register } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // reset fields on first mount and start fade-in
    setUsername("");
    setPassword("");
    setPasswordConfirm("");
    setMounted(true);
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (password !== passwordConfirm) {
        throw new Error("Passwords do not match");
      }

      await register(username, password, passwordConfirm);

      // clear again for safety
      setUsername("");
      setPassword("");
      setPasswordConfirm("");

      router.push("/login?registered=1");
    } catch (err: any) {
      setError(err?.message ?? "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  const cardStyle = {
    width: "100%",
    maxWidth: 420,
    padding: "24px 22px 26px",
    borderRadius: 12,
    background: "#020617",
    border: "1px solid #1f2937",
    boxShadow: "0 18px 45px rgba(15,23,42,0.9)",
    opacity: mounted ? 1 : 0,
    transform: mounted ? "translateY(0px)" : "translateY(8px)",
    transition: "opacity 180ms ease-out, transform 180ms ease-out",
  } as const;

  const tabBase = {
    flex: 1,
    padding: "7px 0",
    borderRadius: 999,
    fontSize: 14,
    fontWeight: 500,
    border: "1px solid transparent",
    background: "transparent",
    cursor: "pointer",
    transition: "background 0.18s ease, color 0.18s ease, border-color 0.18s ease",
  } as const;

  const primaryButton = {
    marginTop: 6,
    padding: "9px 0",
    borderRadius: 999,
    border: "none",
    background: "#3b82f6",
    color: "#eff6ff",
    fontWeight: 600,
    fontSize: 14,
    cursor: loading ? "default" : "pointer",
    opacity: loading ? 0.9 : 1,
    boxShadow: "0 10px 24px rgba(59,130,246,0.55)",
    transition: "transform 0.1s ease-out, box-shadow 0.1s ease-out, opacity 0.2s ease",
  } as const;

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        padding: "40px 12px 32px", // moves it up
      }}
    >
      <section style={cardStyle}>
        <header style={{ marginBottom: 18 }}>
          <h1
            style={{
              fontSize: 24,
              margin: 0,
              fontWeight: 650,
              letterSpacing: "0.01em",
              color: "#e5e7eb",
            }}
          >
            Register
          </h1>
          <p
            style={{
              marginTop: 6,
              marginBottom: 0,
              fontSize: 13,
              color: "#9ca3af",
            }}
          >
            Create a new account to start using the structured output app.
          </p>
        </header>

        {/* Tabs */}
        <div
          style={{
            display: "flex",
            gap: 6,
            marginBottom: 18,
            padding: 4,
            borderRadius: 999,
            background: "#020617",
            border: "1px solid #1f2937",
          }}
        >
          <button
            type="button"
            onClick={() => router.push("/login")}
            style={{
              ...tabBase,
              background: "#020617",
              color: "#cbd5f5",
              borderColor: "transparent",
            }}
          >
            Login
          </button>
          <button
            type="button"
            style={{
              ...tabBase,
              background: "#1f2937",
              color: "#f9fafb",
              borderColor: "#4b5563",
            }}
          >
            Register
          </button>
        </div>

        <form
          onSubmit={onSubmit}
          style={{ display: "flex", flexDirection: "column", gap: 12 }}
        >
          <div>
            <label
              style={{
                fontSize: 12,
                textTransform: "uppercase",
                letterSpacing: "0.09em",
                color: "#9ca3af",
              }}
            >
              Username
            </label>
            <input
              placeholder="Choose a username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="off"
              style={{
                marginTop: 4,
                width: "100%",
                padding: "8px 10px",
                borderRadius: 8,
                border: "1px solid #1f2937",
                background: "#020617",
                color: "#e5e5e5",
                fontSize: 14,
              }}
            />
          </div>

          <div>
            <label
              style={{
                fontSize: 12,
                textTransform: "uppercase",
                letterSpacing: "0.09em",
                color: "#9ca3af",
              }}
            >
              Password
            </label>
            <input
              placeholder="Create a password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              style={{
                marginTop: 4,
                width: "100%",
                padding: "8px 10px",
                borderRadius: 8,
                border: "1px solid #1f2937",
                background: "#020617",
                color: "#e5e5e5",
                fontSize: 14,
              }}
            />
          </div>

          <div>
            <label
              style={{
                fontSize: 12,
                textTransform: "uppercase",
                letterSpacing: "0.09em",
                color: "#9ca3af",
              }}
            >
              Confirm password
            </label>
            <input
              placeholder="Repeat your password"
              type="password"
              value={passwordConfirm}
              onChange={(e) => setPasswordConfirm(e.target.value)}
              autoComplete="new-password"
              style={{
                marginTop: 4,
                width: "100%",
                padding: "8px 10px",
                borderRadius: 8,
                border: "1px solid #1f2937",
                background: "#020617",
                color: "#e5e5e5",
                fontSize: 14,
              }}
            />
          </div>

          {error && (
            <div style={{ color: "#f97373", fontSize: 13, marginTop: 4 }}>
              {error}
            </div>
          )}

          <button type="submit" disabled={loading} style={primaryButton}>
            {loading ? "Creating account…" : "Create account"}
          </button>

          <p
            style={{
              marginTop: 10,
              marginBottom: 0,
              fontSize: 12,
              color: "#9ca3af",
              textAlign: "center",
            }}
          >
            Already registered?{" "}
            <span
              style={{ color: "#93c5fd", cursor: "pointer" }}
              onClick={() => router.push("/login")}
            >
              Log in
            </span>
          </p>
        </form>
      </section>
    </main>
  );
}
