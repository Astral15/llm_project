"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { login, register } from "@/lib/api";

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const router = useRouter();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "register") {
        if (password !== passwordConfirm) {
          throw new Error("Passwords do not match");
        }
        await register(username, password, passwordConfirm);
      }

      const token = await login(username, password);
      if (!token) throw new Error("No token returned");

      localStorage.setItem("token", token);
      router.push("/");
    } catch (err: any) {
      setError(err?.message ?? "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 420, margin: "0 auto" }}>
      <h1 style={{ fontSize: 24, marginBottom: 8 }}>Welcome</h1>
      <p style={{ fontSize: 14, opacity: 0.7, marginBottom: 24 }}>
        {mode === "login"
          ? "Log in to work with prompts, images and structured outputs."
          : "Create an account and then log in."}
      </p>

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button
          type="button"
          onClick={() => setMode("login")}
          style={{
            flex: 1,
            padding: "6px 0",
            borderRadius: 6,
            border: "1px solid #1f2937",
            background: mode === "login" ? "#111827" : "transparent",
            color: "#e5e5e5",
            cursor: "pointer",
          }}
        >
          Login
        </button>
        <button
          type="button"
          onClick={() => setMode("register")}
          style={{
            flex: 1,
            padding: "6px 0",
            borderRadius: 6,
            border: "1px solid #1f2937",
            background: mode === "register" ? "#111827" : "transparent",
            color: "#e5e5e5",
            cursor: "pointer",
          }}
        >
          Register
        </button>
      </div>

      <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
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
        {mode === "register" && (
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
        )}

        {error && (
          <div style={{ color: "#f97373", fontSize: 13, marginTop: 4 }}>
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{
            marginTop: 8,
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
          {loading ? "Working..." : mode === "login" ? "Login" : "Register & Login"}
        </button>
      </form>
    </main>
  );
}
