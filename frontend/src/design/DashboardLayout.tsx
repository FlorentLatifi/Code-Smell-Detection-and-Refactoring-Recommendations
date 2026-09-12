// Korniza: shirit sipër, rresht ikonash majtas, përmbajtja djathtas.
//
// Gjerësia nuk kufizohet: një panel kontrolli lexohet paralelisht, dhe margjinat
// e një faqeje e kthejnë atë në dokument me tabela brenda. Kufirin e vetëm e
// mban kolona e mesme e rrjetit, e cila ndalet kur teksti bëhet më i gjatë se sa
// ndjek syri.

import { useState } from "react";
import {
  Boxes,
  ChevronDown,
  FolderGit2,
  Gauge,
  LayoutDashboard,
  Moon,
  Play,
  Settings,
  Sun,
} from "lucide-react";
import { project } from "./mock";

export type View = "overview" | "metrics";

export function DashboardLayout({
  view,
  onView,
  children,
}: {
  view: View;
  onView: (view: View) => void;
  children: React.ReactNode;
}) {
  const [dark, setDark] = useState(true);

  function toggleTheme() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
  }

  return (
    <div className="min-h-screen bg-ink-100 text-ink-800 dark:bg-ink-950 dark:text-ink-200">
      <Header dark={dark} onTheme={toggleTheme} />
      <div className="flex">
        <Rail view={view} onView={onView} />
        <main className="min-w-0 flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}

function Header({ dark, onTheme }: { dark: boolean; onTheme: () => void }) {
  return (
    <header className="sticky top-0 z-20 flex min-h-14 flex-wrap items-center gap-x-4 gap-y-2 border-b border-ink-200 bg-white/80 px-4 py-2 backdrop-blur sm:flex-nowrap sm:py-0 dark:border-ink-800 dark:bg-ink-900/80">
      <div className="flex items-center gap-2">
        <span className="grid h-7 w-7 place-items-center rounded-lg bg-brand-600 text-white">
          <Boxes className="h-4 w-4" />
        </span>
        <span className="text-[15px] font-semibold tracking-tight text-ink-900 dark:text-white">
          JavaSmell
        </span>
      </div>

      <ProjectPicker />

      <div className="ml-auto flex items-center gap-3">
        <ScanStatus />
        <button className="flex h-9 items-center gap-2 rounded-lg bg-brand-600 px-3.5 text-sm font-semibold text-white transition hover:bg-brand-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500">
          <Play className="h-4 w-4" />
          Nis skanimin
        </button>
        <button
          onClick={onTheme}
          aria-label={dark ? "Kalo te tema e çelët" : "Kalo te tema e errët"}
          className="grid h-9 w-9 place-items-center rounded-lg border border-ink-200 text-ink-500 transition hover:bg-ink-100 dark:border-ink-800 dark:hover:bg-ink-800"
        >
          {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>
      </div>
    </header>
  );
}

/** Zgjedhësi i projektit. Te sistemi i vërtetë këtu hyn shtegu lokal. */
function ProjectPicker() {
  return (
    <button className="hidden h-9 items-center gap-2 rounded-lg border border-ink-200 px-3 text-sm text-ink-600 transition hover:bg-ink-100 md:flex dark:border-ink-800 dark:text-ink-300 dark:hover:bg-ink-800">
      <FolderGit2 className="h-4 w-4 text-ink-400" />
      <span className="font-medium text-ink-800 dark:text-ink-100">{project.name}</span>
      <span className="rounded bg-ink-100 px-1.5 py-0.5 text-[11px] text-ink-500 dark:bg-ink-800 dark:text-ink-400">
        {project.branch}
      </span>
      <ChevronDown className="h-4 w-4 text-ink-400" />
    </button>
  );
}

function ScanStatus() {
  return (
    <div className="hidden items-center gap-3 text-xs text-ink-500 lg:flex dark:text-ink-400">
      <span className="flex items-center gap-1.5">
        <span className="h-1.5 w-1.5 rounded-full bg-low" />
        Skanuar {project.lastScan}
      </span>
      <span className="text-ink-300 dark:text-ink-700">·</span>
      <span>
        <span className="font-semibold text-ink-700 tabular-nums dark:text-ink-200">
          {(project.loc / 1000).toFixed(1)}k
        </span>{" "}
        rreshta
      </span>
      <span className="text-ink-300 dark:text-ink-700">·</span>
      <span>
        <span className="font-semibold text-ink-700 tabular-nums dark:text-ink-200">
          {project.files}
        </span>{" "}
        skedarë
      </span>
    </div>
  );
}

function Rail({ view, onView }: { view: View; onView: (view: View) => void }) {
  const items = [
    { id: "overview" as const, icon: LayoutDashboard, label: "Paneli" },
    { id: "metrics" as const, icon: Gauge, label: "Matjet" },
  ];
  return (
    <nav
      aria-label="Pamjet"
      className="sticky top-14 flex h-[calc(100vh-3.5rem)] w-14 flex-col items-center gap-1 border-r border-ink-200 bg-white py-3 dark:border-ink-800 dark:bg-ink-900"
    >
      {items.map((item) => (
        <button
          key={item.id}
          onClick={() => onView(item.id)}
          title={item.label}
          aria-current={view === item.id}
          className={`grid h-10 w-10 place-items-center rounded-lg transition ${
            view === item.id
              ? "bg-brand-600 text-white"
              : "text-ink-400 hover:bg-ink-100 hover:text-ink-700 dark:hover:bg-ink-800 dark:hover:text-ink-100"
          }`}
        >
          <item.icon className="h-[18px] w-[18px]" />
          <span className="sr-only">{item.label}</span>
        </button>
      ))}
      <button
        title="Rregullimet"
        className="mt-auto grid h-10 w-10 place-items-center rounded-lg text-ink-400 transition hover:bg-ink-100 hover:text-ink-700 dark:hover:bg-ink-800 dark:hover:text-ink-100"
      >
        <Settings className="h-[18px] w-[18px]" />
        <span className="sr-only">Rregullimet</span>
      </button>
    </nav>
  );
}

/** Korniza e përbashkët e çdo karte. */
export function Card({
  title,
  action,
  children,
  className = "",
}: {
  title?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      aria-label={title}
      className={`min-w-0 rounded-xl border border-ink-200 bg-white shadow-sm dark:border-ink-800 dark:bg-ink-900 ${className}`}
    >
      {title && (
        <div className="flex items-center justify-between border-b border-ink-200 px-4 py-3 dark:border-ink-800">
          <h2 className="text-[13px] font-semibold tracking-wide text-ink-700 uppercase dark:text-ink-300">
            {title}
          </h2>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}
