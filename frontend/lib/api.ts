export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

export const MAX_FILE_MB = 4;
export const MIN_JD = 100;
export const MAX_JD = 15000;
export const ACCEPTED = [".pdf", ".docx"];

export type SectionKey = "summary" | "skills" | "experience" | "projects";
export type Tone = "balanced" | "bold" | "concise";

export interface TailoredResume {
  name: string;
  headline: string;
  contact: string[];
  summary: string;
  skills: { name: string; matched: boolean }[];
  experience: { title: string; company: string; location: string; dates: string; bullets: string[] }[];
  projects: { name: string; details: string; bullets: string[] }[];
  education: { degree: string; institution: string; dates: string; details: string }[];
  certifications: string[];
  other_sections: { heading: string; items: string[] }[];
}

export interface TailorResult {
  resume: TailoredResume;
  tailored_text: string;
  original_text: string;
  jd_keywords: { keyword: string; importance: "high" | "medium" | "low" }[];
  missing_keywords: { keyword: string; suggestion: string }[];
  change_log: string[];
  scores: {
    match_before: number;
    match_after: number;
    ats: number;
    ats_checks: { label: string; passed: boolean }[];
    keywords_found_before: string[];
    keywords_found_after: string[];
  };
  model: string;
  file: { name: string; kind: string; size: number };
}

export class ApiError extends Error {}

async function request(path: string, init: RequestInit, timeoutMs = 120_000): Promise<Response> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, signal: ctrl.signal });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw new ApiError("The request timed out. Please try again.");
    throw new ApiError("Can't reach the server. Check your connection, or the API may be waking up — retry in a few seconds.");
  } finally {
    clearTimeout(timer);
  }
  if (!res.ok) {
    let msg = `Request failed (${res.status}).`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") msg = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(msg);
  }
  return res;
}

export async function tailorResume(opts: {
  jd: string;
  file: File;
  sections: SectionKey[];
  tone: Tone;
}): Promise<TailorResult> {
  const form = new FormData();
  form.append("job_description", opts.jd);
  form.append("resume", opts.file);
  form.append("sections", opts.sections.join(","));
  form.append("tone", opts.tone);
  const res = await request("/api/tailor", { method: "POST", body: form });
  return res.json();
}

export async function generateCoverLetter(jd: string, resumeText: string, tone: Tone) {
  const res = await request("/api/cover-letter", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_description: jd, resume_text: resumeText, tone }),
  });
  return (await res.json()) as { subject: string; letter: string; model: string };
}

async function downloadExport(resume: TailoredResume, ext: "pdf" | "docx") {
  const res = await request(`/api/export/${ext}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resume }),
  });
  saveBlob(await res.blob(), `${slug(resume.name)}_tailored.${ext}`);
}

export const downloadDocx = (resume: TailoredResume) => downloadExport(resume, "docx");
export const downloadPdf = (resume: TailoredResume) => downloadExport(resume, "pdf");

export function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function slug(s: string) {
  return (s || "resume").replace(/[^a-z0-9]+/gi, "_").replace(/^_|_$/g, "").slice(0, 40) || "resume";
}

export function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
}

export function validateFile(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!ACCEPTED.some((ext) => name.endsWith(ext))) return "Only PDF or DOCX files are supported.";
  if (file.size === 0) return "That file is empty.";
  if (file.size > MAX_FILE_MB * 1024 * 1024) return `File is too large — maximum is ${MAX_FILE_MB} MB.`;
  return null;
}
