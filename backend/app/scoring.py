"""Deterministic scoring so the numbers shown to users are reproducible, not LLM guesses.

The LLM extracts the JD's important keywords; this module checks which of them
actually appear in the original vs. tailored resume text, and runs a heuristic
ATS-readiness checklist on the tailored resume.
"""

import re

from .schemas import Keyword, TailoredResume

WEIGHTS = {"high": 3, "medium": 2, "low": 1}

# Common equivalents so "JS" in a resume counts for "JavaScript" in a JD, etc.
SYNONYMS = {
    "javascript": ["js", "ecmascript"],
    "typescript": ["ts"],
    "kubernetes": ["k8s"],
    "postgresql": ["postgres"],
    "amazon web services": ["aws"],
    "aws": ["amazon web services"],
    "google cloud platform": ["gcp", "google cloud"],
    "gcp": ["google cloud platform", "google cloud"],
    "machine learning": ["ml"],
    "artificial intelligence": ["ai"],
    "continuous integration": ["ci/cd", "ci"],
    "ci/cd": ["continuous integration", "continuous delivery", "ci cd"],
    "node.js": ["node", "nodejs"],
    "react": ["react.js", "reactjs"],
    "next.js": ["nextjs"],
    "rest api": ["restful", "rest apis", "rest"],
}


def _norm(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9+#./]+", " ", text.lower()) + " "


def _variants(keyword: str) -> list[str]:
    k = keyword.lower().strip()
    out = {k, k.replace("-", " "), k.replace(".", "")}
    out.update(SYNONYMS.get(k, []))
    return [v for v in out if v]


def keyword_present(keyword: str, normalized_text: str) -> bool:
    for v in _variants(keyword):
        token = _norm(v).strip()
        # Allow a simple plural ("API" ↔ "APIs") without matching inside other words.
        pattern = r"(?<![a-z0-9+#])" + re.escape(token) + r"(?:s|es)?(?![a-z0-9+#])"
        if token and re.search(pattern, normalized_text):
            return True
    return False


def match_score(keywords: list[Keyword], text: str) -> tuple[int, list[str]]:
    if not keywords:
        return 0, []
    norm = _norm(text)
    total = found_weight = 0
    found: list[str] = []
    for kw in keywords:
        w = WEIGHTS.get(kw.importance, 2)
        total += w
        if keyword_present(kw.keyword, norm):
            found_weight += w
            found.append(kw.keyword)
    return round(100 * found_weight / total), found


ACTION_VERBS = {
    "led", "built", "designed", "developed", "implemented", "launched", "improved", "reduced", "increased",
    "created", "managed", "delivered", "automated", "optimized", "architected", "drove", "owned", "migrated",
    "scaled", "shipped", "mentored", "analyzed", "streamlined", "established", "spearheaded", "engineered",
    "collaborated", "coordinated", "achieved", "integrated", "deployed", "maintained", "partnered", "wrote",
}


def ats_score(resume: TailoredResume, match_after: int) -> tuple[int, list[dict]]:
    bullets = [b for e in resume.experience for b in e.bullets] + [b for p in resume.projects for b in p.bullets]
    contact = " ".join(resume.contact)
    words = len(resume_to_text(resume).split())
    verb_led = sum(1 for b in bullets if b.split() and b.split()[0].lower().strip(",.") in ACTION_VERBS)
    quantified = sum(1 for b in bullets if re.search(r"\d", b))

    checks = [
        ("Contact details present", bool(re.search(r"@|\+?\d[\d\s().-]{7,}", contact)), 10),
        ("Professional summary", len(resume.summary.split()) >= 20, 10),
        ("Dedicated skills section", len(resume.skills) >= 5, 10),
        ("Experience with dated roles", bool(resume.experience) and all(e.dates for e in resume.experience), 10),
        ("Education listed", bool(resume.education), 5),
        ("Bullets start with action verbs", bool(bullets) and verb_led / len(bullets) >= 0.6, 10),
        ("Achievements are quantified", bool(bullets) and quantified / len(bullets) >= 0.3, 10),
        ("Healthy length (300–1000 words)", 300 <= words <= 1000, 10),
        ("Strong keyword coverage (≥ 60%)", match_after >= 60, 25),
    ]
    score = sum(w for _, ok, w in checks if ok)
    return score, [{"label": label, "passed": bool(ok)} for label, ok, _ in checks]


def resume_to_text(r: TailoredResume) -> str:
    """Plain-text rendering used for downloads, diffing and scoring."""
    out: list[str] = []
    if r.name:
        out.append(r.name)
    if r.headline:
        out.append(r.headline)
    if r.contact:
        out.append(" | ".join(r.contact))
    if r.summary:
        out += ["", "SUMMARY", r.summary]
    if r.skills:
        out += ["", "SKILLS", ", ".join(s.name for s in r.skills)]
    if r.experience:
        out += ["", "EXPERIENCE"]
        for e in r.experience:
            head = " — ".join(x for x in [e.title, e.company] if x)
            meta = " | ".join(x for x in [e.location, e.dates] if x)
            out.append(head + (f" ({meta})" if meta else ""))
            out += [f"• {b}" for b in e.bullets]
    if r.projects:
        out += ["", "PROJECTS"]
        for p in r.projects:
            out.append(p.name + (f" — {p.details}" if p.details else ""))
            out += [f"• {b}" for b in p.bullets]
    if r.education:
        out += ["", "EDUCATION"]
        for ed in r.education:
            line = ", ".join(x for x in [ed.degree, ed.institution] if x)
            out.append(line + (f" ({ed.dates})" if ed.dates else ""))
            if ed.details:
                out.append(ed.details)
    if r.certifications:
        out += ["", "CERTIFICATIONS"] + [f"• {c}" for c in r.certifications]
    for s in r.other_sections:
        out += ["", s.heading.upper()] + [f"• {i}" for i in s.items]
    return "\n".join(out).strip()
