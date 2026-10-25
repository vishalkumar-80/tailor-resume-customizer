"use client";

import { Moon, Sun } from "lucide-react";
import { useSyncExternalStore } from "react";

function subscribe(cb: () => void) {
  const obs = new MutationObserver(cb);
  obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => obs.disconnect();
}
const getTheme = () => document.documentElement.dataset.theme ?? "light";

export function Logo() {
  return (
    <span className="flex items-center gap-2.5">
      <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden className="text-ink">
        {/* needle + looping thread */}
        <path d="M6 26 L24 8" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
        <ellipse cx="25.5" cy="6.5" rx="2.2" ry="1.2" transform="rotate(-45 25.5 6.5)" fill="none" stroke="currentColor" strokeWidth="1.4" />
        <path d="M25 7 C 31 14, 14 18, 18 25 S 6 30, 4 22" fill="none" stroke="var(--thread)" strokeWidth="1.6" strokeDasharray="3 3" strokeLinecap="round" />
      </svg>
      <span className="font-serif text-[28px] leading-none tracking-tight">
        Tailor<span className="text-thread">.</span>
      </span>
    </span>
  );
}

export default function Header() {
  const theme = useSyncExternalStore(subscribe, getTheme, () => "light");
  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("theme", next);
    } catch {
      /* storage blocked — theme just won't persist */
    }
  };

  return (
    <header className="relative z-10 mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-5 sm:px-6">
      <Logo />
      <nav className="flex items-center gap-2 text-sm">
        <a href="#workbench" className="hidden rounded-full px-3 py-1.5 text-ink-2 hover:text-ink sm:inline">
          Workbench
        </a>
        <a href="#how" className="hidden rounded-full px-3 py-1.5 text-ink-2 hover:text-ink sm:inline">
          How it works
        </a>
        <button
          onClick={toggle}
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
          className="grid h-9 w-9 place-items-center rounded-full border border-line bg-card text-ink-2 transition hover:text-ink"
        >
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        </button>
      </nav>
    </header>
  );
}
