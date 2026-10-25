"use client";

import { ArrowRight, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import Header, { Logo } from "@/components/Header";
import { FitOptions, JobInput, ResumeDrop } from "@/components/Inputs";
import Results, { type Version } from "@/components/Results";
import { ApiError, MIN_JD, type SectionKey, tailorResume, type Tone } from "@/lib/api";

const STAGES = ["Reading your resume", "Measuring the job description", "Matching keywords", "Re-stitching bullets", "Pressing the final copy"];

function Stitching() {
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((x) => Math.min(x + 1, STAGES.length - 1)), 2600);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="card rise mx-auto flex max-w-xl flex-col items-center gap-5 p-8 text-center" role="status" aria-live="polite">
      <svg width="220" height="40" viewBox="0 0 220 40" aria-hidden>
        <path d="M4 20 Q 30 4, 56 20 T 108 20 T 160 20 T 216 20" fill="none" stroke="var(--thread)" strokeWidth="2.2" className="sewing" strokeLinecap="round" />
        <path d="M4 20 L 216 20" stroke="var(--line)" strokeWidth="1" />
      </svg>
      <p className="font-serif text-2xl">{STAGES[i]}…</p>
      <ol className="flex gap-1.5">
        {STAGES.map((s, j) => (
          <li key={s} className={`h-1.5 w-8 rounded-full transition ${j <= i ? "bg-ink" : "bg-paper-2"}`} />
        ))}
      </ol>
      <p className="text-xs text-ink-3">Usually 5–20 seconds.</p>
    </div>
  );
}

export default function Home() {
  const [jd, setJd] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [sections, setSections] = useState<SectionKey[]>(["summary", "skills", "experience", "projects"]);
  const [tone, setTone] = useState<Tone>("balanced");
  const [touched, setTouched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [activeId, setActiveId] = useState(0);
  const resultsRef = useRef<HTMLDivElement>(null);

  const valid = jd.trim().length >= MIN_JD && !!file && sections.length > 0;

  const submit = async () => {
    setTouched(true);
    setError(null);
    if (!valid || !file) return;
    setLoading(true);
    try {
      const result = await tailorResume({ jd: jd.trim(), file, sections, tone });
      const id = (versions.at(-1)?.id ?? 0) + 1;
      setVersions((vs) => [...vs, { id, tone, sections: [...sections], result }].slice(-5));
      setActiveId(id);
      requestAnimationFrame(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something unexpected went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="relative">
      <Header />

      {/* Hero */}
      <section className="relative z-10 mx-auto max-w-6xl px-4 pt-8 pb-12 sm:px-6 sm:pt-14">
        <p className="rise mb-6 inline-flex items-center gap-2 rounded-full border border-line bg-card px-3 py-1 font-mono text-[11px] uppercase tracking-[0.16em] text-ink-2">
          <span className="h-1.5 w-1.5 rounded-full bg-thread" /> Gemini-powered · ATS-aware · no fabrication
        </p>
        <h1 className="rise font-serif text-[clamp(3rem,9vw,7.5rem)] leading-[0.92] tracking-tight" style={{ animationDelay: "80ms" }}>
          Your resume,
          <br />
          <em className="relative">
            cut to fit
            <svg className="absolute -bottom-2 left-0 w-full" viewBox="0 0 300 12" preserveAspectRatio="none" aria-hidden>
              <path d="M2 8 C 60 2, 120 12, 180 6 S 280 4, 298 7" fill="none" stroke="var(--thread)" strokeWidth="2.5" strokeDasharray="7 5" strokeLinecap="round" />
            </svg>
          </em>{" "}
          the job.
        </h1>
        <p className="rise mt-8 max-w-xl text-lg text-ink-2" style={{ animationDelay: "160ms" }}>
          Paste a job description, drop in your resume, and Tailor re-cuts your summary, skills and experience bullets to the role —
          then shows you exactly what changed and how well it fits.
        </p>
      </section>

      <div className="tape relative z-10 -rotate-1 border-y border-lime-ink/20" aria-hidden />

      {/* Workbench */}
      <section id="workbench" className="relative z-10 mx-auto max-w-6xl scroll-mt-6 px-4 py-14 sm:px-6">
        <div className="grid gap-4 md:grid-cols-2">
          <JobInput value={jd} onChange={setJd} touched={touched} />
          <ResumeDrop file={file} onFile={setFile} touched={touched} />
        </div>
        <div className="mt-4">
          <FitOptions sections={sections} setSections={setSections} tone={tone} setTone={setTone} />
        </div>

        <div className="mt-8 flex flex-col items-center gap-4">
          {error && (
            <p role="alert" className="w-full max-w-xl rounded-2xl border border-thread/40 bg-thread/10 px-4 py-3 text-center text-sm text-thread">
              {error}
            </p>
          )}
          {loading ? (
            <Stitching />
          ) : (
            <button
              onClick={submit}
              className="group flex items-center gap-3 rounded-full bg-ink py-4 pr-4 pl-7 text-lg text-paper shadow-[var(--shadow)] transition hover:-translate-y-0.5 disabled:opacity-50"
            >
              {versions.length ? "Tailor another version" : "Tailor my resume"}
              <span className="grid h-9 w-9 place-items-center rounded-full bg-lime text-lime-ink transition group-hover:translate-x-1">
                {loading ? <Loader2 size={18} className="animate-spin" /> : <ArrowRight size={18} />}
              </span>
            </button>
          )}
          {!loading && touched && !valid && <p className="text-xs text-ink-3">Fill in the highlighted fields above to continue.</p>}
        </div>
      </section>

      <div ref={resultsRef}>
        {versions.length > 0 && (
          <Results
            versions={versions}
            activeId={activeId}
            setActiveId={setActiveId}
            onRegenerate={submit}
            regenerating={loading}
            jd={jd}
            onCover={(id, cover) => setVersions((vs) => vs.map((v) => (v.id === id ? { ...v, cover } : v)))}
          />
        )}
      </div>

      {/* How it works */}
      <section id="how" className="relative z-10 mx-auto max-w-6xl scroll-mt-6 px-4 pb-20 sm:px-6">
        <h2 className="mb-8 font-serif text-4xl">How the fitting works</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {[
            ["Measure", "Your resume is parsed in memory (PDF or DOCX) and the job description is scanned for the skills, tools and qualifications that matter most."],
            ["Cut", "Gemini rewrites your summary, reorders and rephrases bullets in the JD's language, and flags missing keywords — without inventing anything."],
            ["Fit", "Deterministic scoring shows keyword match before vs. after, an ATS checklist, and a word-level diff so you stay in control."],
          ].map(([t, d], i) => (
            <div key={t} className="card stitch p-6">
              <span className="font-mono text-xs text-thread">0{i + 1}</span>
              <h3 className="mt-2 font-serif text-3xl">{t}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-2">{d}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="relative z-10 border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-8 text-sm text-ink-3 sm:px-6">
          <Logo />
          <p>Files are processed in memory and never stored. Always review AI output before applying.</p>
        </div>
      </footer>
    </main>
  );
}
