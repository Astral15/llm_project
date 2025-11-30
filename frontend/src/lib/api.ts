const B = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

type FieldType = "string" | "number";

export type OutputField = {
  name: string;
  type: FieldType;
};

export type StructuredRequest = {
  prompt: string;
  fields: OutputField[];
  image_id: number | null;
};

export type StructuredResponse = {
  data: Record<string, string | number | null>;
  from_cache: boolean;
};

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) msg = Array.isArray(body.detail) ? body.detail[0].msg ?? msg : body.detail;
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

export async function login(username: string, password: string): Promise<string> {
  const body = new URLSearchParams();
  body.append("username", username);
  body.append("password", password);

  const res = await fetch(`${B}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  const data = await j<{ access_token: string }>(res);
  return data.access_token;
}

export async function register(
  username: string,
  password: string,
  password_confirm: string
): Promise<void> {
  const res = await fetch(`${B}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, password_confirm }),
  });
  await j(res);
}

export async function uploadImage(file: File, token: string): Promise<{ id: number; url: string }> {
  const fd = new FormData();
  fd.append("file", file);

  const res = await fetch(`${B}/images/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: fd,
  });

  return j<{ id: number; url: string }>(res);
}

export async function getStructured(
  body: StructuredRequest,
  token: string
): Promise<StructuredResponse> {
  const res = await fetch(`${B}/llm/structured`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });

  return j<StructuredResponse>(res);
}
