"""PDF export of a tailored resume: single column, selectable text, consistent on every device.

Rendered server-side with fpdf2 and bundled OFL fonts (Source Sans 3 / Source Serif 4) so the
output never depends on the browser's print dialog, theme, or installed fonts.
"""

from pathlib import Path

from fpdf import FPDF

from .schemas import TailoredResume

FONTS = Path(__file__).parent / "fonts"

INK = (26, 26, 26)
MUTED = (100, 100, 100)
ACCENT = (190, 58, 38)
RULE = (205, 205, 205)

PAGE_W, MARGIN = 210, 17
CONTENT_W = PAGE_W - 2 * MARGIN
BODY = 10.2
LINE = 4.9


class _ResumePDF(FPDF):
    show_page_numbers = False

    def footer(self):
        if self.show_page_numbers:
            self.set_y(-11)
            self.set_font("sans", "", 7.5)
            self.set_text_color(*MUTED)
            self.cell(0, 4, f"{self.page_no()} / {{nb}}", align="C")


def _clean(text: str) -> str:
    # Normalise whitespace; strip control characters that would render as tofu.
    return " ".join("".join(ch for ch in (text or "") if ch >= " " or ch == "\n").split())


def build_pdf(r: TailoredResume) -> bytes:
    pdf = _render(r, page_numbers=False)
    if pdf.pages_count > 1:
        # Second pass so every page of a multi-page resume gets "n / total".
        pdf = _render(r, page_numbers=True)
    return bytes(pdf.output())


def _render(r: TailoredResume, page_numbers: bool) -> _ResumePDF:
    pdf = _ResumePDF(format="A4")
    pdf.show_page_numbers = page_numbers
    pdf.set_margins(MARGIN, 15, MARGIN)
    pdf.set_auto_page_break(True, margin=16)
    pdf.add_font("sans", "", FONTS / "SourceSans3-Regular.ttf")
    pdf.add_font("sans", "B", FONTS / "SourceSans3-Semibold.ttf")
    pdf.add_font("sans", "I", FONTS / "SourceSans3-It.ttf")
    pdf.add_font("serif", "", FONTS / "SourceSerif4Display-Regular.ttf")
    pdf.set_title(f"{_clean(r.name) or 'Resume'} — Resume")
    pdf.set_author(_clean(r.name))
    pdf.set_creator("Tailor")
    pdf.alias_nb_pages()
    pdf.add_page()

    # --- header -----------------------------------------------------------------------------------
    pdf.set_text_color(*INK)
    pdf.set_font("serif", "", 25)
    pdf.multi_cell(0, 10, _clean(r.name) or "Resume", align="C", new_x="LMARGIN", new_y="NEXT")
    if r.headline:
        pdf.set_font("sans", "", 11)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(0, 5.5, _clean(r.headline), align="C", new_x="LMARGIN", new_y="NEXT")
    if r.contact:
        pdf.ln(0.8)
        pdf.set_font("sans", "", 9)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(0, 4.5, "   |   ".join(_clean(c) for c in r.contact if c.strip()), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_draw_color(*ACCENT)
    pdf.set_line_width(0.5)
    mid = PAGE_W / 2
    pdf.line(mid - 9, pdf.get_y(), mid + 9, pdf.get_y())
    pdf.ln(1)

    def heading(title: str, keep: float = 22):
        # Never leave a heading stranded at the bottom of a page.
        if pdf.get_y() + keep > pdf.page_break_trigger:
            pdf.add_page()
        pdf.ln(4.5)
        pdf.set_font("sans", "B", 9)
        pdf.set_text_color(*ACCENT)
        pdf.set_char_spacing(1.4)
        pdf.cell(0, 5, title.upper(), align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.set_char_spacing(0)
        pdf.set_draw_color(*RULE)
        pdf.set_line_width(0.25)
        pdf.line(MARGIN, pdf.get_y() + 0.6, PAGE_W - MARGIN, pdf.get_y() + 0.6)
        pdf.ln(2.6)
        pdf.set_text_color(*INK)

    def paragraph(text: str, size: float = BODY):
        pdf.set_font("sans", "", size)
        pdf.set_text_color(*INK)
        pdf.multi_cell(0, LINE, _clean(text), align="L", new_x="LMARGIN", new_y="NEXT")

    def bullets(items: list[str]):
        pdf.set_font("sans", "", BODY)
        for b in items:
            b = _clean(b)
            if not b:
                continue
            y = pdf.get_y()
            if y + LINE > pdf.page_break_trigger:
                pdf.add_page()
                y = pdf.get_y()
            pdf.set_text_color(*MUTED)
            pdf.set_xy(MARGIN + 1.2, y)
            pdf.cell(4, LINE, "•")
            pdf.set_text_color(*INK)
            pdf.set_xy(MARGIN + 5, y)
            pdf.multi_cell(CONTENT_W - 5, LINE, b, align="L", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(0.7)

    def title_row(left_bold: str, left_rest: str, right: str):
        """Bold title + muted subtitle on the left, muted meta right-aligned on the same line (wraps if needed)."""
        left_bold, left_rest, right = _clean(left_bold), _clean(left_rest), _clean(right)
        pdf.set_font("sans", "", 9)
        right_w = pdf.get_string_width(right) + 2 if right else 0
        pdf.set_font("sans", "B", BODY + 0.6)
        bold_w = pdf.get_string_width(left_bold)
        pdf.set_font("sans", "", BODY + 0.2)
        rest_txt = f"  ·  {left_rest}" if left_rest else ""
        rest_w = pdf.get_string_width(rest_txt)
        one_line = bold_w + rest_w + right_w <= CONTENT_W
        if one_line:
            needed = 5.6
        else:
            pdf.set_font("sans", "B", BODY + 0.6)
            lines = pdf.multi_cell(0, 5.4, left_bold + rest_txt, dry_run=True, output="LINES")
            needed = 5.4 * len(lines) + (4.6 if right else 0)
        if pdf.get_y() + needed + LINE > pdf.page_break_trigger:
            pdf.add_page()

        if one_line:
            pdf.set_font("sans", "B", BODY + 0.6)
            pdf.set_text_color(*INK)
            pdf.cell(bold_w, 5.4, left_bold)
            if rest_txt:
                pdf.set_font("sans", "", BODY + 0.2)
                pdf.set_text_color(*MUTED)
                pdf.cell(rest_w, 5.4, rest_txt)
            if right:
                pdf.set_font("sans", "", 9)
                pdf.set_text_color(*MUTED)
                pdf.set_x(PAGE_W - MARGIN - right_w)
                pdf.cell(right_w, 5.4, right, align="R")
            pdf.ln(5.6)
        else:
            pdf.set_font("sans", "B", BODY + 0.6)
            pdf.set_text_color(*INK)
            pdf.multi_cell(0, 5.4, left_bold + rest_txt, align="L", new_x="LMARGIN", new_y="NEXT")
            if right:
                pdf.set_font("sans", "", 9)
                pdf.set_text_color(*MUTED)
                pdf.cell(0, 4.6, right, align="L", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(0.4)

    # --- sections ---------------------------------------------------------------------------------
    if r.summary.strip():
        heading("Summary")
        paragraph(r.summary)

    if r.skills:
        heading("Skills")
        paragraph("  ·  ".join(_clean(s.name) for s in r.skills if s.name.strip()))

    if r.experience:
        heading("Experience", keep=30)
        for i, e in enumerate(r.experience):
            if i:
                pdf.ln(2.2)
            title_row(e.title, e.company, " · ".join(x for x in [e.location, e.dates] if x.strip()))
            bullets(e.bullets)

    if r.projects:
        heading("Projects", keep=26)
        for i, p in enumerate(r.projects):
            if i:
                pdf.ln(1.8)
            title_row(p.name, "", "")
            if p.details.strip():
                pdf.set_font("sans", "I", BODY)
                pdf.set_text_color(*MUTED)
                pdf.multi_cell(0, LINE, _clean(p.details), align="L", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(0.6)
            bullets(p.bullets)

    if r.education:
        heading("Education")
        for ed in r.education:
            title_row(ed.degree, ed.institution, ed.dates)
            if ed.details.strip():
                pdf.set_font("sans", "", BODY - 0.4)
                pdf.set_text_color(*MUTED)
                pdf.multi_cell(0, LINE, _clean(ed.details), align="L", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

    if r.certifications:
        heading("Certifications")
        bullets(r.certifications)

    for s in r.other_sections:
        if s.items:
            heading(_clean(s.heading) or "Additional")
            bullets(s.items)

    return pdf
