from typing import Literal

from pydantic import BaseModel, Field

Section = Literal["summary", "skills", "experience", "projects"]
Tone = Literal["balanced", "bold", "concise"]


class Skill(BaseModel):
    name: str
    matched: bool = False


class Experience(BaseModel):
    title: str = ""
    company: str = ""
    location: str = ""
    dates: str = ""
    bullets: list[str] = Field(default_factory=list)


class Project(BaseModel):
    name: str = ""
    details: str = ""
    bullets: list[str] = Field(default_factory=list)


class Education(BaseModel):
    degree: str = ""
    institution: str = ""
    dates: str = ""
    details: str = ""


class OtherSection(BaseModel):
    heading: str
    items: list[str] = Field(default_factory=list)


class Keyword(BaseModel):
    keyword: str
    importance: Literal["high", "medium", "low"] = "medium"


class MissingKeyword(BaseModel):
    keyword: str
    suggestion: str = ""


class TailoredResume(BaseModel):
    name: str = ""
    headline: str = ""
    contact: list[str] = Field(default_factory=list)
    summary: str = ""
    skills: list[Skill] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    other_sections: list[OtherSection] = Field(default_factory=list)


class Scores(BaseModel):
    match_before: int
    match_after: int
    ats: int
    ats_checks: list[dict]
    keywords_found_before: list[str]
    keywords_found_after: list[str]


class TailorResponse(BaseModel):
    resume: TailoredResume
    tailored_text: str
    original_text: str
    jd_keywords: list[Keyword]
    missing_keywords: list[MissingKeyword]
    change_log: list[str]
    scores: Scores
    model: str
    file: dict


class CoverLetterRequest(BaseModel):
    job_description: str = Field(min_length=1, max_length=15_000)
    resume_text: str = Field(min_length=1, max_length=30_000)
    tone: Tone = "balanced"


class CoverLetterResponse(BaseModel):
    subject: str
    letter: str
    model: str


class ExportRequest(BaseModel):
    resume: TailoredResume
