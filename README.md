# LLM Structured Output App

Prompt + optional image → structured JSON fields, over a small full-stack app.

- Backend: FastAPI + Postgres + MinIO (S3-compatible) + Google Gemini
- Frontend: Next.js (app router) + React
- Auth: JWT (username / password)
- Extras: query caching, per-user image deduplication
- Deployment: `docker compose up --build` from repo root

---

## 1. What this app does

User flow:

1. Register with username + password + confirmation.
2. Log in → get redirected to the main page.
3. Type a prompt (e.g. “Who invented the Turing machine?”).
4. Optionally upload an image (goes to MinIO, deduplicated by content hash).
5. Define response structure:
   - Arbitrary field names.
   - Each field type: `"string"` or `"number"`.
6. Hit submit → backend calls Gemini with a strict response schema.
7. UI renders the returned JSON and marks whether it came from cache.

---

## 2. Quickstart (Docker)

Requirements:

- Docker
- Docker Compose
- A valid `GEMINI_API_KEY` (Google AI Studio / Vertex Gemini)

Steps:

```bash
# from repo root
cp .env.example .env
# edit .env and put your real GEMINI_API_KEY

# first build docker
docker compose up --build

- for frontend use http://localhost:3000
- Backend: http://localhost:8000
- MinIO: http://localhost:9000  password and user both minioadmin