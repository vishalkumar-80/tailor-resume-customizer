import { Fragment, type ReactNode } from "react";
import type { TailoredResume } from "@/lib/api";

/** Wraps keyword occurrences in a marker highlight. Builds React nodes — never injects HTML. */
export function highlight(text: string, keywords: string[]): ReactNode {
  const terms = keywords.filter((k) => k.trim().length > 1).sort((a, b) => b.length - a.length);
  if (!terms.length || !text) return text;
  const escaped = terms.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const re = new RegExp(`(?<![A-Za-z0-9+#])(${escaped.join("|")})(?![A-Za-z0-9+#])`, "gi");
  const parts = text.split(re);
  return parts.map((p, i) =>
    i % 2 === 1 ? (
      <mark key={i} className="marker">
        {p}
      </mark>
    ) : (
      <Fragment key={i}>{p}</Fragment>
    ),
  );
}

function H({ children }: { children: ReactNode }) {
  return (
    <h3 className="mt-6 mb-2 border-b border-current/15 pb-1 font-mono text-[11px] font-semibold uppercase tracking-[0.18em] opacity-70">
      {children}
    </h3>
  );
}

export default function ResumeSheet({ r, keywords, showMarks }: { r: TailoredResume; keywords: string[]; showMarks: boolean }) {
  const hl = (t: string) => (showMarks ? highlight(t, keywords) : t);

  return (
    <article className="rounded-[18px] border border-line bg-card px-6 py-8 text-[14.5px] leading-relaxed sm:px-10 sm:py-10">
      <header className="text-center">
        <h2 className="font-serif text-4xl leading-tight sm:text-5xl">{r.name || "Your Name"}</h2>
        {r.headline && <p className="mt-1 text-ink-2">{r.headline}</p>}
        {r.contact.length > 0 && (
          <p className="mt-2 flex flex-wrap justify-center gap-x-3 gap-y-1 font-mono text-xs text-ink-3">
            {r.contact.map((c, i) => (
              <span key={i}>{c}</span>
            ))}
          </p>
        )}
      </header>

      {r.summary && (
        <>
          <H>Summary</H>
          <p>{hl(r.summary)}</p>
        </>
      )}

      {r.skills.length > 0 && (
        <>
          <H>Skills</H>
          <ul className="flex flex-wrap gap-1.5">
            {r.skills.map((s, i) => (
              <li
                key={i}
                className={`rounded-md border px-2 py-0.5 text-[13px] ${
                  s.matched && showMarks ? "border-transparent bg-lime font-medium text-lime-ink" : "border-line"
                }`}
              >
                {s.name}
              </li>
            ))}
          </ul>
        </>
      )}

      {r.experience.length > 0 && (
        <>
          <H>Experience</H>
          <div className="space-y-4">
            {r.experience.map((e, i) => (
              <section key={i}>
                <div className="flex flex-wrap items-baseline justify-between gap-x-4">
                  <p className="font-semibold">
                    {e.title}
                    {e.company && <span className="font-normal text-ink-2"> · {e.company}</span>}
                  </p>
                  <p className="font-mono text-xs text-ink-3">{[e.location, e.dates].filter(Boolean).join(" · ")}</p>
                </div>
                <ul className="mt-1.5 list-disc space-y-1 pl-5 marker:text-ink-3">
                  {e.bullets.map((b, j) => (
                    <li key={j}>{hl(b)}</li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        </>
      )}

      {r.projects.length > 0 && (
        <>
          <H>Projects</H>
          <div className="space-y-3">
            {r.projects.map((p, i) => (
              <section key={i}>
                <p className="font-semibold">
                  {p.name}
                  {p.details && <span className="font-normal text-ink-2"> — {hl(p.details)}</span>}
                </p>
                <ul className="mt-1 list-disc space-y-1 pl-5 marker:text-ink-3">
                  {p.bullets.map((b, j) => (
                    <li key={j}>{hl(b)}</li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        </>
      )}

      {r.education.length > 0 && (
        <>
          <H>Education</H>
          {r.education.map((ed, i) => (
            <div key={i} className="mb-2 flex flex-wrap items-baseline justify-between gap-x-4">
              <p>
                <span className="font-semibold">{ed.degree}</span>
                {ed.institution && <span className="text-ink-2"> · {ed.institution}</span>}
                {ed.details && <span className="block text-sm text-ink-2">{ed.details}</span>}
              </p>
              <p className="font-mono text-xs text-ink-3">{ed.dates}</p>
            </div>
          ))}
        </>
      )}

      {r.certifications.length > 0 && (
        <>
          <H>Certifications</H>
          <ul className="list-disc space-y-1 pl-5">
            {r.certifications.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </>
      )}

      {r.other_sections.map((s, i) => (
        <Fragment key={i}>
          <H>{s.heading}</H>
          <ul className="list-disc space-y-1 pl-5">
            {s.items.map((it, j) => (
              <li key={j}>{it}</li>
            ))}
          </ul>
        </Fragment>
      ))}
    </article>
  );
}
