# Tailor — AI Resume Customizer

**Live app:** https://tailor-resume-ai-eight.vercel.app  ·  **API:** https://tailor-resume-api.vercel.app/api/health

Paste a job description, upload a resume (PDF or DOCX), and Tailor uses Google Gemini to re-cut the resume for that role:
it rewrites the summary, highlights matching skills, reorders and rephrases experience bullets in the JD's language, and
suggests missing keywords, without inventing experience. You get a clean on-screen resume, a word-level diff, keyword
match and ATS scores, an optional cover letter, and PDF / DOCX / TXT downloads.

```
frontend/   Next.js 16 (App Router, React 19, Tailwind CSS v4)
backend/    FastAPI (Python) — parsing, prompt engineering, Gemini integration, scoring, DOCX export
```

## Features

**Core (required)**
- Job description textarea with live validation (non-empty, min 100 / max 15,000 chars) and a progress meter
- Resume upload (PDF **and** DOCX) via drag-and-drop or file picker, showing file name, size and type
- Backend text extraction with `pdfplumber` / `python-docx`
- LLM tailoring: summary rewrite, matched-skill highlighting, bullet reordering/rephrasing, missing-keyword suggestions
- Clean resume view with keyword highlights; download as **PDF** (server-rendered, typeset A4), **DOCX** (ATS-friendly, same layout) or **TXT**
- Error handling for invalid file types, oversized files, empty/short input, scanned PDFs, LLM failures, timeouts and rate limits

**Bonus**
- **Match score**: weighted keyword coverage before → after tailoring
- **ATS score**: a 9-point checklist (contact info, sections, action verbs, quantified bullets, length, keyword coverage)
- **Diff view**: word-level diff of the original vs. the tailored resume
- **Multiple versions**: generate up to 5 versions (different tones/sections) and switch between them
- **Section-wise customization**: choose Summary / Skills / Experience / Projects; the rest is kept as-is
- **Tone control**: Balanced, Bold or Concise
- **Cover letter generator**: grounded in the original resume; copy or download
- Light and dark themes; responsive down to 360px

## Tech stack

| Layer    | Technology |
|----------|------------|
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, `diff`, `lucide-react` |
| Backend  | Python 3.12+, FastAPI, Uvicorn, Pydantic v2, httpx, pdfplumber, python-docx, fpdf2 (PDF export, bundled OFL Source Sans 3 / Source Serif 4 fonts) |
| LLM      | Google Gemini via the REST API: **`gemini-3.5-flash`** (thinking level `low`), with automatic fallback to **`gemini-3.5-flash-lite`** |
| Hosting  | Vercel: the Next.js app plus the FastAPI backend as a Python function (a Dockerfile and `render.yaml` are also included for Render / Cloud Run) |

## Architecture

```
┌──────────────────────────── Next.js (Vercel) ────────────────────────────┐
│  JD textarea · resume dropzone · fit options                             │
│  Results: score dials · keyword chips · resume sheet · diff · cover      │
│  Downloads: PDF + DOCX (rendered by API) · TXT (client)                  │
└──────────────┬───────────────────────────────────────────────────────────┘
               │ REST (multipart / JSON), CORS-restricted
┌──────────────▼──────────────── FastAPI (Render) ─────────────────────────┐
│ guard middleware: body-size limit, security headers · per-IP rate limit  │
│ parsing.py   validate ext + MIME + magic bytes, zip-bomb check, page cap │
│ prompts.py   system prompt + JSON response schema (truthfulness rules)   │
│ llm.py       Gemini REST, structured JSON output, retry + model fallback │
│ scoring.py   deterministic keyword match + ATS checklist                 │
│ export.py / pdf_export.py   DOCX and PDF generation                      │
└──────────────┬───────────────────────────────────────────────────────────┘
               │ HTTPS, API key in header
        ┌──────▼──────┐
        │ Gemini API  │
        └─────────────┘
```

**API**

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/api/health` | Liveness and configured model |
| POST | `/api/tailor` | multipart: `job_description`, `resume`, `sections`, `tone` → tailored resume + scores |
| POST | `/api/parse` | multipart: `resume` → extracted text (debug/preview) |
| POST | `/api/cover-letter` | JSON: `job_description`, `resume_text`, `tone` |
| POST | `/api/export/docx` | JSON: `{resume}` → .docx file |
| POST | `/api/export/pdf` | JSON: `{resume}` → .pdf file (A4, selectable text, page numbers) |

### Prompt engineering

- A recruiter-persona **system prompt** with explicit, numbered truthfulness rules: never invent employers, titles,
  dates, metrics or skills; keep every role; keep numbers verbatim; don't add new activities when rephrasing.
- **Terminology mirroring**: use the JD's exact phrase only when the meaning is the same (for example "unit tests" becomes
  "automated tests"), because that is what ATS keyword matching rewards.
- **Structured output**: Gemini's `responseSchema` forces typed JSON (skills with a `matched` flag, experience
  bullets, `jd_keywords` with importance, `missing_keywords` with suggestions, `change_log`), validated again with Pydantic.
- **Prompt-injection hardening**: the JD and resume are wrapped in XML-style tags and declared untrusted data.
- **Scores are not LLM guesses**: the LLM only extracts the JD's keywords. `scoring.py` deterministically checks
  which of them appear in the original and tailored text (with synonyms such as JS ↔ JavaScript and k8s ↔ Kubernetes).

## Run locally

Prerequisites: Python 3.12+ and Node 20+.

```bash
# 1. Backend
cd backend
python -m venv .venv
.venv/Scripts/activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env            # then put your Gemini key in GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000

# 2. Frontend (new terminal)
cd frontend
npm install
cp .env.example .env.local      # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                     # http://localhost:3000
```

Get a free Gemini key at <https://aistudio.google.com/apikey>. Sample files for a quick demo are in
`backend/tests/fixtures/` (`sample_resume.pdf`, `sample_resume.docx`, `sample_jd.txt`).

### Tests and security checks

```bash
cd backend
pip install -r requirements-dev.txt
pytest -q                 # 33 tests; the LLM is mocked
pip-audit -r requirements.txt
bandit -r app
cd ../frontend && npm audit && npm run lint && npx tsc --noEmit
```

## Deploy

The live app runs as two Vercel projects:

| Project | Root | Env vars |
|---------|------|----------|
| `tailor-resume-api` (framework: FastAPI, entry `backend/index.py`) | `backend/` | `GEMINI_API_KEY` (sensitive), `GEMINI_MODEL`, `GEMINI_FALLBACK_MODEL`, `ALLOWED_ORIGINS=https://<web>.vercel.app`, `MAX_UPLOAD_MB=4`, `CLIENT_IP_HEADER=x-real-ip` |
| `tailor-resume-ai` (framework: Next.js) | `frontend/` | `NEXT_PUBLIC_API_URL=https://<api>.vercel.app` |

```bash
cd backend  && vercel deploy --prod
cd frontend && vercel deploy --prod
```

`.vercelignore` files keep `.env`, `.venv`, tests and `node_modules` out of the uploads.
**Alternative:** deploy the backend to Render with `render.yaml` / the Dockerfile, or to Cloud Run with `gcloud run deploy --source backend`.

## Security

- No secrets in code: the API key is read from env vars, `.env` files are gitignored, and only `.env.example` files are committed
- The Gemini key is sent in the `x-goog-api-key` header (never in URLs), and upstream error bodies are never logged or echoed
- Uploads: 4 MB cap (Vercel functions accept bodies up to 4.5 MB) (checked by Content-Length and again on read), extension + MIME + magic-byte validation,
  DOCX zip-bomb protection (uncompressed size and entry count), a 10-page PDF cap, parsing in memory in a worker thread, and no disk writes
- Request-size guard for JSON bodies; chunked POSTs without Content-Length are rejected
- Per-IP rate limiting on the LLM and export endpoints; CORS locked to configured origins; `/docs` is off by default
- Security headers on both apps (CSP, `X-Frame-Options: DENY`, `nosniff`, Referrer-Policy, HSTS on the frontend)
- The frontend renders LLM output as React text nodes only (no `dangerouslySetInnerHTML` for user or LLM content)
- Content-Disposition filenames are sanitised
- Dependency scans are clean at the time of writing: `pip-audit` reports no known vulnerabilities, `npm audit` 0, `bandit` no issues

## Known limitations and trade-offs

- **Scanned (image-only) PDFs** aren't supported, because there is no OCR. Users get a clear error asking for a text-based file.
- **Layout isn't preserved**: the tailored resume is re-rendered in a clean single-column ATS-friendly format,
  not the original design.
- **Rate limiting is in-memory**, so it is per instance and resets on restart. Multi-instance deployments should use Redis or a gateway.
  Behind a proxy, run uvicorn with `--proxy-headers` (the Dockerfile does) so the real client IP is used.
- **No auth or history**: versions live in browser memory and disappear on refresh. This is deliberate, because no resume data is stored.
- **No streaming**: one structured JSON response is more reliable to validate than a partial stream. The UI shows staged progress instead.
- **PDF/DOCX use one fixed, clean template.** They don't reproduce the on-screen highlights or offer template choices.
- The ATS score is a transparent heuristic, not a replica of any specific commercial ATS.
- LLM output can still overstate things. The UI shows a diff and a change log and reminds users to review before sending.
