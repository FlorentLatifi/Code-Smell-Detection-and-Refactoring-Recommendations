import { useMemo, useRef, useState } from "react";
import { analyse } from "./api";
import { Detail } from "./Detail";
import { SMELL_SQ } from "./evaluation";
import { agreementOn, indexModel } from "./model";
import { Patch } from "./Patch";
import { Results } from "./Results";
import { byFile, byScore, bySeverity, countByWorst, groupBySite } from "./sites";
import type { Site } from "./sites";
import type { Analysis, ModelBlock, Severity, Smell } from "./types";


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
  const [selected, setSelected] = useState<Site | null>(null);
  // Cila erë e vendit të zgjedhur shfaqet djathtas. Rivendoset te më e rënda
  // sa herë zgjidhet një vend tjetër, sepse ajo është ajo që lexuesi kërkoi.
  const [shownSmell, setShownSmell] = useState<Smell | null>(null);
  const listRef = useRef<HTMLElement>(null);

  async function run(event: React.FormEvent) {
    event.preventDefault();
    setScreen({ state: "loading" });
    setSelected(null);
    setShownSmell(null);
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
  /**
   * A e plotëson kjo erë çdo kusht të filtrave.
   *
   * Kushtet janë per-erë sepse ashtu i mat detektori: një metodë mund të jetë
   * `critical` për një strategji dhe `minor` për një tjetër.
   */
  const matches = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return (smell: Smell) =>
      (severity === "all" || smell.severity === severity) &&
      (kind === "all" || smell.smell_type === kind) &&
      // Inert without a model to agree with. The control is hidden in that
      // case, so a filter left checked from an earlier run would empty the
      // list with nothing on screen to switch it back off.
      (!agreed || model === null || agreementOn(model, smell) !== null) &&
      (needle === "" ||
        `${smell.class_name} ${smell.method ?? ""} ${smell.file_path} ${smell.smell_type}`
          .toLowerCase()
          .includes(needle));
  }, [severity, kind, query, agreed, model]);

  const filtering = severity !== "all" || kind !== "all" || query.trim() !== "" || agreed;

  /** Të gjitha vendet, pa filtër: emëruesi kundrejt të cilit lexohet lista. */
  const allSites = useMemo(() => groupBySite(smells), [smells]);

  /**
   * Filtri zgjedh **vende**, jo erëra, dhe vendi i zgjedhur shfaqet i tërë.
   *
   * Drafti i parë filtronte erërat dhe gruponte të mbijetuarat, çka e zbrazte
   * pikërisht atë që grupimi shtoi: duke kërkuar `LongMethod` humbisje faktin se
   * tri nga ato metoda janë edhe `BrainMethod` edhe `DeepNesting` — konteksti që
   * të thotë cilën ta hapësh të parën. Tani vendi mbahet i plotë dhe erërat që
   * përputhen shënohen, ndaj shihet edhe pse rreshti doli edhe çfarë tjetër mban.
   */
  const shown = useMemo(() => {
    const sites = allSites.filter((site) => site.smells.some(matches));
    if (order === "file") return byFile(sites);
    if (order === "score") return byScore(sites);
    return bySeverity(sites);
  }, [allSites, matches, order]);

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
    choose(shown[next]);
    listRef.current?.querySelectorAll<HTMLButtonElement>("button.row")[next]?.focus();
  }

  /** Zgjedh një vend, dhe me të erën e tij më të rëndë. */
  function choose(site: Site): void {
    setSelected(site);
    setShownSmell(site.smells[0]);
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
          <SummaryBar analysis={screen.analysis} sites={allSites} />
          {screen.analysis.model && <ModelBar block={screen.analysis.model} />}

          {screen.analysis.smells.length === 0 ? (
            <p className="empty">Asnjë erë e detektuar. Kodi kaloi çdo strategji.</p>
          ) : (
            <>
            <Patch path={path} />
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
                  {shown.length} nga {allSites.length} {allSites.length === 1 ? "vend" : "vende"}
                  {", "}
                  {countSmells(shown)} erëra
                </p>
                <ul>
                  {shown.map((site) => (
                    <li key={site.key}>
                      <button
                        className={`row ${site.worst}${selected?.key === site.key ? " selected" : ""}`}
                        onClick={() => choose(site)}
                        aria-current={selected?.key === site.key}
                      >
                        <span className="mark" aria-hidden="true" />
                        <span>
                          <span className="headline">
                            <span className="where">
                              {site.class_name}
                              {site.method ? `.${site.method.replace(/\(.*$/, "")}` : ""}
                            </span>
                            <span className="grade">
                              {site.smells.some((s) => agreementOn(model, s)) && (
                                <abbr className="both" title="Modeli e shënoi po ashtu">
                                  A∩B
                                </abbr>
                              )}
                              {site.automated && (
                                <abbr className="auto" title="Motori e rishkruan vetë">
                                  ✎
                                </abbr>
                              )}
                              {site.worst}
                            </span>
                          </span>
                          <span className="kinds">
                            {site.smells.length > 1 && (
                              <span className="tally">{site.smells.length} erëra</span>
                            )}
                            {site.smells.map((s) => (
                              <span
                                key={s.smell_type}
                                className={filtering && matches(s) ? "kind hit" : "kind"}
                              >
                                {s.smell_type}
                              </span>
                            ))}
                          </span>
                          <span className="file">
                            {site.file_path}:{site.start_line}
                          </span>
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </section>

              <section className="detail">
                {selected && shownSmell ? (
                  <>
                    {selected.smells.length > 1 && (
                      <nav className="which" aria-label="Erërat e këtij vendi">
                        {selected.smells.map((s) => (
                          <button
                            key={s.smell_type}
                            className={s.smell_type === shownSmell.smell_type ? "pick on" : "pick"}
                            onClick={() => setShownSmell(s)}
                            aria-pressed={s.smell_type === shownSmell.smell_type}
                          >
                            {s.smell_type}
                          </button>
                        ))}
                      </nav>
                    )}
                    <Detail
                      smell={shownSmell}
                      path={path}
                      prediction={agreementOn(model, shownSmell)}
                      asked={model !== null}
                    />
                  </>
                ) : (
                  <p className="empty">Zgjidh një vend nga lista për ta parë arsyen.</p>
                )}
              </section>
            </div>
            </>
          )}
        </>
      )}
      </>
      )}
    </div>
  );
}

/** Sa erëra mbajnë këto vende bashkë. */
function countSmells(sites: Site[]): number {
  return sites.reduce((total, site) => total + site.smells.length, 0);
}

/**
 * Sa u mat, në të njëjtat njësi që përdor lista poshtë.
 *
 * Erërat dhe vendet janë të dyja aty me qëllim: numri i erërave është ai që
 * raporton motori, numri i vendeve është ai që lexuesi do të hapë. Pa të dytin,
 * shiriti thoshte 106 dhe lista thoshte 74 pa asgjë që ta shpjegonte dallimin.
 *
 * Ashpërsia numërohet **sipas vendit**, me të njëjtin rregull që përdor
 * distinktivi i çdo rreshti: më e rënda që mban vendi. Kështu shuma e tri
 * shifrave barazon numrin e vendeve, dhe klikimi nga shiriti te lista nuk
 * ndryshon njësi në rrugë.
 */
function SummaryBar({ analysis, sites }: { analysis: Analysis; sites: Site[] }) {
  const { summary } = analysis;
  const byWorst = countByWorst(sites);
  return (
    <div className="summary">
      <Figure value={summary.files} label="skedarë" />
      <Figure value={summary.classes} label="klasa" />
      <Figure value={summary.methods} label="metoda" />
      <Figure value={summary.smells} label="erëra" />
      <Figure value={sites.length} label={sites.length === 1 ? "vend" : "vende"} accent />
      {(["critical", "major", "minor"] as const).map((level) =>
        byWorst[level] ? (
          <Figure key={level} value={byWorst[level]} label={`${level} (vende)`} tone={level} />
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
