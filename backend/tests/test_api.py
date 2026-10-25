import io
import zipfile

import httpx
import pytest
from fastapi.testclient import TestClient

from app import llm, main
from app.config import Settings
from app.parsing import ResumeParseError, extract_resume_text
from app.schemas import Keyword
from app.scoring import keyword_present, match_score, _norm

from .conftest import FIXTURES

JD = (FIXTURES / "sample_jd.txt").read_text(encoding="utf-8")
PDF = (FIXTURES / "sample_resume.pdf").read_bytes()
DOCX = (FIXTURES / "sample_resume.docx").read_bytes()
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

FAKE_LLM = {
    "name": "Priya Sharma",
    "headline": "Software Engineer",
    "contact": ["priya.sharma@example.com"],
    "summary": "Software engineer with 4 years building React and Python web apps, REST APIs and Docker deployments on AWS.",
    "skills": [{"name": "React", "matched": True}, {"name": "Python", "matched": True}, {"name": "Jira", "matched": False}],
    "experience": [
        {"title": "Software Engineer", "company": "Finlytics", "dates": "2022 - Present", "bullets": ["Built REST APIs in Flask, cutting manual work by 30%."]}
    ],
    "education": [{"degree": "B.Tech", "institution": "VIT"}],
    "jd_keywords": [
        {"keyword": "React", "importance": "high"},
        {"keyword": "REST APIs", "importance": "high"},
        {"keyword": "Kubernetes", "importance": "medium"},
    ],
    "missing_keywords": [{"keyword": "Kubernetes", "suggestion": "Add if true."}, {"keyword": "React", "suggestion": "x"}],
    "change_log": ["Rewrote summary"],
}


@pytest.fixture
def client(monkeypatch):
    async def fake_generate(settings, **kwargs):
        if "cover" in kwargs["system"].lower():
            return {"subject": "Application", "letter": "Dear team,\n\nHello."}, "fake-model"
        return FAKE_LLM, "fake-model"

    monkeypatch.setattr(main, "generate_json", fake_generate)
    main._hits.clear()
    return TestClient(main.app)


def post_tailor(client, data=PDF, name="resume.pdf", mime="application/pdf", jd=JD, **form):
    return client.post(
        "/api/tailor",
        data={"job_description": jd, **form},
        files={"resume": (name, data, mime)},
    )


# --- parsing --------------------------------------------------------------------------------------
def test_parse_pdf_and_docx():
    for name, data, mime in [("r.pdf", PDF, "application/pdf"), ("r.docx", DOCX, DOCX_MIME)]:
        kind, text = extract_resume_text(name, mime, data, max_pages=10, max_chars=30000)
        assert kind == name.split(".")[1]
        assert "Priya Sharma" in text and "Finlytics" in text


@pytest.mark.parametrize(
    "name,data,mime,msg",
    [
        ("resume.txt", b"hello", "text/plain", "Unsupported"),
        ("resume.exe", b"MZ", "application/octet-stream", "Unsupported"),
        ("resume.pdf", b"not a pdf at all", "application/pdf", "not a valid PDF"),
        ("resume.docx", b"%PDF-1.4 fake", DOCX_MIME, "not a valid DOCX"),
        ("resume.pdf", PDF, "text/html", "content type"),
        ("resume.pdf", b"", "application/pdf", "empty"),
        ("resume.pdf", b"%PDF-1.4\n garbage", "application/pdf", "Could not read"),
    ],
)
def test_parse_rejects_bad_files(name, data, mime, msg):
    with pytest.raises(ResumeParseError, match=msg):
        extract_resume_text(name, mime, data, max_pages=10, max_chars=30000)


def test_docx_zip_bomb_rejected():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("word/document.xml", "<w/>")
        zf.writestr("big.bin", b"\0" * (45 * 1024 * 1024))  # compresses to a few KB
    with pytest.raises(ResumeParseError, match="unusually large"):
        extract_resume_text("r.docx", DOCX_MIME, buf.getvalue(), max_pages=10, max_chars=30000)


def test_pdf_page_limit():
    with pytest.raises(ResumeParseError, match="pages"):
        extract_resume_text("r.pdf", "application/pdf", PDF, max_pages=0, max_chars=30000)


# --- scoring --------------------------------------------------------------------------------------
def test_keyword_matching_boundaries_and_synonyms():
    t = _norm("Built APIs with JS, k8s and Postgres. Java developer.")
    assert keyword_present("JavaScript", t)
    assert keyword_present("Kubernetes", t)
    assert keyword_present("PostgreSQL", t)
    assert keyword_present("API", t)  # plural
    assert not keyword_present("Go", _norm("Google cloud and Django"))
    assert not keyword_present("C", _norm("CSS and C# code"))


def test_match_score_weighted():
    kws = [Keyword(keyword="React", importance="high"), Keyword(keyword="Redis", importance="low")]
    score, found = match_score(kws, "React developer")
    assert found == ["React"] and score == 75


# --- API ------------------------------------------------------------------------------------------
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    assert "test-key" not in r.text
    assert r.headers["x-content-type-options"] == "nosniff"


def test_tailor_happy_path(client):
    r = post_tailor(client)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["resume"]["name"] == "Priya Sharma"
    assert body["scores"]["match_after"] >= body["scores"]["match_before"]
    # "React" is found in the tailored text, so it must be dropped from missing keywords
    assert [m["keyword"] for m in body["missing_keywords"]] == ["Kubernetes"]
    assert body["file"] == {"name": "resume.pdf", "kind": "pdf", "size": len(PDF)}
    assert "SUMMARY" in body["tailored_text"]


def test_tailor_docx(client):
    assert post_tailor(client, DOCX, "r.docx", DOCX_MIME).status_code == 200


@pytest.mark.parametrize(
    "jd,status,msg",
    [("", 422, "job description"), ("   ", 422, "job description"), ("too short", 422, "too short"), ("x" * 15_001, 422, "too long")],
)
def test_tailor_jd_validation(client, jd, status, msg):
    r = post_tailor(client, jd=jd)
    assert r.status_code == status
    assert msg in r.json()["detail"].lower()


def test_tailor_bad_file_type(client):
    r = post_tailor(client, b"hello", "notes.txt", "text/plain")
    assert r.status_code == 422 and "PDF or DOCX" in r.json()["detail"]


def test_tailor_no_sections(client):
    r = post_tailor(client, sections="bogus")
    assert r.status_code == 422 and "section" in r.json()["detail"]


def test_tailor_file_too_large(client, monkeypatch):
    s = Settings(max_upload_mb=0.001)
    main.app.dependency_overrides[main.get_settings] = lambda: s
    try:
        r = post_tailor(client)
        assert r.status_code == 413
    finally:
        main.app.dependency_overrides.clear()


def test_request_too_large_by_header(client):
    r = client.post("/api/export/docx", content=b"{}", headers={"Content-Type": "application/json", "Content-Length": str(10**7)})
    assert r.status_code == 413


def test_rate_limit(client):
    s = Settings(rate_limit_per_minute=2)
    main.app.dependency_overrides[main.get_settings] = lambda: s
    try:
        codes = [post_tailor(client).status_code for _ in range(3)]
        assert codes == [200, 200, 429]
    finally:
        main.app.dependency_overrides.clear()


def test_llm_failure_is_graceful(client, monkeypatch):
    async def boom(settings, **kwargs):
        raise llm.LLMError("The AI service is busy right now (rate limited). Please try again in a minute.", 503)

    monkeypatch.setattr(main, "generate_json", boom)
    r = post_tailor(client)
    assert r.status_code == 503 and "busy" in r.json()["detail"]


def test_llm_malformed_output(client, monkeypatch):
    async def weird(settings, **kwargs):
        return {"skills": "not-a-list"}, "m"

    monkeypatch.setattr(main, "generate_json", weird)
    r = post_tailor(client)
    assert r.status_code == 502 and "unexpected format" in r.json()["detail"]


def test_cover_letter(client):
    r = client.post("/api/cover-letter", json={"job_description": JD, "resume_text": "Priya, engineer", "tone": "bold"})
    assert r.status_code == 200 and r.json()["letter"].startswith("Dear")
    bad = client.post("/api/cover-letter", json={"job_description": JD, "resume_text": "x", "tone": "evil"})
    assert bad.status_code == 422


def test_export_docx(client):
    r = client.post("/api/export/docx", json={"resume": FAKE_LLM | {"name": 'Priya"; rm -rf /'}})
    assert r.status_code == 200
    assert r.content.startswith(b"PK")
    # filename is sanitised (no quotes / injection into the header)
    assert r.headers["content-disposition"] == 'attachment; filename="Priya_rm_rf_tailored.docx"'


def test_cors_only_allows_configured_origin(client):
    ok = client.options("/api/health", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
    bad = client.options("/api/health", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "access-control-allow-origin" not in bad.headers


def test_docs_disabled_by_default(client):
    assert client.get("/docs").status_code == 404 or main.settings.enable_docs


# --- LLM client -----------------------------------------------------------------------------------
@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_llm_fallback_and_errors(anyio_backend, monkeypatch):
    monkeypatch.setattr(llm.asyncio, "sleep", lambda *_: _noop())
    calls = []

    def handler(request: httpx.Request):
        model = request.url.path.split("/")[-1].split(":")[0]
        calls.append(model)
        assert request.headers["x-goog-api-key"] == "k"
        assert "key=" not in str(request.url)  # key never in URL
        if model == "primary":
            return httpx.Response(404)
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}]})

    s = Settings(gemini_api_key="k", gemini_model="primary", gemini_fallback_model="backup")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        data, model = await llm.generate_json(s, system="s", user="u", schema={}, client=c)
    assert data == {"ok": True} and model == "backup"
    assert calls == ["primary", "backup"]  # 404 model is not retried

    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(429))) as c:
        with pytest.raises(llm.LLMError, match="busy"):
            await llm.generate_json(s, system="s", user="u", schema={}, client=c)

    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(403))) as c:
        with pytest.raises(llm.LLMError, match="credentials"):
            await llm.generate_json(s, system="s", user="u", schema={}, client=c)

    with pytest.raises(llm.LLMError, match="missing"):
        await llm.generate_json(Settings(gemini_api_key=""), system="s", user="u", schema={})


async def _noop():
    return None


def test_chunked_post_without_length_rejected(client):
    def gen():
        yield b'{"resume": {}}'

    r = client.post("/api/export/docx", content=gen(), headers={"Content-Type": "application/json"})
    assert r.status_code == 411


def test_export_pdf(client):
    from pypdf import PdfReader

    long = FAKE_LLM | {"experience": FAKE_LLM["experience"] * 25, "name": "Zoë Ñúñez"}
    r = client.post("/api/export/pdf", json={"resume": long})
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    assert r.headers["content-disposition"] == 'attachment; filename="Zoe_Nunez_tailored.pdf"'
    reader = PdfReader(io.BytesIO(r.content))
    assert len(reader.pages) >= 2
    text = reader.pages[0].extract_text()
    assert "Zoë Ñúñez" in text and "SUMMARY" in text and "1 / " in text  # unicode + page numbers


def test_exports_have_separate_rate_budget(client):
    s = Settings(rate_limit_per_minute=1, export_rate_limit_per_minute=3)
    main.app.dependency_overrides[main.get_settings] = lambda: s
    try:
        assert post_tailor(client).status_code == 200
        assert post_tailor(client).status_code == 429  # LLM budget spent
        codes = [client.post("/api/export/pdf", json={"resume": FAKE_LLM}).status_code for _ in range(4)]
        assert codes == [200, 200, 200, 429]  # downloads still work, with their own cap
    finally:
        main.app.dependency_overrides.clear()
