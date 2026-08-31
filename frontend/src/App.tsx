import { useMemo, useRef, useState } from "react";
import { analyse, preview } from "./api";
import { Diff } from "./Diff";
import { Results } from "./Results";
import type { Analysis, Preview, Severity, Smell } from "./types";

const SEVERITY_ORDER: Record<Severity, number> = { critical: 0, major: 1, minor: 2 };

type Screen =
  | { state: "idle" }
  | { state: "loading" }
  | { state: "error"; message: string }
  | { state: "ready"; analysis: Analysis };

// Dy pamje, pa router: një bibliotekë rrugëzimi për dy gjendje do të ishte më
// shumë kod se vetë kalimi mes tyre.
type View = "analysis" | "results";

export function App() {
  const [view, setView] = useState<View>("analysis");
  const [path, setPath] = useState("");
  const [screen, setScreen] = useState<Screen>({ state: "idle" });
  const [severity, setSeverity] = useState<Severity | "all">("all");
  const [kind, setKind] = useState<string>("all");
  const [selected, setSelected] = useState<Smell | null>(null);
  const listRef = useRef<HTMLElement>(null);

  async function run(event: React.FormEvent) {
    event.preventDefault();
    setScreen({ state: "loading" });
    setSelected(null);
    try {
      setScreen({ state: "ready", analysis: await analyse(path) });
    } catch (failure) {
      setScreen({ state: "error", message: (failure as Error).message });
    }
  }

  const smells = screen.state === "ready" ? screen.analysis.smells : [];
  const shown = useMemo(
    () =>
      smells
        .filter((s) => severity === "all" || s.severity === severity)
        .filter((s) => kind === "all" || s.smell_type === kind)
        .sort(
          (a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity] || b.score - a.score,
        ),
    [smells, severity, kind],
  );

  /**
   * Up and down move through the findings.
   *
   * The list is the part a reader walks: a hundred rows read one after another
   * while the detail beside them changes. Reaching for the mouse for each one
   * makes that a chore, and the rows are already buttons, so the only thing
   * missing is moving the focus with the selection.
   */
  function navigate(event: React.KeyboardEvent) {
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    if (shown.length === 0) return;
    event.preventDefault();

    const current = selected ? shown.indexOf(selected) : -1;
    const step = event.key === "ArrowDown" ? 1 : -1;
    const next = Math.min(Math.max(current + step, 0), shown.length - 1);
    setSelected(shown[next]);
    listRef.current?.querySelectorAll<HTMLButtonElement>("button.row")[next]?.focus();
  }

  return (
    <div className="page">
      <header>
        <h1>JavaSmell</h1>
        <p className="tagline">Detektim i code smells dhe rekomandime refaktorimi</p>
        <nav className="tabs">
          <button
            className={view === "analysis" ? "tab on" : "tab"}
            onClick={() => setView("analysis")}
            aria-pressed={view === "analysis"}
          >
            Analizo një projekt
          </button>
          <button
            className={view === "results" ? "tab on" : "tab"}
            onClick={() => setView("results")}
            aria-pressed={view === "results"}
          >
            Rezultatet e vlerësimit
          </button>
        </nav>
      </header>

      {view === "results" && <Results />}

      {view === "analysis" && (
      <>
      <form className="search" onSubmit={run}>
        <input
          value={path}
          onChange={(e) => setPath(e.target.value)}
          placeholder="Shtegu i projektit, brenda dosjes së lejuar"
          aria-label="Shtegu i projektit"
        />
        <button type="submit" disabled={screen.state === "loading" || !path.trim()}>
          {screen.state === "loading" ? "Duke analizuar…" : "Analizo"}
        </button>
      </form>

      {screen.state === "idle" && (
        <p className="empty">
          Shkruaj shtegun e një projekti Java për të filluar. Analiza lexon vetëm brenda dosjes
          që serveri e ka të lejuar.
        </p>
      )}

      {screen.state === "loading" && <p className="empty">Duke matur skedarët…</p>}

      {screen.state === "error" && (
        <p className="failure" role="alert">
          {screen.message}
        </p>
      )}

      {screen.state === "ready" && (
        <>
          <SummaryBar analysis={screen.analysis} />

          {screen.analysis.smells.length === 0 ? (
            <p className="empty">Asnjë erë e detektuar. Kodi kaloi çdo strategji.</p>
          ) : (
            <div className="layout">
              <section className="list" ref={listRef} onKeyDown={navigate}>
                <Filters
                  analysis={screen.analysis}
                  severity={severity}
                  kind={kind}
                  onSeverity={setSeverity}
                  onKind={setKind}
                />
                <p className="count">
                  {shown.length} nga {screen.analysis.smells.length}
                </p>
                <ul>
                  {shown.map((smell, index) => (
                    <li key={`${smell.file_path}:${smell.start_line}:${smell.smell_type}:${index}`}>
                      <button
                        className={`row ${smell.severity}${selected === smell ? " selected" : ""}`}
                        onClick={() => setSelected(smell)}
                        aria-current={selected === smell}
                      >
                        <span className="mark" aria-hidden="true" />
                        <span>
                          <span className="headline">
                            <span className="kind">{smell.smell_type}</span>
                            <span className="where">
                              {smell.class_name}
                              {smell.method ? `.${smell.method.replace(/\(.*$/, "")}` : ""}
                            </span>
                            <span className="grade">{smell.severity}</span>
                          </span>
                          <span className="file">
                            {smell.file_path}:{smell.start_line}
                          </span>
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </section>

              <section className="detail">
                {selected ? <Detail smell={selected} path={path} /> : (
                  <p className="empty">Zgjidh një erë nga lista për ta parë arsyen.</p>
                )}
              </section>
            </div>
          )}
        </>
      )}
      </>
      )}
    </div>
  );
}

function SummaryBar({ analysis }: { analysis: Analysis }) {
  const { summary } = analysis;
  return (
    <div className="summary">
      <Figure value={summary.files} label="skedarë" />
      <Figure value={summary.classes} label="klasa" />
      <Figure value={summary.methods} label="metoda" />
      <Figure value={summary.smells} label="erëra" accent />
      {(["critical", "major", "minor"] as const).map((level) =>
        summary.by_severity[level] ? (
          <Figure key={level} value={summary.by_severity[level]} label={level} tone={level} />
        ) : null,
      )}
    </div>
  );
}

function Figure({
  value,
  label,
  accent,
  tone,
}: {
  value: number;
  label: string;
  accent?: boolean;
  tone?: Severity;
}) {
  return (
    <div className={`figure${accent ? " accent" : ""}${tone ? ` ${tone}` : ""}`}>
      <b>{value}</b>
      <span>{label}</span>
    </div>
  );
}

function Filters({
  analysis,
  severity,
  kind,
  onSeverity,
  onKind,
}: {
  analysis: Analysis;
  severity: Severity | "all";
  kind: string;
  onSeverity: (value: Severity | "all") => void;
  onKind: (value: string) => void;
}) {
  return (
    <div className="filters">
      <label>
        Ashpërsia
        <select value={severity} onChange={(e) => onSeverity(e.target.value as Severity | "all")}>
          <option value="all">të gjitha</option>
          <option value="critical">critical</option>
          <option value="major">major</option>
          <option value="minor">minor</option>
        </select>
      </label>
      <label>
        Lloji
        <select value={kind} onChange={(e) => onKind(e.target.value)}>
          <option value="all">të gjitha</option>
          {Object.keys(analysis.summary.by_type).map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

function Detail({ smell, path }: { smell: Smell; path: string }) {
  const [result, setResult] = useState<Preview | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  async function ask() {
    setBusy(true);
    setFailure(null);
    setResult(null);
    try {
      setResult(await preview(path, smell));
    } catch (error) {
      setFailure((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <article>
      <h2>{smell.smell_type}</h2>
      <p className="where">
        {smell.package ? `${smell.package}.` : ""}
        {smell.class_name}
        {smell.method ? `.${smell.method}` : ""}
      </p>
      <p className="file">
        {smell.file_path}:{smell.start_line}–{smell.end_line}
      </p>

      <h3>Pse u shënua</h3>
      <Conditions smell={smell} />
      {smell.conditions.length > 0 && <p className="note caption">{EXCESS_NOTE}</p>}

      <h3>Metrikat e matura</h3>
      <table className="metrics">
        <tbody>
          {Object.entries(smell.metrics).map(([name, value]) => (
            <tr key={name}>
              <th>{name}</th>
              <td>{value}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Refaktorimet e propozuara</h3>
      <ul className="refactorings">
        {smell.refactorings.map((name) => (
          <li key={name}>{name}</li>
        ))}
      </ul>

      {smell.automated ? (
        <button className="primary" onClick={ask} disabled={busy}>
          {busy ? "Duke përgatitur…" : "Shfaq ndryshimin e propozuar"}
        </button>
      ) : (
        <p className="note">
          Motori nuk e aplikon automatikisht këtë refaktorim: ai kërkon gjetjen e çdo reference
          në projekt, çka analiza nuk e provon dot. Mbetet propozim për autorin.
        </p>
      )}

      {failure && (
        <p className="failure" role="alert">
          {failure}
        </p>
      )}

      {result && !result.applied && (
        <p className="note">
          Motori refuzoi ta aplikojë: <b>{result.refusal}</b>
          {result.detail ? ` — ${result.detail}` : ""}. Refuzimi është rezultat i saktë, jo
          dështim.
        </p>
      )}

      {result?.applied && result.before && result.after && (
        <Diff before={result.before} after={result.after} />
      )}
    </article>
  );
}

/**
 * Why the detector fired: the measurement beside the bound it passed.
 *
 * The API sends the clauses as data as well as as a sentence, so the value and
 * the threshold can be put in the same column and compared by eye. The bar is
 * the excess — how far past the bound the measurement sits — on the same 5x cap
 * the severity score uses, so a reader who has seen one has seen the other.
 */
function Conditions({ smell }: { smell: Smell }) {
  if (smell.conditions.length === 0) {
    return <p className="empty">{smell.rationale}</p>;
  }

  return (
    <table className="conditions">
      <tbody>
        {smell.conditions.map((condition) => {
          const above = condition.operator.startsWith(">");
          const excess = above
            ? condition.value / (condition.threshold || 1)
            : (condition.threshold || 1) / (condition.value || 0.001);
          const width = Math.min(Math.max(excess, 1), 5) / 5;
          return (
            <tr key={`${condition.metric}${condition.operator}`}>
              <th>{condition.metric}</th>
              <td className="measured">{condition.value}</td>
              <td className="bound">
                {condition.operator} {condition.threshold}
              </td>
              <td className="excess">
                <span style={{ width: `${width * 100}%` }} title={`${excess.toFixed(1)}×`} />
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

/**
 * The bar needs one sentence, because it is not a progress bar.
 *
 * It is the excess the severity score is built from, on the same 5x cap. Saying
 * so also exposes the oddity the thesis reports in section 5.6: a permissive
 * clause like `FDP <= 5` reads as a large excess when the measurement sits far
 * below it, which is one of the reasons the derived severity does not track the
 * reviewers' judgement.
 */
const EXCESS_NOTE =
  "Shiriti tregon tepricën mbi kufirin, e kufizuar në 5× — e njëjta madhësi nga e cila " +
  "derivohet ashpërsia.";
