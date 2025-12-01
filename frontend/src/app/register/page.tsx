"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { register } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (password !== passwordConfirm) {
        throw new Error("Passwords do not match");
      }

      await register(username, password, passwordConfirm);

      router.push("/login?registered=1");
    } catch (err: any) {
      setError(err?.message ?? "Failed to register");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 420, margin: "0 auto" }}>
      <h1 style={{ fontSize: 24, marginBottom: 8 }}>Register</h1>

      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        <a
          href="/login"
          style={{
            flex: 1,
            textAlign: "center",
            padding: "8px 0",
            borderRadius: 6,
            border: "1px solid #334155",
            background: "#0f172a",
            color: "#94a3b8",
            fontWeight: 500,
            textDecoration: "none",
          }}
        >
          Login
        </a>

        <a
          href="/register"
          style={{
            flex: 1,
            textAlign: "center",
            padding: "8px 0",
            borderRadius: 6,
            border: "1px solid #475569",
            background: "#1e293b",
            color: "#e2e8f0",
            fontWeight: 500,
            textDecoration: "none",
          }}
        >
          Register
        </a>
      </div>

      <form
        onSubmit={onSubmit}
        style={{ display: "flex", flexDirection: "column", gap: 12 }}
      >
        <input
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          style={{
            padding: "8px 10px",
            borderRadius: 6,
            border: "1px solid #1f2937",
            background: "#020617",
            color: "#e5e5e5",
          }}
        />

        <input
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={{
            padding: "8px 10px",
            borderRadius: 6,
            border: "1px solid #1f2937",
            background: "#020617",
            color: "#e5e5e5",
          }}
        />

        <input
          placeholder="Confirm Password"
          type="password"
          value={passwordConfirm}
          onChange={(e) => setPasswordConfirm(e.target.value)}
          style={{
            padding: "8px 10px",
            borderRadius: 6,
            border: "1px solid #1f2937",
            background: "#020617",
            color: "#e5e5e5",
          }}
        />

        {error && (
          <div style={{ color: "#f97373", fontSize: 13 }}>{error}</div>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{
            padding: "8px 0",
            borderRadius: 6,
            border: "none",
            background: "#22c55e",
            color: "#020617",
            fontWeight: 600,
            cursor: loading ? "default" : "pointer",
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? "Creating..." : "Create Account"}
        </button>
      </form>
    </main>
  );
}
