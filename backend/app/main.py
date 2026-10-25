import logging
import re
import time
import unicodedata
from collections import defaultdict, deque
from threading import Lock
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError

from .config import Settings, get_settings
from .export import build_docx
from .llm import LLMError, generate_json
from .pdf_export import build_pdf
from .parsing import ResumeParseError, extract_resume_text
from .prompts import COVER_SCHEMA, COVER_SYSTEM, TAILOR_SCHEMA, TAILOR_SYSTEM, cover_user_prompt, tailor_user_prompt
from .schemas import (
    CoverLetterRequest,
    CoverLetterResponse,
    ExportRequest,
    Keyword,
    MissingKeyword,
    Scores,
    TailoredResume,
    TailorResponse,
)
from .scoring import ats_score, match_score, resume_to_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("resume-api")

settings = get_settings()
app = FastAPI(
    title="Tailor — Resume Customizer API",
    version="1.0.0",
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    max_age=600,
)


@app.middleware("http")
async def guard(request: Request, call_next):
    # Reject oversized bodies early, before multipart/JSON parsing.
    limit = settings.max_upload_bytes + 64 * 1024
    if request.headers.get("content-type", "").startswith("application/json"):
        limit = settings.max_json_body_kb * 1024
    try:
        length = int(request.headers.get("content-length") or 0)
    except ValueError:
        return JSONResponse({"detail": "Invalid Content-Length header."}, status_code=400)
    if length > limit:
        return JSONResponse({"detail": "Request is too large."}, status_code=413)
    # Chunked bodies have no Content-Length and would bypass the check above.
    if request.method == "POST" and "content-length" not in request.headers:
        return JSONResponse({"detail": "Content-Length header is required."}, status_code=411)

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    return response


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first.get("loc", [])[1:]) or "request"
    return JSONResponse({"detail": f"Invalid {field}: {first.get('msg', 'bad value')}"}, status_code=422)


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    log.exception("Unhandled error: %s", type(exc).__name__)
    return JSONResponse({"detail": "Something went wrong on our side. Please try again."}, status_code=500)


# --- rate limiting ---------------------------------------------------------------------------------
_hits: dict[str, deque] = defaultdict(deque)
_hits_lock = Lock()


def _client_ip(request: Request) -> str:
    # Only trust a forwarding header when the platform sets it (e.g. Vercel's x-real-ip); otherwise use the socket peer.
    if settings.client_ip_header and (ip := request.headers.get(settings.client_ip_header)):
        return ip.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate(request: Request, bucket: str, per_minute: int) -> None:
    key = f"{bucket}:{_client_ip(request)}"
    now = time.monotonic()
    with _hits_lock:
        q = _hits[key]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= per_minute:
            raise HTTPException(429, "Too many requests — please wait a minute and try again.")
        q.append(now)
        if len(_hits) > 10_000:  # keep memory bounded
            for k in [k for k, v in _hits.items() if not v or now - v[-1] > 60]:
                del _hits[k]


def rate_limit(request: Request, s: Annotated[Settings, Depends(get_settings)]) -> None:
    """Budget for endpoints that call the LLM or parse uploads."""
    _check_rate(request, "llm", s.rate_limit_per_minute)


def export_rate_limit(request: Request, s: Annotated[Settings, Depends(get_settings)]) -> None:
    """Separate, larger budget so downloads never eat into the LLM allowance."""
    _check_rate(request, "export", s.export_rate_limit_per_minute)


# --- helpers ---------------------------------------------------------------------------------------
def clean_jd(jd: str, s: Settings) -> str:
    jd = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", jd or "").strip()
    if not jd:
        raise HTTPException(422, "Please paste the job description.")
    if len(jd) < s.min_jd_chars:
        raise HTTPException(422, f"The job description looks too short — paste at least {s.min_jd_chars} characters.")
    if len(jd) > s.max_jd_chars:
        raise HTTPException(422, f"The job description is too long (max {s.max_jd_chars:,} characters).")
    return jd


async def read_upload(file: UploadFile, s: Settings) -> bytes:
    data = await file.read(s.max_upload_bytes + 1)
    if len(data) > s.max_upload_bytes:
        raise HTTPException(413, f"File is too large. Maximum size is {s.max_upload_mb:g} MB.")
    return data


# --- routes ----------------------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    return {"status": "ok", "model": settings.gemini_model, "llm_configured": bool(settings.gemini_api_key.get_secret_value())}


@app.post("/api/parse")
async def parse_resume(
    s: Annotated[Settings, Depends(get_settings)],
    _: Annotated[None, Depends(rate_limit)],
    resume: UploadFile = File(...),
):
    """Parse only — lets the UI preview extracted text before spending an LLM call."""
    data = await read_upload(resume, s)
    try:
        kind, text = await run_in_threadpool(
            extract_resume_text,
            resume.filename or "",
            resume.content_type,
            data,
            max_pages=s.max_pdf_pages,
            max_chars=s.max_resume_chars,
        )
    except ResumeParseError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"kind": kind, "text": text, "chars": len(text)}


@app.post("/api/tailor", response_model=TailorResponse)
async def tailor(
    s: Annotated[Settings, Depends(get_settings)],
    _: Annotated[None, Depends(rate_limit)],
    job_description: str = Form("", max_length=20_000),
    resume: UploadFile = File(...),
    sections: str = Form("summary,skills,experience,projects", max_length=100),
    tone: str = Form("balanced", max_length=20),
):
    jd = clean_jd(job_description, s)
    chosen = [x for x in ("summary", "skills", "experience", "projects") if x in {p.strip() for p in sections.split(",")}]
    if not chosen:
        raise HTTPException(422, "Select at least one section to customize.")
    if tone not in ("balanced", "bold", "concise"):
        tone = "balanced"

    data = await read_upload(resume, s)
    try:
        kind, original = await run_in_threadpool(
            extract_resume_text,
            resume.filename or "",
            resume.content_type,
            data,
            max_pages=s.max_pdf_pages,
            max_chars=s.max_resume_chars,
        )
    except ResumeParseError as exc:
        raise HTTPException(422, str(exc)) from exc

    try:
        raw, model = await generate_json(
            s, system=TAILOR_SYSTEM, user=tailor_user_prompt(jd, original, chosen, tone), schema=TAILOR_SCHEMA
        )
        tailored = TailoredResume.model_validate(raw)
        keywords = [Keyword.model_validate(k) for k in raw.get("jd_keywords", [])][:30]
        missing = [MissingKeyword.model_validate(k) for k in raw.get("missing_keywords", [])][:20]
    except LLMError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc
    except ValidationError as exc:
        log.warning("LLM output failed validation: %s", exc.error_count())
        raise HTTPException(502, "The AI returned an unexpected format. Please try again.") from exc

    tailored_text = resume_to_text(tailored)
    before, found_before = match_score(keywords, original)
    after, found_after = match_score(keywords, tailored_text)
    ats, checks = ats_score(tailored, after)

    # Recompute which "missing" keywords are truly absent from the tailored resume.
    missing = [m for m in missing if m.keyword not in found_after]

    return TailorResponse(
        resume=tailored,
        tailored_text=tailored_text,
        original_text=original,
        jd_keywords=keywords,
        missing_keywords=missing,
        change_log=[str(c) for c in raw.get("change_log", [])][:10],
        scores=Scores(
            match_before=before,
            match_after=after,
            ats=ats,
            ats_checks=checks,
            keywords_found_before=found_before,
            keywords_found_after=found_after,
        ),
        model=model,
        file={"name": resume.filename, "kind": kind, "size": len(data)},
    )


@app.post("/api/cover-letter", response_model=CoverLetterResponse)
async def cover_letter(
    body: CoverLetterRequest,
    s: Annotated[Settings, Depends(get_settings)],
    _: Annotated[None, Depends(rate_limit)],
):
    jd = clean_jd(body.job_description, s)
    try:
        raw, model = await generate_json(
            s, system=COVER_SYSTEM, user=cover_user_prompt(jd, body.resume_text, body.tone), schema=COVER_SCHEMA, temperature=0.6
        )
    except LLMError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc
    return CoverLetterResponse(subject=str(raw.get("subject", "")), letter=str(raw.get("letter", "")), model=model)


def _attachment(data: bytes, resume: TailoredResume, ext: str, media_type: str) -> Response:
    # Filename is reduced to [A-Za-z0-9_] so nothing can break out of the header.
    ascii_name = unicodedata.normalize("NFKD", resume.name or "").encode("ascii", "ignore").decode()
    slug = re.sub(r"[^A-Za-z0-9]+", "_", ascii_name).strip("_")[:40] or "resume"
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{slug}_tailored.{ext}"'},
    )


@app.post("/api/export/docx")
async def export_docx(body: ExportRequest, _: Annotated[None, Depends(export_rate_limit)]):
    data = await run_in_threadpool(build_docx, body.resume)
    return _attachment(data, body.resume, "docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@app.post("/api/export/pdf")
async def export_pdf(body: ExportRequest, _: Annotated[None, Depends(export_rate_limit)]):
    data = await run_in_threadpool(build_pdf, body.resume)
    return _attachment(data, body.resume, "pdf", "application/pdf")
