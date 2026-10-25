"use client";

import { diffWords } from "diff";
import { useMemo } from "react";

const norm = (s: string) =>
  s
    .replace(/[•▪●◦·–-]\s/g, "• ")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{2,}/g, "\n")
    .trim();

export default function DiffView({ original, tailored }: { original: string; tailored: string }) {
  const parts = useMemo(() => diffWords(norm(original), norm(tailored)), [original, tailored]);
  const added = parts.filter((p) => p.added).reduce((n, p) => n + p.value.split(/\s+/).filter(Boolean).length, 0);
  const removed = parts.filter((p) => p.removed).reduce((n, p) => n + p.value.split(/\s+/).filter(Boolean).length, 0);

  return (
    <div className="rounded-[18px] border border-line bg-card p-6 sm:p-8">
      <div className="mb-4 flex flex-wrap items-center gap-3 font-mono text-xs">
        <span className="diff-add px-2 py-0.5">+{added} words added</span>
        <span className="diff-del px-2 py-0.5">−{removed} words removed</span>
        <span className="text-ink-3">Original text vs. tailored version</span>
      </div>
      <pre className="font-sans text-[14px] leading-relaxed whitespace-pre-wrap">
        {parts.map((p, i) =>
          p.added ? (
            <ins key={i} className="diff-add">
              {p.value}
            </ins>
          ) : p.removed ? (
            <del key={i} className="diff-del">
              {p.value}
            </del>
          ) : (
            <span key={i}>{p.value}</span>
          ),
        )}
      </pre>
    </div>
  );
}
