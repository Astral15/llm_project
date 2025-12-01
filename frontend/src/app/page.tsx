"use client";

import { useEffect, useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { getStructured, uploadImage, type OutputField } from "@/lib/api";

type FieldRow = OutputField & { id: number };

export default function MainPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);

  const [prompt, setPrompt] = useState(
    "Who invented turing machine? return byear and fullname.\nAlso, return what is the number on the shirt the person is wearing on the picture."
  );
  const [fields, setFields] = useState<FieldRow[]>([
    { id: 1, name: "inventorFullName", type: "string" },
    { id: 2, name: "inventorBirthYear", type: "number" },
    { id: 3, name: "numberOnTheShirt", type: "number" },
  ]);

  const [file, setFile] = useState<File | null>(null);
  const [imageId, setImageId] = useState<number | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  const [result, setResult] = useState<
    Record<string, string | number | null> | null
  >(null);
  const [fromCache, setFromCache] = useState(false);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // load token or redirect to /login
  useEffect(() => {
    const t =
      typeof window !== "undefined" ? localStorage.getItem("token") : null;
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
    <main
      style={{
        display: "flex",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 760,
          background: "#ffffff",
          borderRadius: 8,
          boxShadow: "0 10px 30px rgba(15, 23, 42, 0.12)",
          padding: 24,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginBottom: 16,
            alignItems: "center",
          }}
        >
          <h1
            style={{
              fontSize: 24,
              margin: 0,
              fontWeight: 600,
            }}
          >
            Example User Experience
          </h1>
          <button
            type="button"
            onClick={logout}
            style={{
              padding: "4px 10px",
              borderRadius: 4,
              border: "1px solid #d1d5db",
              background: "#ffffff",
              fontSize: 12,
              cursor: "pointer",
            }}
          >
            Logout
          </button>
        </div>

        <form
          onSubmit={onSubmit}
          style={{ display: "flex", flexDirection: "column", gap: 20 }}
        >
          {/* Prompt */}
          <div>
            <label
              style={{
                fontSize: 14,
                fontWeight: 500,
                display: "block",
                marginBottom: 6,
              }}
            >
              Prompt
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={4}
              style={{
                width: "100%",
                padding: 10,
                borderRadius: 4,
                border: "1px solid #d1d5db",
                fontSize: 14,
                resize: "vertical",
              }}
            />
          </div>

          {/* Image upload */}
          <div>
            <label
              style={{
                fontSize: 14,
                fontWeight: 500,
                display: "block",
                marginBottom: 6,
              }}
            >
              Image (optional)
            </label>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
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
                  padding: "6px 12px",
                  borderRadius: 4,
                  border: "none",
                  background: "#3b82f6",
                  color: "#ffffff",
                  fontSize: 13,
                  fontWeight: 500,
                  cursor: !file || uploading ? "default" : "pointer",
                  opacity: !file || uploading ? 0.6 : 1,
                }}
              >
                {uploading ? "Uploading…" : "Upload"}
              </button>
            </div>
            {imageId && (
              <div
                style={{
                  marginTop: 4,
                  fontSize: 12,
                  color: "#6b7280",
                }}
              >
                image uploaded
              </div>
            )}
          </div>

          {/* Response structure */}
          <div>
            <label
              style={{
                fontSize: 14,
                fontWeight: 500,
                display: "block",
                marginBottom: 6,
              }}
            >
              Response Structure
            </label>
            <div
              style={{
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
                    placeholder="fieldName"
                    value={f.name}
                    onChange={(e) =>
                      updateField(f.id, { name: e.target.value })
                    }
                    style={{
                      flex: 2,
                      padding: "6px 8px",
                      borderRadius: 4,
                      border: "1px solid #d1d5db",
                      fontSize: 14,
                    }}
                  />
                  <select
                    value={f.type}
                    onChange={(e) =>
                      updateField(f.id, {
                        type: e.target.value as FieldRow["type"],
                      })
                    }
                    style={{
                      flex: 1,
                      padding: "6px 8px",
                      borderRadius: 4,
                      border: "1px solid #d1d5db",
                      fontSize: 14,
                      background: "#ffffff",
                    }}
                  >
                    <option value="string">String</option>
                    <option value="number">Number</option>
                  </select>
                  <button
                    type="button"
                    onClick={() => removeField(f.id)}
                    style={{
                      padding: "6px 10px",
                      borderRadius: 4,
                      border: "none",
                      background: "#ef4444",
                      color: "#ffffff",
                      fontSize: 12,
                      cursor: "pointer",
                    }}
                  >
                    ×
                  </button>
                </div>
              ))}

              <button
                type="button"
                onClick={addField}
                style={{
                  marginTop: 4,
                  padding: "6px 12px",
                  borderRadius: 4,
                  border: "none",
                  background: "#2563eb",
                  color: "#ffffff",
                  fontSize: 14,
                  fontWeight: 500,
                  cursor: "pointer",
                  alignSelf: "flex-start",
                }}
              >
                + Add Field
              </button>
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            style={{
              marginTop: 8,
              padding: "10px 14px",
              borderRadius: 4,
              border: "none",
              background: "#22c55e",
              color: "#ffffff",
              fontWeight: 600,
              fontSize: 15,
              cursor: loading ? "default" : "pointer",
              opacity: loading ? 0.8 : 1,
            }}
          >
            {loading ? "Submitting…" : "Submit"}
          </button>

          {error && (
            <div
              style={{
                marginTop: 4,
                color: "#b91c1c",
                fontSize: 13,
              }}
            >
              {error}
            </div>
          )}
        </form>

        {/* Structured Output */}
        <div
          style={{
            marginTop: 24,
            padding: 16,
            borderRadius: 4,
            background: "#f9fafb",
            border: "1px solid #e5e7eb",
          }}
        >
          <div
            style={{
              fontWeight: 600,
              marginBottom: 8,
              fontSize: 14,
            }}
          >
            Structured Output:
            {result && (
              <span
                style={{
                  marginLeft: 8,
                  fontWeight: 400,
                  fontSize: 11,
                  color: "#6b7280",
                }}
              >
                {fromCache ? "(from cache)" : "(fresh)"}
              </span>
            )}
          </div>

          {!result && (
            <div style={{ fontSize: 13, color: "#6b7280" }}>
              No response yet. Submit the form to see structured output here.
            </div>
          )}

          {result && (
            <div style={{ fontSize: 14, lineHeight: 1.6 }}>
              {Object.entries(result).map(([k, v]) => (
                <div key={k}>
                  <span style={{ fontWeight: 600 }}>{k}:</span>{" "}
                  {v === null ? (
                    <span style={{ color: "#9ca3af" }}>null</span>
                  ) : (
                    String(v)
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
