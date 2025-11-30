"use client";

import { useEffect, useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { getStructured, uploadImage, type OutputField } from "@/lib/api";

type FieldRow = OutputField & { id: number };

export default function MainPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);

  const [prompt, setPrompt] = useState("Who invented the Turing machine?");
  const [fields, setFields] = useState<FieldRow[]>([
    { id: 1, name: "name", type: "string" },
    { id: 2, name: "surname", type: "string" },
    { id: 3, name: "inventor_birth_year", type: "number" },
  ]);

  const [file, setFile] = useState<File | null>(null);
  const [imageId, setImageId] = useState<number | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  const [result, setResult] = useState<Record<string, string | number | null> | null>(null);
  const [fromCache, setFromCache] = useState(false);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // load token or redirect to /login
  useEffect(() => {
    const t = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    if (!t) {
      router.push("/login");
    } else {
      setToken(t);
    }
  }, [router]);

  function updateField(id: number, patch: Partial<FieldRow>) {
    setFields((fs) => fs.map((f) => (f.id === id ? { ...f, ...patch } : f)));
  }

  function addField() {
    const id = Date.now();
    setFields((fs) => [...fs, { id, name: "", type: "string" }]);
  }

  function removeField(id: number) {
    setFields((fs) => fs.filter((f) => f.id !== id));
  }

  async function onUploadImage() {
    if (!token || !file) return;
    setUploading(true);
    setError(null);
    try {
      const { id, url } = await uploadImage(file, token);
      setImageId(id);
      setImageUrl(url);
    } catch (err: any) {
      setError(err?.message ?? "Failed to upload image");
    } finally {
      setUploading(false);
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!token) {
      router.push("/login");
      return;
    }
    setError(null);
    setLoading(true);
    setResult(null);
    setFromCache(false);
    try {
      const cleanFields = fields
        .map(({ name, type }) => ({ name: name.trim(), type }))
        .filter((f) => f.name !== "");
      if (!cleanFields.length) throw new Error("Add at least one field");

      const resp = await getStructured(
        {
          prompt: prompt.trim(),
          fields: cleanFields,
          image_id: imageId,
        },
        token
      );
      setResult(resp.data);
      setFromCache(resp.from_cache);
    } catch (err: any) {
      setError(err?.message ?? "Failed to get structured response");
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    localStorage.removeItem("token");
    setToken(null);
    router.push("/login");
  }

  if (!token) {
    return (
      <main>
        <p>Redirecting to login…</p>
      </main>
    );
  }

  return (
    <main style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
      <section style={{ flex: 3, minWidth: 0 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
          <h1 style={{ fontSize: 22, margin: 0 }}>Prompt & Structure</h1>
          <button
            type="button"
            onClick={logout}
            style={{
              padding: "4px 8px",
              borderRadius: 6,
              border: "1px solid #1f2937",
              background: "transparent",
              color: "#e5e5e5",
              cursor: "pointer",
              fontSize: 12,
            }}
          >
            Logout
          </button>
        </div>

        <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <label style={{ fontSize: 13, opacity: 0.8 }}>Prompt</label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={4}
              style={{
                width: "100%",
                marginTop: 4,
                padding: 8,
                borderRadius: 6,
                border: "1px solid #1f2937",
                background: "#020617",
                color: "#e5e5e5",
                resize: "vertical",
              }}
            />
          </div>

          <div>
            <label style={{ fontSize: 13, opacity: 0.8 }}>Output fields</label>
            <div
              style={{
                marginTop: 4,
                borderRadius: 6,
                border: "1px solid #1f2937",
                padding: 8,
                display: "flex",
                flexDirection: "column",
                gap: 8,
              }}
            >
              {fields.map((f) => (
                <div
                  key={f.id}
                  style={{
                    display: "flex",
                    gap: 8,
                    alignItems: "center",
                  }}
                >
                  <input
                    placeholder="field_name"
                    value={f.name}
                    onChange={(e) => updateField(f.id, { name: e.target.value })}
                    style={{
                      flex: 2,
                      padding: "6px 8px",
                      borderRadius: 4,
                      border: "1px solid #1f2937",
                      background: "#020617",
                      color: "#e5e5e5",
                      fontSize: 13,
                    }}
                  />
                  <select
                    value={f.type}
                    onChange={(e) =>
                      updateField(f.id, { type: e.target.value as FieldRow["type"] })
                    }
                    style={{
                      flex: 1,
                      padding: "6px 8px",
                      borderRadius: 4,
                      border: "1px solid #1f2937",
                      background: "#020617",
                      color: "#e5e5e5",
                      fontSize: 13,
                    }}
                  >
                    <option value="string">string</option>
                    <option value="number">number</option>
                  </select>
                  <button
                    type="button"
                    onClick={() => removeField(f.id)}
                    style={{
                      padding: "4px 8px",
                      borderRadius: 4,
                      border: "1px solid #450a0a",
                      background: "transparent",
                      color: "#fecaca",
                      fontSize: 11,
                      cursor: "pointer",
                    }}
                  >
                    ✕
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={addField}
                style={{
                  marginTop: 4,
                  padding: "4px 8px",
                  borderRadius: 4,
                  border: "1px dashed #4b5563",
                  background: "transparent",
                  color: "#9ca3af",
                  fontSize: 12,
                  cursor: "pointer",
                  alignSelf: "flex-start",
                }}
              >
                + Add field
              </button>
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              style={{
                padding: "8px 14px",
                borderRadius: 6,
                border: "none",
                background: "#22c55e",
                color: "#020617",
                fontWeight: 600,
                cursor: loading ? "default" : "pointer",
                opacity: loading ? 0.7 : 1,
              }}
            >
              {loading ? "Asking LLM…" : "Run"}
            </button>
          </div>

          {error && (
            <div style={{ color: "#f97373", fontSize: 13 }}>
              {error}
            </div>
          )}
        </form>
      </section>

      <section style={{ flex: 2, minWidth: 0, display: "flex", flexDirection: "column", gap: 16 }}>
        <div
          style={{
            borderRadius: 6,
            border: "1px solid #1f2937",
            padding: 10,
          }}
        >
          <div style={{ fontSize: 13, marginBottom: 8, opacity: 0.8 }}>Image</div>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => {
              const f = e.target.files?.[0] ?? null;
              setFile(f);
              setImageId(null);
              setImageUrl(null);
            }}
          />
          <button
            type="button"
            disabled={!file || !token || uploading}
            onClick={onUploadImage}
            style={{
              marginTop: 8,
              padding: "6px 10px",
              borderRadius: 6,
              border: "none",
              background: "#3b82f6",
              color: "#020617",
              fontSize: 13,
              cursor: !file || uploading ? "default" : "pointer",
              opacity: !file || uploading ? 0.6 : 1,
            }}
          >
            {uploading ? "Uploading…" : "Upload to MinIO"}
          </button>
          {imageId && (
            <div style={{ marginTop: 6, fontSize: 12, opacity: 0.8 }}>
              Image stored with id <code>{imageId}</code>
            </div>
          )}
          {imageUrl && (
            <div style={{ marginTop: 8 }}>
              <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 4 }}>Preview</div>
              {/* imageUrl is internal (http://minio:9000/...), not reachable from browser. 
                  Just show that it's set, don't try to render <img src>. */}
              <code style={{ fontSize: 11, wordBreak: "break-all" }}>{imageUrl}</code>
            </div>
          )}
        </div>

        <div
          style={{
            borderRadius: 6,
            border: "1px solid #1f2937",
            padding: 10,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
            <div style={{ fontSize: 13, opacity: 0.8 }}>Structured response</div>
            {result && (
              <div style={{ fontSize: 11, opacity: 0.7 }}>
                {fromCache ? "from cache" : "fresh"}
              </div>
            )}
          </div>
          {!result && <div style={{ fontSize: 12, opacity: 0.6 }}>No response yet.</div>}
          {result && (
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: 13,
              }}
            >
              <thead>
                <tr>
                  <th
                    style={{
                      textAlign: "left",
                      borderBottom: "1px solid #1f2937",
                      padding: "4px 2px",
                    }}
                  >
                    Field
                  </th>
                  <th
                    style={{
                      textAlign: "left",
                      borderBottom: "1px solid #1f2937",
                      padding: "4px 2px",
                    }}
                  >
                    Value
                  </th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(result).map(([k, v]) => (
                  <tr key={k}>
                    <td
                      style={{
                        padding: "4px 2px",
                        borderBottom: "1px solid #020617",
                        opacity: 0.85,
                      }}
                    >
                      {k}
                    </td>
                    <td
                      style={{
                        padding: "4px 2px",
                        borderBottom: "1px solid #020617",
                      }}
                    >
                      {v === null ? <span style={{ opacity: 0.6 }}>null</span> : String(v)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </main>
  );
}
