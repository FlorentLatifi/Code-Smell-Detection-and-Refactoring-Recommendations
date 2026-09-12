// Korniza: shirit sipër, rresht ikonash majtas, përmbajtja djathtas.
//
// Gjerësia nuk kufizohet: një panel kontrolli lexohet paralelisht, dhe margjinat
// e një faqeje e kthejnë atë në dokument me tabela brenda.
//
// Asgjë këtu nuk di nga vijnë të dhënat. Shiriti merr një nyje për zgjedhësin e
// projektit dhe një për statusin, që i njëjti komponent të shërbejë faqen e
// dizajnit me të dhëna të rreme dhe aplikacionin me ato të vërteta (VD-106).

import { Boxes, Gauge, LayoutDashboard, Moon, Play, Square, Sun } from "lucide-react";

export type View = "overview" | "metrics";

export function DashboardLayout({
  view,
  onView,
  dark,
  onTheme,
  project,
  status,
  onScan,
  onStop,
  busy = false,
  canScan = true,
  scanLabel = "Nis skanimin",
  onTabKeyDown,
  children,
}: {
  view: View;
  onView: (view: View) => void;
  dark: boolean;
  onTheme: () => void;
  /** Zgjedhësi i projektit: dropdown te maketi, kutia e shtegut te aplikacioni. */
  project: React.ReactNode;
  status?: React.ReactNode;
  onScan: () => void;
  onStop?: () => void;
  busy?: boolean;
  /** Pa shteg nuk ka çfarë të skanohet, dhe butoni nuk guxon ta premtojë. */
  canScan?: boolean;
  scanLabel?: string;
  /** Shigjetat lëvizin mes pamjeve, siç pret dikush që njeh modelin `tablist`. */
  onTabKeyDown?: (event: React.KeyboardEvent) => void;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-ink-100 text-ink-800 dark:bg-ink-950 dark:text-ink-200">
      {/* Lidhja e parë te rendi i tabulimit, e padukshme derisa merr fokusin. Pa
          të, një përdorues me tastierë kalon çdo herë nëpër kokë dhe nëpër rresht
          para se të arrijë te përmbajtja. */}
      <a
        href="#content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-lg focus:bg-brand-600 focus:px-3 focus:py-2 focus:text-sm focus:text-white"
      >
        Kalo te përmbajtja
      </a>
      <header className="sticky top-0 z-20 flex min-h-14 flex-wrap items-center gap-x-4 gap-y-2 border-b border-ink-200 bg-white/85 px-4 py-2 backdrop-blur sm:flex-nowrap sm:py-0 dark:border-ink-800 dark:bg-ink-900/85">
        <div className="flex shrink-0 items-center gap-2">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-brand-600 text-white">
            <Boxes className="h-4 w-4" />
          </span>
          <span className="text-[15px] font-semibold tracking-tight text-ink-900 dark:text-white">
            JavaSmell
          </span>
        </div>

        {project}

        <div className="ml-auto flex shrink-0 items-center gap-3">
          {status}
          {busy && onStop ? (
            <button
              onClick={onStop}
              className="flex h-9 items-center gap-2 rounded-lg border border-ink-300 px-3.5 text-sm font-medium text-ink-700 transition hover:bg-ink-100 dark:border-ink-700 dark:text-ink-200 dark:hover:bg-ink-800"
            >
              <Square className="h-3.5 w-3.5" />
              Ndalo
            </button>
          ) : (
            <button
              onClick={onScan}
              disabled={busy || !canScan}
              className="flex h-9 items-center gap-2 rounded-lg bg-brand-600 px-3.5 text-sm font-semibold text-white transition hover:bg-brand-500 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500"
            >
              <Play className="h-4 w-4" />
              {busy ? "Duke skanuar…" : scanLabel}
            </button>
          )}
          <button
            onClick={onTheme}
            aria-label={dark ? "Kalo te tema e çelët" : "Kalo te tema e errët"}
            className="grid h-9 w-9 place-items-center rounded-lg border border-ink-200 text-ink-500 transition hover:bg-ink-100 dark:border-ink-800 dark:hover:bg-ink-800"
          >
            {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
        </div>
      </header>

      <div className="flex">
        <Rail view={view} onView={onView} onKeyDown={onTabKeyDown} />
        {/* `role="tabpanel"` mbi vetë `<main>` do ta mbivendoste rolin e tij të
            nënkuptuar dhe faqja do të mbetej pa landmark kryesor. Të dy rolet i
            duhen, te elemente të ndara. */}
        <main id="content" tabIndex={-1} className="min-w-0 flex-1 p-4 sm:p-6">
          <div role="tabpanel" aria-labelledby={`tab-${view}`}>
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

function Rail({
  view,
  onView,
  onKeyDown,
}: {
  view: View;
  onView: (view: View) => void;
  onKeyDown?: (event: React.KeyboardEvent) => void;
}) {
  const items = [
    { id: "overview" as const, icon: LayoutDashboard, label: "Analizo një projekt" },
    { id: "metrics" as const, icon: Gauge, label: "Rezultatet e vlerësimit" },
  ];
  return (
    <nav
      aria-label="Pamjet"
      role="tablist"
      aria-orientation="vertical"
      className="sticky top-14 flex h-[calc(100vh-3.5rem)] w-14 shrink-0 flex-col items-center gap-1 border-r border-ink-200 bg-white py-3 dark:border-ink-800 dark:bg-ink-900"
    >
      {items.map((item) => (
        <button
          key={item.id}
          role="tab"
          id={`tab-${item.id}`}
          onClick={() => onView(item.id)}
          onKeyDown={onKeyDown}
          title={item.label}
          aria-selected={view === item.id}
          tabIndex={view === item.id ? 0 : -1}
          className={`grid h-10 w-10 place-items-center rounded-lg transition ${
            view === item.id
              ? "bg-brand-600 text-white"
              : "text-ink-400 hover:bg-ink-100 hover:text-ink-700 dark:hover:bg-ink-800 dark:hover:text-ink-100"
          }`}
        >
          <item.icon className="h-[18px] w-[18px]" aria-hidden="true" />
          <span className="sr-only">{item.label}</span>
        </button>
      ))}
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
        <div className="flex items-center justify-between gap-3 border-b border-ink-200 px-4 py-3 dark:border-ink-800">
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

/** Rreshti i statusit te shiriti: fakte të shkurtra, të ndara me pika. */
export function StatusStrip({ items }: { items: (string | null)[] }) {
  const shown = items.filter((item): item is string => Boolean(item));
  if (shown.length === 0) return null;
  return (
    <div className="hidden items-center gap-2.5 text-xs text-ink-500 lg:flex dark:text-ink-400">
      {shown.map((item, index) => (
        <span key={item} className="flex items-center gap-2.5">
          {index > 0 && <span className="text-ink-300 dark:text-ink-700">·</span>}
          {item}
        </span>
      ))}
    </div>
  );
}
