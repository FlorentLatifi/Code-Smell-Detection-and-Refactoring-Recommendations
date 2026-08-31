import { useMemo, useRef, useState } from "react";
import { analyse } from "./api";
import { Detail } from "./Detail";
import { SMELL_SQ } from "./evaluation";
import { agreementOn, indexModel } from "./model";
import { Results } from "./Results";
import type { Analysis, ModelBlock, Severity, Smell } from "./types";

const SEVERITY_ORDER: Record<Severity, number> = { critical: 0, major: 1, minor: 2 };

/** How the list is ordered. Severity first is the default a reader wants. */
type Order = "severity" | "score" | "file";

const ORDER_LABELS: Record<Order, string> = {
  severity: "ashpërsia",
  score: "teprica",
  file: "skedari",
};

const REMEMBERED_PATH = "javasmell.path";

/**
 * The last path analysed, so the tool opens where it was left.
 *
 * Wrapped because storage is not always there to be read: a private window or a
 * browser set to block site data throws on access rather than returning null,
 * and an interface that will not render without a convenience is worse than one
 * without the convenience.
 */
function remembered(key: string): string {
  try {
    return window.localStorage.getItem(key) ?? "";
  } catch {
    return "";
  }
}

function remember(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Nothing to do and nothing worth telling the user.
  }
}

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
  const [path, setPath] = useState(() => remembered(REMEMBERED_PATH));
  const [screen, setScreen] = useState<Screen>({ state: "idle" });
  const [severity, setSeverity] = useState<Severity | "all">("all");
  const [kind, setKind] = useState<string>("all");
  const [query, setQuery] = useState("");
  const [order, setOrder] = useState<Order>("severity");
  // Whether the model was asked, kept apart from whether it answered: an
  // untrained checkout has no models, and the difference has to stay visible.
  const [askModel, setAskModel] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [selected, setSelected] = useState<Smell | null>(null);
  const listRef = useRef<HTMLElement>(null);

  async function run(event: React.FormEvent) {
    event.preventDefault();
    setScreen({ state: "loading" });
    setSelected(null);
    try {
      setScreen({ state: "ready", analysis: await analyse(path, askModel) });
      remember(REMEMBERED_PATH, path);
    } catch (failure) {
      setScreen({ state: "error", message: (failure as Error).message });
    }
  }

  const smells = screen.state === "ready" ? screen.analysis.smells : [];
  const model = useMemo(
    () => (screen.state === "ready" ? indexModel(screen.analysis.model) : null),
    [screen],
  );
  const shown = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const matches = (smell: Smell) =>
      needle === "" ||
      `${smell.class_name} ${smell.method ?? ""} ${smell.file_path} ${smell.smell_type}`
        .toLowerCase()
        .includes(needle);

    // Sorted into a copy: `smells` belongs to the analysis, and sorting it in
    // place would reorder what the summary was counted from.
    const ordered = smells
      .filter((s) => severity === "all" || s.severity === severity)
      .filter((s) => kind === "all" || s.smell_type === kind)
      .filter((s) => !agreed || agreementOn(model, s) !== null)
      .filter(matches);

    if (order === "file") {
      return ordered.sort(
        (a, b) => a.file_path.localeCompare(b.file_path) || a.start_line - b.start_line,
      );
    }
    if (order === "score") {
      return ordered.sort((a, b) => b.score - a.score);
    }
    return ordered.sort(
      (a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity] || b.score - a.score,
    );
  }, [smells, severity, kind, query, order, agreed, model]);

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
        <label className="ask" title="Kërkon modele të trajnuara dhe matje mbi tërë projektin">
          <input
            type="checkbox"
            checked={askModel}
            aria-label="Pyet edhe modelin"
            onChange={(e) => setAskModel(e.target.checked)}
          />
          Pyet edhe modelin
        </label>
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
          {screen.analysis.model && <ModelBar block={screen.analysis.model} />}

          {screen.analysis.smells.length === 0 ? (
            <p className="empty">Asnjë erë e detektuar. Kodi kaloi çdo strategji.</p>
          ) : (
            <div className="layout">
              <section className="list" ref={listRef} onKeyDown={navigate}>
                <Filters
                  analysis={screen.analysis}
                  severity={severity}
                  kind={kind}
                  order={order}
                  query={query}
                  agreed={agreed}
                  hasModel={model !== null}
                  onSeverity={setSeverity}
                  onKind={setKind}
                  onOrder={setOrder}
                  onQuery={setQuery}
                  onAgreed={setAgreed}
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
                            <span className="grade">
                              {agreementOn(model, smell) && (
                                <abbr className="both" title="Modeli e shënoi po ashtu">
                                  A∩B
                                </abbr>
                              )}
                              {smell.automated && (
                                <abbr className="auto" title="Motori e rishkruan vetë">
                                  ✎
                                </abbr>
                              )}
                              {smell.severity}
                            </span>
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
                {selected ? (
                  <Detail
                    smell={selected}
                    path={path}
                    prediction={agreementOn(model, selected)}
                    asked={model !== null}
                  />
                ) : (
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

/**
 * What the second approach found, kept apart from what the rules found.
 *
 * Deliberately its own row rather than numbers folded into the summary. The two
 * approaches are not interchangeable: A's count is of published strategies
 * firing, B's is of a classifier trained on how reviewers labelled MLCQ, and
 * adding them would suggest a single total that no measurement supports.
 */
function ModelBar({ block }: { block: ModelBlock }) {
  if (!block.available) {
    return (
      <p className="note model-note">
        Modeli nuk u pyet dot: {block.reason}
      </p>
    );
  }

  const skipped = block.smells.reduce((total, report) => total + report.incomplete, 0);

  return (
    <div className="summary model">
      {/* The row says whose numbers these are. Without it the second row reads
          as more of the first, and the two approaches are not additive. */}
      <div className="figure name">
        <b>Qasja B</b>
        <span>modeli i trajnuar</span>
      </div>
      {block.smells.map((report) => (
        <div className="figure" key={report.smell}>
          <b>{report.flagged}</b>
          <span>{SMELL_SQ[report.smell] ?? report.smell}</span>
        </div>
      ))}
      {skipped > 0 && (
        <p className="caption">
          {skipped} entitete nuk u gjykuan: u mungonte një matje, dhe modeli nuk pyetet mbi një
          zero të shpikur.
        </p>
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
  order,
  query,
  agreed,
  hasModel,
  onSeverity,
  onKind,
  onOrder,
  onQuery,
  onAgreed,
}: {
  analysis: Analysis;
  severity: Severity | "all";
  kind: string;
  order: Order;
  query: string;
  agreed: boolean;
  hasModel: boolean;
  onSeverity: (value: Severity | "all") => void;
  onKind: (value: string) => void;
  onOrder: (value: Order) => void;
  onQuery: (value: string) => void;
  onAgreed: (value: boolean) => void;
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
      <label>
        Radhitur sipas
        <select value={order} onChange={(e) => onOrder(e.target.value as Order)}>
          {(Object.keys(ORDER_LABELS) as Order[]).map((name) => (
            <option key={name} value={name}>
              {ORDER_LABELS[name]}
            </option>
          ))}
        </select>
      </label>
      <label className="grow">
        Kërko
        <input
          type="search"
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder="klasë, metodë ose skedar"
        />
      </label>
      {hasModel && (
        <label className="only-agreed" title="Prerja e dy qasjeve — sinjali më i fortë i matur">
          <input
            type="checkbox"
            checked={agreed}
            aria-label="Vetëm ku pajtohen të dyja qasjet"
            onChange={(e) => onAgreed(e.target.checked)}
          />
          Vetëm ku pajtohen
        </label>
      )}
    </div>
  );
}
