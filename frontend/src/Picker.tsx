// Zgjedhja e projektit pa shkruar shteg: dosje me klikim, ose depo nga GitHub.
//
// Deri tani hyrja e vetme ishte një kuti teksti, dhe ajo kërkonte nga përdoruesi
// të dinte paraprakisht shtegun e plotë e të mos e shtypte gabim. Gjatë
// demonstrimit ky ishte gabimi i vetëm që u përsërit: shtegu relativ punonte me
// një server dhe jo me tjetrin, dhe mesazhi «del jashtë dosjes së lejuar» nuk i
// thoshte se ku ishte kufiri (VD-126).
//
// Dy rrugë hyrjeje sepse nisjet janë dy: kodi që dikush e ka në kompjuter, dhe
// kodi që dikush do ta provojë pa e shkarkuar vetë.

import { useCallback, useEffect, useRef, useState } from "react";
import { Download, FolderOpen, Github, Loader2 } from "lucide-react";
import { browse, importRepository } from "./api";
import type { Folder, Listing } from "./types";

type Tab = "folders" | "github";

/** Sa shtigje të përdorura së fundi mbahen; më tepër do të ishin listë e dytë. */
export const RECENT = 5;

export function Picker({
  open,
  recent,
  onChoose,
  onClose,
}: {
  open: boolean;
  recent: string[];
  onChoose: (path: string) => void;
  onClose: () => void;
}) {
  const [tab, setTab] = useState<Tab>("folders");
  const dialog = useRef<HTMLDivElement>(null);

  // Escape mbyll, si te çdo dialog. Pa të, i vetmi dalje ishte butoni, dhe një
  // dialog që kapet me tastierë por nuk lëshohet me tastierë është gjysma e punës.
  //
  // Fokusi mbyllet brenda dialogut dhe kthehet aty ku ishte kur ai mbyllet
  // (VD-127). Pa të, Tab-i kalonte te faqja pas perdes, e padukshme për
  // përdoruesin e tastierës, dhe pas mbylljes fokusi binte te fundi i faqes.
  useEffect(() => {
    if (!open) return;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    function onKey(event: KeyboardEvent): void {
      if (event.key === "Escape") onClose();
      if (event.key === "Tab" && dialog.current) trapFocus(event, dialog.current);
    }
    window.addEventListener("keydown", onKey);
    dialog.current?.focus();
    return () => {
      window.removeEventListener("keydown", onKey);
      if (opener?.isConnected) opener.focus();
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-ink-950/50 p-4 sm:items-center"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby="picker-title"
        tabIndex={-1}
        className="w-full max-w-2xl rounded-xl border border-ink-200 bg-white shadow-xl outline-none dark:border-ink-700 dark:bg-ink-900"
      >
        <header className="flex items-center justify-between gap-3 border-b border-ink-200 px-4 py-3 dark:border-ink-700">
          <h2 id="picker-title" className="text-sm font-semibold text-ink-900 dark:text-ink-100">
            Zgjidh një projekt Java
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-2 py-1 text-xs text-ink-500 hover:bg-ink-100 dark:text-ink-400 dark:hover:bg-ink-800"
          >
            Mbyll
          </button>
        </header>

        <div
          role="tablist"
          aria-label="Nga ku vjen projekti"
          className="flex gap-1 border-b border-ink-200 px-4 pt-3 dark:border-ink-700"
        >
          <TabButton
            id="picker-tab-folders"
            active={tab === "folders"}
            onClick={() => setTab("folders")}
          >
            <FolderOpen className="h-3.5 w-3.5" aria-hidden="true" /> Nga kompjuteri
          </TabButton>
          <TabButton
            id="picker-tab-github"
            active={tab === "github"}
            onClick={() => setTab("github")}
          >
            <Github className="h-3.5 w-3.5" aria-hidden="true" /> Nga GitHub
          </TabButton>
        </div>

        <div id="picker-panel" role="tabpanel" aria-labelledby={`picker-tab-${tab}`}>
          {tab === "folders" ? (
            <Folders recent={recent} onChoose={onChoose} />
          ) : (
            <FromGithub onChoose={onChoose} />
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Tab-i te elementi i fundit kthehet te i pari, dhe Shift+Tab te i pari te i fundi.
 *
 * Elementet lexohen në çast e jo një herë, sepse lista e dosjeve ndryshon sa
 * herë hyhet në një dosje tjetër.
 */
function trapFocus(event: KeyboardEvent, container: HTMLElement): void {
  const focusable = Array.from(
    container.querySelectorAll<HTMLElement>(
      'button:not([disabled]), input:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
    ),
  );
  if (focusable.length === 0) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  const active = document.activeElement;
  if (event.shiftKey && (active === first || active === container)) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && active === last) {
    event.preventDefault();
    first.focus();
  }
}

function TabButton({
  id,
  active,
  onClick,
  children,
}: {
  id: string;
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      id={id}
      type="button"
      role="tab"
      aria-selected={active}
      aria-controls="picker-panel"
      onClick={onClick}
      className={`-mb-px flex h-auto items-center gap-1.5 rounded-none border-0 border-b-2 bg-transparent px-3 py-2 text-xs font-medium ${
        active
          ? "border-brand-500 text-brand-700 dark:text-brand-300"
          : "border-transparent text-ink-500 hover:text-ink-800 dark:text-ink-400 dark:hover:text-ink-200"
      }`}
    >
      {children}
    </button>
  );
}

/** Shfletimi i dosjeve brenda atyre që serveri i lexon. */
function Folders({ recent, onChoose }: { recent: string[]; onChoose: (path: string) => void }) {
  const [listing, setListing] = useState<Listing | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Numri i kërkesës së fundit. Vetëm përgjigjja e saj pranohet: dy klikime të
  // shpejta mbi dosje të ndryshme mund të kthehen në radhë të kundërt, dhe e
  // vonuara do të mbishkruante listën e dosjes që përdoruesi zgjodhi i fundit.
  const latest = useRef(0);

  const load = useCallback((path: string, first = false) => {
    const ticket = ++latest.current;
    setBusy(true);
    setFailure(null);
    browse(path)
      // Kur rrënja është e vetme, lista e rrënjëve do të ishte një rresht i
      // vetëm për t'u klikuar para se puna të nisë, ndaj hyhet drejt brenda saj.
      .then((next) => (first && next.roots.length === 1 ? browse(next.roots[0].path) : next))
      .then((next) => {
        if (ticket === latest.current) setListing(next);
      })
      .catch((error: Error) => {
        if (ticket === latest.current) setFailure(error.message);
      })
      .finally(() => {
        if (ticket === latest.current) setBusy(false);
      });
  }, []);

  // Hapet te rrënjët, që lista të mos kërkojë asnjë dijeni paraprake. Pas
  // mbylljes, një përgjigje e vonuar nuk ka ku të bjerë: numri i kërkesës
  // rritet, dhe ajo injorohet.
  useEffect(() => {
    load("", true);
    return () => {
      latest.current += 1;
    };
  }, [load]);

  const here = listing?.path ?? "";

  return (
    <div className="px-4 py-3">
      {recent.length > 0 && (
        <section className="mb-3">
          <h3 className="mb-1.5 text-xs font-medium text-ink-500 dark:text-ink-400">
            Të hapura së fundi
          </h3>
          <ul className="m-0 flex list-none flex-wrap gap-1.5 p-0">
            {recent.map((path) => (
              <li key={path}>
                <button
                  type="button"
                  onClick={() => onChoose(path)}
                  title={path}
                  className="max-w-[18rem] truncate rounded-md border border-ink-200 px-2 py-1 font-mono text-xs text-ink-700 hover:border-brand-500 hover:text-brand-700 dark:border-ink-700 dark:text-ink-300 dark:hover:text-brand-300"
                >
                  {path.split(/[\\/]/).filter(Boolean).slice(-2).join("/")}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="mb-2 flex items-center gap-2">
        <button
          type="button"
          disabled={!listing?.parent && here === ""}
          onClick={() => load(listing?.parent ?? "")}
          className="shrink-0 rounded-md border border-ink-200 px-2 py-1 text-xs text-ink-700 disabled:opacity-40 dark:border-ink-700 dark:text-ink-300"
        >
          {here === "" ? "Rrënjët" : "↑ Lart"}
        </button>
        <p
          className="min-w-0 flex-1 truncate font-mono text-xs text-ink-500 dark:text-ink-400"
          title={here}
        >
          {here === "" ? "Dosjet që serveri i lexon" : here}
        </p>
      </div>

      {failure && (
        <p
          className="mb-2 rounded-md bg-rose-50 px-2 py-1.5 text-xs text-rose-700 dark:bg-rose-950 dark:text-rose-300"
          role="alert"
        >
          {failure}
        </p>
      )}

      <ul className="m-0 max-h-72 list-none overflow-y-auto rounded-md border border-ink-200 p-0 dark:border-ink-700">
        {busy && listing === null && <Row>Duke lexuar…</Row>}
        {listing?.folders.length === 0 && <Row>Asnjë nënndosje këtu.</Row>}
        {listing?.folders.map((folder) => (
          <li
            key={folder.path}
            className="border-b border-ink-100 last:border-0 dark:border-ink-800"
          >
            <button
              type="button"
              onClick={() => load(folder.path)}
              className="flex h-auto w-full items-center gap-2 rounded-none border-0 bg-transparent px-3 py-2 text-left text-sm text-ink-800 hover:bg-ink-50 dark:text-ink-200 dark:hover:bg-ink-800"
            >
              <FolderOpen className="h-4 w-4 shrink-0 text-ink-400" aria-hidden="true" />
              <span className="min-w-0 flex-1 truncate">{folder.name}</span>
              <JavaMark folder={folder} />
            </button>
          </li>
        ))}
      </ul>

      <footer className="mt-3 flex items-center justify-between gap-3">
        <p className="text-xs text-ink-500 dark:text-ink-400">
          Kliko një dosje për të hyrë brenda, pastaj «Analizo këtë dosje».
        </p>
        <button
          type="button"
          disabled={here === "" || busy}
          onClick={() => onChoose(here)}
          className="shrink-0 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 disabled:opacity-40"
        >
          Analizo këtë dosje
        </button>
      </footer>
    </div>
  );
}

/**
 * A ka kod Java brenda, sipas serverit.
 *
 * Tri gjendje e jo dy: «nuk e dita» del kur kërkimi ndalet te kufiri, dhe ajo
 * nuk guxon të dukej si «nuk ka kod», sepse dosja mund të jetë pikërisht ajo që
 * përdoruesi kërkon.
 */
function JavaMark({ folder }: { folder: Folder }) {
  if (folder.java === true) {
    return (
      <span className="shrink-0 rounded bg-emerald-100 px-1.5 py-0.5 text-[0.65rem] font-medium text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
        Java
      </span>
    );
  }
  if (folder.java === null) {
    return (
      <span
        className="shrink-0 text-[0.65rem] text-ink-400"
        title="Dosja është e madhe; kërkimi u ndal para se të gjendej kod Java."
      >
        e madhe
      </span>
    );
  }
  return <span className="shrink-0 text-[0.65rem] text-ink-400">pa Java</span>;
}

function Row({ children }: { children: React.ReactNode }) {
  return <li className="px-3 py-2 text-sm text-ink-500 dark:text-ink-400">{children}</li>;
}

/** Importi i një depoje publike nga një lidhje. */
function FromGithub({ onChoose }: { onChoose: (path: string) => void }) {
  const [url, setUrl] = useState("");
  // API-ja e pranonte rishkarkimin, por ndërfaqja nuk e dërgonte kurrë: kush e
  // importoi një depo dje nuk e merrte dot versionin e sotëm (VD-127).
  const [refresh, setRefresh] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  function submit(event: React.FormEvent): void {
    event.preventDefault();
    if (!url.trim() || busy) return;
    setBusy(true);
    setFailure(null);
    importRepository(url.trim(), { refresh })
      .then((imported) => onChoose(imported.path))
      .catch((error: Error) => setFailure(error.message))
      .finally(() => setBusy(false));
  }

  return (
    <form className="px-4 py-3" onSubmit={submit}>
      <label
        htmlFor="picker-url"
        className="mb-1.5 block text-xs font-medium text-ink-500 dark:text-ink-400"
      >
        Lidhja e një depoje publike
      </label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          id="picker-url"
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="https://github.com/jhy/jsoup"
          className="h-9 min-w-0 flex-1 rounded-lg border border-ink-200 bg-white px-3 font-mono text-sm text-ink-900 placeholder:text-ink-400 focus-visible:border-brand-500 focus-visible:ring-2 focus-visible:ring-brand-500/25 focus-visible:outline-none dark:border-ink-700 dark:bg-ink-950 dark:text-ink-100"
        />
        <button
          type="submit"
          disabled={!url.trim() || busy}
          className="flex shrink-0 items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 disabled:opacity-40"
        >
          {busy ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
          ) : (
            <Download className="h-3.5 w-3.5" aria-hidden="true" />
          )}
          {busy ? "Duke shkarkuar…" : "Shkarko dhe analizo"}
        </button>
      </div>

      {failure && (
        <p
          className="mt-2 rounded-md bg-rose-50 px-2 py-1.5 text-xs text-rose-700 dark:bg-rose-950 dark:text-rose-300"
          role="alert"
        >
          {failure}
        </p>
      )}

      <label className="mt-3 flex items-center gap-2 text-xs text-ink-700 dark:text-ink-300">
        <input
          type="checkbox"
          checked={refresh}
          onChange={(event) => setRefresh(event.target.checked)}
          className="h-3.5 w-3.5 accent-brand-600"
        />
        Shkarko versionin më të ri, edhe nëse depoja është importuar më parë
      </label>

      <p className="mt-3 text-xs text-ink-500 dark:text-ink-400">
        Shkarkohen vetëm skedarët «.java», te një dosje brenda mjetit. Kodi lexohet dhe kompilohet
        për verifikim, por nuk ekzekutohet kurrë. Depo private nuk importohen.
      </p>
      <p className="mt-1.5 text-xs text-ink-500 dark:text-ink-400">
        Pranohen edhe forma «pronari/depoja» dhe lidhja e një dege, p.sh.
        <code className="ml-1">github.com/jhy/jsoup/tree/master</code>.
      </p>
    </form>
  );
}
