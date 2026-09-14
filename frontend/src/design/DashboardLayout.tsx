// Korniza: shirit sipër, rresht pamjesh majtas, përmbajtja djathtas.
//
// Gjerësia nuk kufizohet: një panel kontrolli lexohet paralelisht, dhe margjinat
// e një faqeje e kthejnë atë në dokument me tabela brenda.
//
// Asgjë këtu nuk di nga vijnë të dhënat. Shiriti merr një nyje për zgjedhësin e
// projektit dhe një për statusin, që i njëjti komponent të shërbejë faqen e
// dizajnit me të dhëna të rreme dhe aplikacionin me ato të vërteta (VD-106).
//
// Pa logon me ikonë dhe pa etiketa me shkronja kapitale: emri i mjetit është
// shenja e tij, dhe titujt lexohen si fjali (VD-119).

import { Gauge, LayoutDashboard, Moon, Play, Square, Sun } from "lucide-react";

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
    <div className="min-h-screen bg-ink-100 font-sans text-ink-800 dark:bg-ink-950 dark:text-ink-200">
      {/* Lidhja e parë te rendi i tabulimit, e padukshme derisa merr fokusin. Pa
          të, një përdorues me tastierë kalon çdo herë nëpër kokë dhe nëpër rresht
          para se të arrijë te përmbajtja. */}
      <a
        href="#content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-brand-600 focus:px-3 focus:py-2 focus:text-sm focus:text-white"
      >
        Kalo te përmbajtja
      </a>
      <header className="sticky top-0 z-20 flex h-auto min-h-14 flex-wrap items-center gap-x-5 gap-y-2 border-b border-ink-200 bg-white px-4 py-2 sm:flex-nowrap sm:py-0 dark:border-ink-800 dark:bg-ink-900">
        {/* `h1` e jo `span`: faqja duhet të ketë një titull të nivelit të parë,
            dhe emri i mjetit është i vetmi kandidat që qëndron te të dyja pamjet. */}
        <h1 className="m-0 shrink-0 text-[17px] font-semibold tracking-[-0.01em] text-ink-900 dark:text-white">
          JavaSmell
        </h1>

        {project}

        <div className="ml-auto flex shrink-0 items-center gap-3">
          {status}
          {busy && onStop ? (
            <button
              onClick={onStop}
              className="flex h-9 items-center gap-2 rounded-md border border-ink-300 bg-transparent px-3.5 text-sm font-medium text-ink-700 transition hover:bg-ink-100 dark:border-ink-700 dark:text-ink-200 dark:hover:bg-ink-800"
            >
              <Square className="h-3.5 w-3.5" />
              Ndalo
            </button>
          ) : (
            <button
              onClick={onScan}
              disabled={busy || !canScan}
              className="flex h-9 items-center gap-2 rounded-md border-0 bg-brand-600 px-3.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500"
            >
              <Play className="h-4 w-4" />
              {busy ? "Duke skanuar…" : scanLabel}
            </button>
          )}
          <button
            onClick={onTheme}
            aria-label={dark ? "Kalo te tema e çelët" : "Kalo te tema e errët"}
            className="grid h-9 w-9 place-items-center rounded-md border border-ink-200 bg-transparent p-0 text-ink-500 transition hover:bg-ink-100 dark:border-ink-800 dark:text-ink-400 dark:hover:bg-ink-800"
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
  // Emri i shkurtër shihet, i gjati lexohet. Me dy pamje, një ikonë pa fjalë e
  // detyronte dikë që e sheh mjetin për herë të parë të rrinte me miun sipër saj
  // për ta mësuar se çfarë hap (VD-119).
  const items = [
    { id: "overview" as const, icon: LayoutDashboard, short: "Analiza", label: "Analizo një projekt" },
    { id: "metrics" as const, icon: Gauge, short: "Vlerësimi", label: "Rezultatet e vlerësimit" },
  ];
  return (
    /* `role="tablist"` mbi vetë `<nav>` e mbivendos rolin e tij `navigation`, dhe
       faqja mbetet me përmbajtje jashtë çdo landmark-u. Të dy rolet i duhen, te
       elemente të ndara — e njëjta gjë si `<main>` dhe `tabpanel` më lart. */
    <nav
      aria-label="Pamjet"
      className="sticky top-14 h-[calc(100vh-3.5rem)] w-[76px] shrink-0 border-r border-ink-200 bg-white py-3 dark:border-ink-800 dark:bg-ink-900"
    >
      <div
        role="tablist"
        aria-label="Pamjet"
        aria-orientation="vertical"
        className="flex flex-col items-center gap-1"
      >
        {items.map((item) => {
          const on = view === item.id;
          return (
            <button
              key={item.id}
              role="tab"
              id={`tab-${item.id}`}
              onClick={() => onView(item.id)}
              onKeyDown={onKeyDown}
              title={item.label}
              aria-selected={on}
              tabIndex={on ? 0 : -1}
              className={`relative flex h-auto w-[64px] flex-col items-center gap-1 rounded-md border-0 px-0 py-2 text-[11.5px] font-medium transition ${
                on
                  ? "bg-brand-600/10 text-brand-ink"
                  : "bg-transparent text-ink-500 hover:bg-ink-100 hover:text-ink-800 dark:text-ink-400 dark:hover:bg-ink-800 dark:hover:text-ink-100"
              }`}
            >
              {on && (
                <span
                  className="absolute top-2 bottom-2 -left-1.5 w-[3px] rounded-r-sm bg-brand-600 dark:bg-brand-400"
                  aria-hidden="true"
                />
              )}
              <item.icon className="h-[18px] w-[18px]" aria-hidden="true" />
              <span aria-hidden="true">{item.short}</span>
              <span className="sr-only">{item.label}</span>
            </button>
          );
        })}
      </div>
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
      className={`min-w-0 rounded-lg border border-ink-200 bg-white dark:border-ink-800 dark:bg-ink-900 ${className}`}
    >
      {/* Titulli si fjali mbi përmbajtjen, jo si shirit me kufi poshtë: shiriti
          hante 56 piksela te çdo kartë dhe e ndante titullin nga ajo që emërton. */}
      {title && (
        <div className="flex items-baseline justify-between gap-3 px-4 pt-3.5 pb-1">
          <h2 className="m-0 text-[14px] font-semibold text-ink-900 dark:text-ink-100">{title}</h2>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

/** Rreshti i statusit te shiriti: fakte të shkurtra, të ndara me hapësirë. */
export function StatusStrip({ items }: { items: (string | null)[] }) {
  const shown = items.filter((item): item is string => Boolean(item));
  if (shown.length === 0) return null;
  return (
    <div className="hidden items-center gap-4 text-xs text-ink-500 tabular-nums lg:flex dark:text-ink-400">
      {shown.map((item) => (
        <span key={item}>{item}</span>
      ))}
    </div>
  );
}
