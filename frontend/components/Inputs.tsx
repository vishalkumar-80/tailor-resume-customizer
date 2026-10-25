"use client";

import { FileText, UploadCloud, X } from "lucide-react";
import { useRef, useState } from "react";
import { formatBytes, MAX_FILE_MB, MAX_JD, MIN_JD, type SectionKey, type Tone, validateFile } from "@/lib/api";

function StepLabel({ n, title, hint }: { n: string; title: string; hint?: string }) {
  return (
    <div className="mb-3 flex items-baseline justify-between gap-3">
      <h2 className="flex items-baseline gap-3">
        <span className="font-mono text-xs text-thread">{n}</span>
        <span className="font-serif text-2xl">{title}</span>
      </h2>
      {hint && <span className="text-xs text-ink-3">{hint}</span>}
    </div>
  );
}

export function JobInput({ value, onChange, touched }: { value: string; onChange: (v: string) => void; touched: boolean }) {
  const len = value.trim().length;
  const error = touched && len === 0 ? "Paste the job description first." : touched && len < MIN_JD ? `Too short — at least ${MIN_JD} characters (${len} now).` : null;
  const pct = Math.min(100, (len / MIN_JD) * 100);

  return (
    <div className="card flex flex-col p-5 sm:p-6">
      <StepLabel n="01" title="The job" hint="Paste the full JD" />
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value.slice(0, MAX_JD))}
        placeholder={"Senior Frontend Engineer — Acme\n\nWe're looking for someone who…\n• 4+ years with React & TypeScript\n• …"}
        aria-label="Job description"
        aria-invalid={!!error}
        aria-describedby="jd-help"
        className={`min-h-[260px] w-full flex-1 resize-y rounded-2xl border bg-paper/60 p-4 text-[15px] leading-relaxed outline-none transition placeholder:text-ink-3 focus:border-ink ${
          error ? "border-thread" : "border-line"
        }`}
      />
      <div id="jd-help" className="mt-3 flex items-center gap-3 text-xs">
        <div className="h-1 flex-1 overflow-hidden rounded-full bg-paper-2">
          <div className="h-full rounded-full bg-ink transition-all" style={{ width: `${pct}%`, background: len >= MIN_JD ? "var(--ok)" : undefined }} />
        </div>
        <span className={error ? "text-thread" : "text-ink-3"} role={error ? "alert" : undefined}>
          {error ?? `${len.toLocaleString()} / ${MAX_JD.toLocaleString()} chars`}
        </span>
      </div>
    </div>
  );
}

export function ResumeDrop({
  file,
  onFile,
  touched,
}: {
  file: File | null;
  onFile: (f: File | null) => void;
  touched: boolean;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const take = (f?: File | null) => {
    if (!f) return;
    const err = validateFile(f);
    setError(err);
    onFile(err ? null : f);
  };

  const shownError = error ?? (touched && !file ? "Upload your resume (PDF or DOCX)." : null);

  return (
    <div className="card flex flex-col p-5 sm:p-6">
      <StepLabel n="02" title="Your resume" hint={`PDF or DOCX · max ${MAX_FILE_MB} MB`} />
      {file ? (
        <div className="stitch flex flex-1 flex-col items-center justify-center gap-4 rounded-2xl bg-paper/60 p-6 text-center">
          <div className="grid h-14 w-14 place-items-center rounded-2xl bg-lime text-lime-ink">
            <FileText size={26} />
          </div>
          <div className="min-w-0">
            <p className="max-w-[260px] truncate font-medium" title={file.name}>
              {file.name}
            </p>
            <p className="mt-1 font-mono text-xs text-ink-3">
              {formatBytes(file.size)} · {file.name.split(".").pop()?.toUpperCase()}
            </p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => input.current?.click()} className="rounded-full border border-line px-3 py-1.5 text-xs hover:border-ink">
              Replace
            </button>
            <button
              onClick={() => {
                onFile(null);
                setError(null);
                if (input.current) input.current.value = "";
              }}
              className="flex items-center gap-1 rounded-full border border-line px-3 py-1.5 text-xs hover:border-thread hover:text-thread"
            >
              <X size={12} /> Remove
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => input.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            take(e.dataTransfer.files?.[0]);
          }}
          className={`stitch group flex min-h-[260px] flex-1 flex-col items-center justify-center gap-3 rounded-2xl p-6 text-center transition ${
            drag ? "bg-lime/30" : "bg-paper/60 hover:bg-paper-2/70"
          }`}
        >
          <span className="grid h-14 w-14 place-items-center rounded-full border border-line bg-card transition group-hover:-translate-y-1">
            <UploadCloud size={24} />
          </span>
          <span className="font-serif text-xl">Drop it on the cutting table</span>
          <span className="text-sm text-ink-3">or click to browse</span>
        </button>
      )}
      <input
        ref={input}
        type="file"
        accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        className="hidden"
        onChange={(e) => take(e.target.files?.[0])}
        aria-label="Upload resume"
      />
      <p className={`mt-3 min-h-4 text-xs ${shownError ? "text-thread" : "text-ink-3"}`} role={shownError ? "alert" : undefined}>
        {shownError ?? "Your file is parsed in memory and never stored."}
      </p>
    </div>
  );
}

const SECTIONS: { key: SectionKey; label: string }[] = [
  { key: "summary", label: "Summary" },
  { key: "skills", label: "Skills" },
  { key: "experience", label: "Experience" },
  { key: "projects", label: "Projects" },
];

const TONES: { key: Tone; label: string }[] = [
  { key: "balanced", label: "Balanced" },
  { key: "bold", label: "Bold" },
  { key: "concise", label: "Concise" },
];

export function FitOptions({
  sections,
  setSections,
  tone,
  setTone,
}: {
  sections: SectionKey[];
  setSections: (s: SectionKey[]) => void;
  tone: Tone;
  setTone: (t: Tone) => void;
}) {
  const toggle = (k: SectionKey) =>
    setSections(sections.includes(k) ? sections.filter((s) => s !== k) : [...sections, k]);

  return (
    <div className="card flex flex-col gap-5 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
      <div>
        <StepLabel n="03" title="Fit options" />
        <fieldset className="flex flex-wrap gap-2">
          <legend className="sr-only">Sections to customize</legend>
          {SECTIONS.map((s) => {
            const on = sections.includes(s.key);
            return (
              <button
                key={s.key}
                type="button"
                aria-pressed={on}
                onClick={() => toggle(s.key)}
                className={`rounded-full border px-3.5 py-1.5 text-sm transition ${
                  on ? "border-ink bg-ink text-paper" : "border-line text-ink-2 hover:border-ink-3"
                }`}
              >
                {on ? "✓ " : "+ "}
                {s.label}
              </button>
            );
          })}
        </fieldset>
        {sections.length === 0 && <p className="mt-2 text-xs text-thread">Pick at least one section.</p>}
      </div>
      <div>
        <p className="mb-2 font-mono text-xs uppercase tracking-wider text-ink-3">Tone</p>
        <div role="radiogroup" aria-label="Tone" className="inline-flex rounded-full border border-line bg-paper/60 p-1">
          {TONES.map((t) => (
            <button
              key={t.key}
              role="radio"
              aria-checked={tone === t.key}
              onClick={() => setTone(t.key)}
              className={`rounded-full px-4 py-1.5 text-sm transition ${tone === t.key ? "bg-lime text-lime-ink shadow-sm" : "text-ink-2 hover:text-ink"}`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
