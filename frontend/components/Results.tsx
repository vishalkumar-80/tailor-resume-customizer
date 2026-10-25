"use client";

import { Check, Copy, Download, FileDown, FileText, Highlighter, Loader2, Plus, RefreshCw, X } from "lucide-react";
import { useState } from "react";
import { ApiError, downloadDocx, downloadPdf, generateCoverLetter, saveBlob, slug, type TailorResult, type Tone } from "@/lib/api";
import DiffView from "./DiffView";
import ResumeSheet from "./ResumeSheet";
import ScoreDial from "./ScoreDial";

export interface Version {
  id: number;
  tone: Tone;
  sections: string[];
  result: TailorResult;
  cover?: { subject: string; letter: string };
}

type Tab = "tailored" | "diff" | "cover" | "original";

function Tile({ title, children, className = "" }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`card rise p-5 ${className}`}>
      <h3 className="mb-3 font-mono text-[11px] uppercase tracking-[0.16em] text-ink-3">{title}</h3>
      {children}
    </section>
  );
}

export default function Results({
  versions,
  activeId,
  setActiveId,
  onRegenerate,
  regenerating,
  jd,
  onCover,
}: {
  versions: Version[];
  activeId: number;
  setActiveId: (id: number) => void;
  onRegenerate: () => void;
  regenerating: boolean;
  jd: string;
  onCover: (id: number, cover: { subject: string; letter: string }) => void;
}) {
  const v = versions.find((x) => x.id === activeId) ?? versions[versions.length - 1];
  const { result: r } = v;
  const [tab, setTab] = useState<Tab>("tailored");
  const [marks, setMarks] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const run = async (key: string, fn: () => Promise<void>) => {
    setBusy(key);
    setErr(null);
    try {
      await fn();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(null);
    }
  };

  const makeCover = () =>
    run("cover", async () => {
      // Ground the letter in the original resume, the candidate's source of truth.
      const c = await generateCoverLetter(jd, r.original_text, v.tone);
      onCover(v.id, { subject: c.subject, letter: c.letter });
    });

  const txt = () => saveBlob(new Blob([r.tailored_text], { type: "text/plain;charset=utf-8" }), `${slug(r.resume.name)}_tailored.txt`);

  const tabs: { key: Tab; label: string }[] = [
    { key: "tailored", label: "Tailored" },
    { key: "diff", label: "What changed" },
    { key: "cover", label: "Cover letter" },
    { key: "original", label: "Original" },
  ];

  const passed = r.scores.ats_checks.filter((c) => c.passed).length;

  return (
    <div id="results" className="relative z-10 mx-auto w-full max-w-6xl scroll-mt-6 px-4 pb-24 sm:px-6">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-thread">Fitting room</p>
          <h2 className="font-serif text-4xl sm:text-5xl">
            Here&apos;s your <em>tailored</em> cut.
          </h2>
        </div>
        <div className="flex flex-wrap items-center gap-2" role="tablist" aria-label="Resume versions">
          {versions.map((x) => (
            <button
              key={x.id}
              role="tab"
              aria-selected={x.id === v.id}
              onClick={() => setActiveId(x.id)}
              className={`rounded-full border px-3 py-1.5 font-mono text-xs transition ${
                x.id === v.id ? "border-ink bg-ink text-paper" : "border-line text-ink-2 hover:border-ink-3"
              }`}
              title={`${x.tone} tone · ${x.sections.join(", ")}`}
            >
              v{x.id} · {x.result.scores.match_after}%
            </button>
          ))}
          <button
            onClick={onRegenerate}
            disabled={regenerating}
            className="flex items-center gap-1.5 rounded-full border border-dashed border-ink-3 px-3 py-1.5 text-xs text-ink-2 transition hover:border-ink hover:text-ink disabled:opacity-50"
          >
            {regenerating ? <Loader2 size={13} className="animate-spin" /> : <Plus size={13} />} New version
          </button>
        </div>
      </div>

      {/* Bento grid of insights */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-6">
        <Tile title="Keyword match" className="md:col-span-2">
          <div className="flex justify-center">
            <ScoreDial value={r.scores.match_after} before={r.scores.match_before} label="JD match" />
          </div>
          <p className="mt-3 text-center text-xs text-ink-3">
            {r.scores.keywords_found_after.length} of {r.jd_keywords.length} key terms found, weighted by importance.
          </p>
        </Tile>

        <Tile title="ATS readiness" className="md:col-span-2">
          <div className="flex items-center gap-4">
            <ScoreDial value={r.scores.ats} label="ATS" size={104} />
            <ul className="space-y-1 text-[13px]">
              {r.scores.ats_checks.slice(0, 5).map((c) => (
                <li key={c.label} className="flex items-start gap-1.5">
                  {c.passed ? <Check size={14} className="mt-0.5 shrink-0 text-ok" /> : <X size={14} className="mt-0.5 shrink-0 text-thread" />}
                  <span className={c.passed ? "" : "text-ink-2"}>{c.label}</span>
                </li>
              ))}
            </ul>
          </div>
          <details className="mt-2 text-[13px]">
            <summary className="cursor-pointer text-xs text-ink-3">
              All {r.scores.ats_checks.length} checks ({passed} passed)
            </summary>
            <ul className="mt-2 space-y-1">
              {r.scores.ats_checks.slice(5).map((c) => (
                <li key={c.label} className="flex items-start gap-1.5">
                  {c.passed ? <Check size={14} className="mt-0.5 shrink-0 text-ok" /> : <X size={14} className="mt-0.5 shrink-0 text-thread" />}
                  {c.label}
                </li>
              ))}
            </ul>
          </details>
        </Tile>

        <Tile title="JD keywords" className="md:col-span-2">
          <ul className="flex flex-wrap gap-1.5">
            {r.jd_keywords.map((k) => {
              const found = r.scores.keywords_found_after.includes(k.keyword);
              const isNew = found && !r.scores.keywords_found_before.includes(k.keyword);
              return (
                <li
                  key={k.keyword}
                  title={`${k.importance} importance${isNew ? " · added by tailoring" : ""}`}
                  className={`rounded-full border px-2.5 py-0.5 text-xs ${
                    found ? "border-transparent bg-lime text-lime-ink" : "border-dashed border-ink-3 text-ink-3"
                  } ${k.importance === "high" ? "font-semibold" : ""}`}
                >
                  {isNew && "★ "}
                  {k.keyword}
                </li>
              );
            })}
          </ul>
          <p className="mt-3 text-xs text-ink-3">Lime = in your resume · ★ = surfaced by tailoring · dashed = missing</p>
        </Tile>

        <Tile title="Missing keywords — worth adding if true" className="md:col-span-3">
          {r.missing_keywords.length === 0 ? (
            <p className="text-sm text-ink-2">Nothing important is missing. Nice fit.</p>
          ) : (
            <ul className="space-y-2.5">
              {r.missing_keywords.map((m) => (
                <li key={m.keyword} className="text-sm">
                  <span className="mr-2 rounded-md border border-thread/40 px-1.5 py-0.5 font-mono text-xs text-thread">{m.keyword}</span>
                  <span className="text-ink-2">{m.suggestion}</span>
                </li>
              ))}
            </ul>
          )}
        </Tile>

        <Tile title="Alterations made" className="md:col-span-3">
          <ol className="space-y-2 text-sm">
            {r.change_log.map((c, i) => (
              <li key={i} className="flex gap-3">
                <span className="font-mono text-xs text-thread">{String(i + 1).padStart(2, "0")}</span>
                <span className="text-ink-2">{c}</span>
              </li>
            ))}
          </ol>
        </Tile>
      </div>

      {/* Document area */}
      <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
        <div role="tablist" aria-label="Views" className="inline-flex flex-wrap rounded-full border border-line bg-card p-1">
          {tabs.map((t) => (
            <button
              key={t.key}
              role="tab"
              aria-selected={tab === t.key}
              onClick={() => setTab(t.key)}
              className={`rounded-full px-4 py-1.5 text-sm transition ${tab === t.key ? "bg-ink text-paper" : "text-ink-2 hover:text-ink"}`}
            >
              {t.label}
            </button>
          ))}
        </div>
        {tab === "tailored" && (
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setMarks(!marks)}
              aria-pressed={marks}
              className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs ${marks ? "border-ink" : "border-line text-ink-3"}`}
            >
              <Highlighter size={13} /> Highlights
            </button>
            <button
              onClick={() => run("pdf", () => downloadPdf(r.resume))}
              disabled={busy === "pdf"}
              className="flex items-center gap-1.5 rounded-full border border-line px-3 py-1.5 text-xs hover:border-ink disabled:opacity-50"
            >
              {busy === "pdf" ? <Loader2 size={13} className="animate-spin" /> : <FileDown size={13} />} PDF
            </button>
            <button
              onClick={() => run("docx", () => downloadDocx(r.resume))}
              disabled={busy === "docx"}
              className="flex items-center gap-1.5 rounded-full border border-line px-3 py-1.5 text-xs hover:border-ink disabled:opacity-50"
            >
              {busy === "docx" ? <Loader2 size={13} className="animate-spin" /> : <FileDown size={13} />} DOCX
            </button>
            <button onClick={txt} className="flex items-center gap-1.5 rounded-full bg-lime px-3 py-1.5 text-xs font-medium text-lime-ink">
              <Download size={13} /> TXT
            </button>
          </div>
        )}
      </div>

      {err && (
        <p role="alert" className="mt-3 rounded-xl border border-thread/40 bg-thread/10 px-4 py-2 text-sm text-thread">
          {err}
        </p>
      )}

      <div className="mt-4">
        {tab === "tailored" && <ResumeSheet r={r.resume} keywords={r.scores.keywords_found_after} showMarks={marks} />}
        {tab === "diff" && <DiffView original={r.original_text} tailored={r.tailored_text} />}
        {tab === "original" && (
          <pre className="rounded-[18px] border border-line bg-card p-6 font-sans text-[14px] leading-relaxed whitespace-pre-wrap text-ink-2 sm:p-8">
            {r.original_text}
          </pre>
        )}
        {tab === "cover" && (
          <div className="rounded-[18px] border border-line bg-card p-6 sm:p-10">
            {v.cover ? (
              <>
                <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                  <p className="font-serif text-2xl">{v.cover.subject}</p>
                  <div className="flex gap-2">
                    <button
                      onClick={async () => {
                        await navigator.clipboard.writeText(v.cover!.letter);
                        setCopied(true);
                        setTimeout(() => setCopied(false), 1500);
                      }}
                      className="flex items-center gap-1.5 rounded-full border border-line px-3 py-1.5 text-xs hover:border-ink"
                    >
                      {copied ? <Check size={13} /> : <Copy size={13} />} {copied ? "Copied" : "Copy"}
                    </button>
                    <button
                      onClick={() =>
                        saveBlob(new Blob([v.cover!.letter], { type: "text/plain;charset=utf-8" }), `${slug(r.resume.name)}_cover_letter.txt`)
                      }
                      className="flex items-center gap-1.5 rounded-full border border-line px-3 py-1.5 text-xs hover:border-ink"
                    >
                      <Download size={13} /> TXT
                    </button>
                    <button
                      onClick={makeCover}
                      disabled={busy === "cover"}
                      className="flex items-center gap-1.5 rounded-full border border-line px-3 py-1.5 text-xs hover:border-ink disabled:opacity-50"
                    >
                      <RefreshCw size={13} className={busy === "cover" ? "animate-spin" : ""} /> Rewrite
                    </button>
                  </div>
                </div>
                <div className="max-w-2xl space-y-4 text-[15px] leading-relaxed">
                  {v.cover.letter.split(/\n{2,}/).map((p, i) => (
                    <p key={i} className="whitespace-pre-line">
                      {p}
                    </p>
                  ))}
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center gap-4 py-10 text-center">
                <FileText size={28} className="text-ink-3" />
                <p className="max-w-md text-ink-2">Generate a concise cover letter grounded in your resume and this job description.</p>
                <button
                  onClick={makeCover}
                  disabled={busy === "cover"}
                  className="flex items-center gap-2 rounded-full bg-ink px-5 py-2.5 text-sm text-paper disabled:opacity-60"
                >
                  {busy === "cover" && <Loader2 size={15} className="animate-spin" />} Write my cover letter
                </button>
              </div>
            )}
          </div>
        )}
      </div>
      <p className="mt-4 text-center font-mono text-[11px] text-ink-3">
        v{v.id} · {v.tone} tone · tailored with {r.model} · always review AI output before sending
      </p>
    </div>
  );
}
