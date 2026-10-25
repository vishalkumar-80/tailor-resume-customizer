"""Generates sample resumes used by the tests and for manual demos."""
from pathlib import Path

from docx import Document
from fpdf import FPDF

HERE = Path(__file__).parent / "fixtures"
LINES = """Priya Sharma
Software Engineer
priya.sharma@example.com | +91 98765 43210 | Bengaluru, India | github.com/priyasharma

SUMMARY
Software engineer with 4 years of experience building web applications. Comfortable across frontend and backend.

SKILLS
JavaScript, React, Node.js, Python, Flask, PostgreSQL, Git, Docker, HTML, CSS, Jira

EXPERIENCE
Software Engineer - Finlytics Pvt Ltd (Bengaluru) | Jan 2022 - Present
- Worked on the customer dashboard used by 40,000 monthly users.
- Built REST APIs in Flask for payments reconciliation, cutting manual work by 30%.
- Wrote unit tests and fixed production bugs.
- Moved the deployment to Docker containers on AWS EC2.
Associate Developer - BrightApps (Pune) | Jul 2020 - Dec 2021
- Developed React components for an e-commerce storefront.
- Helped integrate Razorpay payment gateway.
- Participated in code reviews and sprint planning.

PROJECTS
DocuChat - chatbot that answers questions over PDFs using OpenAI API and FAISS.
- Built ingestion pipeline and a simple React UI.

EDUCATION
B.Tech in Computer Science, VIT Vellore (2016 - 2020), CGPA 8.4
""".strip().splitlines()


def main():
    HERE.mkdir(exist_ok=True)
    doc = Document()
    for line in LINES:
        doc.add_paragraph(line)
    doc.save(HERE / "sample_resume.docx")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    for line in LINES:
        pdf.multi_cell(0, 5, line or " ", new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(HERE / "sample_resume.pdf"))


if __name__ == "__main__":
    main()
