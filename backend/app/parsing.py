"""Resume text extraction for PDF and DOCX uploads.

Files are never written to disk: they are validated by size, extension and magic
bytes, then parsed from memory. DOCX archives are checked for zip bombs before
python-docx touches them.
"""

import io
import logging
import re
import zipfile

import pdfplumber
from docx import Document

log = logging.getLogger(__name__)

PDF_MAGIC = b"%PDF-"
ZIP_MAGIC = b"PK\x03\x04"
MAX_DOCX_UNCOMPRESSED = 40 * 1024 * 1024
MAX_DOCX_ENTRIES = 2_000

ALLOWED = {
    ".pdf": {"application/pdf", "application/x-pdf", "application/octet-stream", ""},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
        "application/zip",
        "",
    },
}


class ResumeParseError(ValueError):
    """A user-facing problem with the uploaded file."""


def file_kind(filename: str, content_type: str | None, data: bytes) -> str:
    name = (filename or "").lower().strip()
    ext = next((e for e in ALLOWED if name.endswith(e)), None)
    if ext is None:
        raise ResumeParseError("Unsupported file type. Please upload a PDF or DOCX resume.")
    if (content_type or "").split(";")[0].strip().lower() not in ALLOWED[ext]:
        raise ResumeParseError("The file's content type does not match its extension.")
    if ext == ".pdf" and not data.startswith(PDF_MAGIC):
        raise ResumeParseError("This file is not a valid PDF.")
    if ext == ".docx" and not data.startswith(ZIP_MAGIC):
        raise ResumeParseError("This file is not a valid DOCX document.")
    return ext[1:]


def _clean(text: str) -> str:
    text = text.replace("\x00", "").replace("\r", "\n")
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.strip() for line in text.split("\n")).strip()


def _extract_pdf(data: bytes, max_pages: int) -> str:
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            if len(pdf.pages) > max_pages:
                raise ResumeParseError(f"Resume is too long — please keep it under {max_pages} pages.")
            return "\n".join((page.extract_text() or "") for page in pdf.pages)
    except ResumeParseError:
        raise
    except Exception as exc:  # pdfminer raises many exception types for broken/encrypted files
        log.info("PDF parse failure: %s", type(exc).__name__)
        raise ResumeParseError("Could not read this PDF. It may be corrupted or password-protected.") from exc


def _extract_docx(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            infos = zf.infolist()
            if len(infos) > MAX_DOCX_ENTRIES or sum(i.file_size for i in infos) > MAX_DOCX_UNCOMPRESSED:
                raise ResumeParseError("This DOCX file is unusually large once unpacked and was rejected.")
            if "word/document.xml" not in zf.namelist():
                raise ResumeParseError("This file is not a valid DOCX document.")
        doc = Document(io.BytesIO(data))
    except ResumeParseError:
        raise
    except Exception as exc:
        log.info("DOCX parse failure: %s", type(exc).__name__)
        raise ResumeParseError("Could not read this DOCX file. It may be corrupted.") from exc

    lines = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            cells = []
            for cell in row.cells:
                if cell.text.strip() and cell.text not in cells:
                    cells.append(cell.text.strip())
            lines.append(" | ".join(cells))
    return "\n".join(lines)


def extract_resume_text(filename: str, content_type: str | None, data: bytes, *, max_pages: int, max_chars: int) -> tuple[str, str]:
    """Return (kind, text) or raise ResumeParseError."""
    if not data:
        raise ResumeParseError("The uploaded file is empty.")
    kind = file_kind(filename, content_type, data)
    raw = _extract_pdf(data, max_pages) if kind == "pdf" else _extract_docx(data)
    text = _clean(raw)
    if len(text) < 50:
        raise ResumeParseError(
            "We couldn't find enough text in this resume. If it's a scanned image, please upload a text-based PDF or DOCX."
        )
    return kind, text[:max_chars]
