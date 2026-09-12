import { useEffect, useMemo, useRef, useState } from "react";
import { allowedRoot, analyse, Cancelled, treeState } from "./api";
import { Detail } from "./Detail";
import { Filters } from "./Filters";
import type { Order } from "./Filters";
import { Hotspots } from "./Hotspots";
import { agreementOn, indexModel, modelOnly } from "./model";
import { ModelOnly } from "./ModelOnly";
import { Landing } from "./Landing";
import { Context } from "./Context";
import { PatchOutput, usePatch } from "./Patch";
import { Dashboard } from "./Dashboard";
import { Tools } from "./Tools";
import { Results } from "./Results";
import { ModelBar, Unparsed } from "./Summary";
import { automatable, byFile, byScore, bySeverity, groupBySite } from "./sites";
import type { Site } from "./sites";
import type { Analysis, Severity, Smell, TreeState } from "./types";


const REMEMBERED_PATH = "javasmell.path";

/**
 * Sa rreshta hyjnë te DOM-i njëherësh.
 *
 * Lista i jepte të gjithë. Mbi `apache/ambari` kjo do të thoshte 4 249 rreshta dhe
 * 53 821 nyje, dhe **146 ms bllokim për çdo shkronjë** të shkruar te kërkimi —
 * mjaftueshëm sa shkrimi të ndihet i ngecur. Numri nuk është zgjedhur si kompromis
 * teknik: lista renditet me të rëndën e para, ndaj dyqind rreshta janë shumë më
 * tepër se sa lexon dikush para se të ngushtojë kërkimin.
 *
 * Pa virtualizim dhe pa bibliotekë. Një dritare rrëshqitëse do të ishte kod dhe
 * varësi për një problem që një kufi me «shfaq më shumë» e zgjidh plotësisht, dhe
 * §7 i `ENGINEERING.md` e kërkon zgjidhjen më të thjeshtë që është e saktë.
 */
const PAGE = 200;

/**
 * Gjendja që i përket adresës, e jo vetëm kujtesës së komponentit.
 *
 * Pa këtë, rifreskimi e zbrazte gjithçka, butoni «prapa» e mbyllte faqen në vend
 * që të kthehej te lista, dhe asnjë pamje nuk ndahej dot me dikë tjetër. Nuk u
 * shtua bibliotekë rrugëzimi: vendimi te `View` qëndron, dhe katër parametra
 * kërkimi e bëjnë tërë punën.
 *
 * Shkruhet me `replaceState` e jo me `pushState`, sepse ndryshimi i një filtri
 * nuk është vend ku dikush do të kthehej — një histori me njëzet hapa filtrash
 * do ta bënte butonin «prapa» të padobishëm.
 */
function readAddress(): { view: View; path: string; query: string; kind: string } {
  const params = new URLSearchParams(window.location.search);
  const view = params.get("view");
  return {
    view: view === "results" ? "results" : "analysis",
    path: params.get("path") ?? "",
    query: params.get("q") ?? "",
    kind: params.get("kind") ?? "all",
  };
}

function writeAddress(view: View, path: string, query: string, kind: string): void {
  const params = new URLSearchParams();
  if (view === "results") params.set("view", view);
  if (path.trim()) params.set("path", path.trim());
  if (query.trim()) params.set("q", query.trim());
  if (kind !== "all") params.set("kind", kind);

  const search = params.toString();
  const next = search ? `${window.location.pathname}?${search}` : window.location.pathname;
  if (next !== window.location.pathname + window.location.search) {
    window.history.replaceState(null, "", next);
  }
}

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

/**
 * `path` udhëton bashkë me analizën, e nuk lexohet nga kutia.
 *
 * Kutia mban atë që po shkruan përdoruesi tani; analiza i përket shtegut që u
 * dërgua vërtet. Kur të dyja ishin e njëjta ndryshore, redaktimi i kutisë pa
 * ri-ekzekutuar e prishte panelin e detajit: gjetjet në ekran i përkisnin
 * analizës së vjetër, ndërsa `/source` dhe `/refactor/preview` thirreshin me
 * shtegun e ri dhe ktheheshin me gabim pa asnjë shpjegim.
 */
type Screen =
  | { state: "idle" }
  | { state: "loading" }
  | { state: "error"; message: string }
  | {
      state: "ready";
      analysis: Analysis;
      path: string;
      /** Sa zgjati kërkesa, matur te klienti: vetëm ai e di kur e nisi. */
      seconds: number;
      /** A u pyet modeli për *këtë* analizë, e jo çfarë thotë kutiza tani. */
      askedModel: boolean;
    };

// Dy pamje, pa router: një bibliotekë rrugëzimi për dy gjendje do të ishte më
// shumë kod se vetë kalimi mes tyre.
type View = "analysis" | "results";

export function App() {
  // Adresa lexohet një herë, në ngarkim. Pas saj burimi i vërtetë është gjendja;
  // adresa e ndjek atë e nuk e drejton.
  const address = useRef(readAddress()).current;
  const [view, setView] = useState<View>(address.view);
  // Shtegu te adresa fiton mbi atë të kujtuar: një link i ndarë duhet të hapë atë
  // që premton, e jo atë që ky shfletues pa herën e fundit.
  const [path, setPath] = useState(() => address.path || remembered(REMEMBERED_PATH));
  const [screen, setScreen] = useState<Screen>({ state: "idle" });
  // Emri i dosjes së lejuar, që ftesa ta thotë para se dikush të gabojë (VD-95).
  const [root, setRoot] = useState<string | null>(null);
  const [severity, setSeverity] = useState<Severity | "all">("all");
  const [kind, setKind] = useState<string>(address.kind);
  const [query, setQuery] = useState(address.query);
  const [order, setOrder] = useState<Order>("severity");
  // Whether the model was asked, kept apart from whether it answered: an
  // untrained checkout has no models, and the difference has to stay visible.
  const [askModel, setAskModel] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [selected, setSelected] = useState<Site | null>(null);
  const [limit, setLimit] = useState(PAGE);
  // Cila erë e vendit të zgjedhur shfaqet djathtas. Rivendoset te më e rënda
  // sa herë zgjidhet një vend tjetër, sepse ajo është ajo që lexuesi kërkoi.
  const [shownSmell, setShownSmell] = useState<Smell | null>(null);
  const listRef = useRef<HTMLElement>(null);
  // Mbahet te një ref e jo te gjendja: e ndryshon vetëm trajtuesi, dhe asgjë në
  // ekran nuk varet prej saj përveç butonit që e përdor.
  const running = useRef<AbortController | null>(null);
  // Shtegu i analizuar, e jo ai te kutia: patch-i dhe shkrimi i përkasin asaj
  // që u matur vërtet.
  const analysed = screen.state === "ready" ? screen.path : "";
  const patchSession = usePatch(analysed);
  const [tree, setTree] = useState<TreeState | null>(null);

  async function run(event: React.FormEvent) {
    event.preventDefault();
    setScreen({ state: "loading" });
    setSelected(null);
    setShownSmell(null);
    const asked = path;
    const controller = new AbortController();
    running.current = controller;
    const started = performance.now();
    try {
      const analysis = await analyse(asked, askModel, controller.signal);
      setScreen({
        state: "ready",
        analysis,
        path: asked,
        seconds: (performance.now() - started) / 1000,
        askedModel: askModel,
      });
      remember(REMEMBERED_PATH, asked);
    } catch (failure) {
      // Ndalimi nga vetë përdoruesi nuk është gabim: ekrani kthehet aty ku ishte,
      // pa një banderolë të kuqe që i thotë se diçka shkoi keq.
      setScreen(
        failure instanceof Cancelled
          ? { state: "idle" }
          : { state: "error", message: (failure as Error).message },
      );
    } finally {
      running.current = null;
    }
  }

  function stop(): void {
    running.current?.abort();
  }

  /** I njëjti ekzekutim si forma, i thirrur nga një buton pa ngjarje. */
  async function rerun(): Promise<void> {
    await run({ preventDefault() {} } as React.FormEvent);
  }

  // Adresa përditësohet pas çdo renderimi që e ndryshon atë që ajo mban.
  useEffect(() => {
    let live = true;
    void allowedRoot().then((name) => {
      if (live) setRoot(name);
    });
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => writeAddress(view, path, query, kind), [view, path, query, kind]);

  // Gjendja e pemës pyetet një herë për çdo shteg të analizuar, që kolona e
  // veglave ta thotë para se dikush ta provojë shkrimin (VD-100).
  useEffect(() => {
    if (!analysed) {
      setTree(null);
      return;
    }
    let live = true;
    void treeState(analysed)
      .then((state) => live && setTree(state))
      .catch(() => live && setTree(null));
    return () => {
      live = false;
    };
  }, [analysed]);

  // Një filtër i ri e kthen dritaren te fillimi: rreshtat e zgjeruar i përkisnin
  // listës së mëparshme, dhe mbajtja e tyre do të hapte një dritare arbitrare mbi
  // një listë tjetër.
  useEffect(() => setLimit(PAGE), [severity, kind, query, agreed, order, screen]);

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
   * Vetëm kreu i listës hyn te DOM-i; pjesa tjetër vjen me kërkesë.
   *
   * `shown` mbetet emëruesi i plotë — numërimi, filtrat dhe hotspot-et lexohen
   * prej tij — ndaj kufiri prek vetëm sa nyje ndërton shfletuesi.
   */
  const visible = useMemo(() => shown.slice(0, limit), [shown, limit]);

  /**
   * Up and down move through the findings.
   *
   * The list is the part a reader walks: a hundred rows read one after another
   * while the detail beside them changes. Reaching for the mouse for each one
   * makes that a chore, and the rows are already buttons, so the only thing
   * missing is moving the focus with the selection.
   */
  function navigate(event: React.KeyboardEvent) {
    // Filtrat rrinë brenda të njëjtës seksion, ndaj ngjarja e tyre fluturon lart
    // deri këtu. Pa këtë kontroll, shigjetat mbi një `select` ose brenda kutisë
    // së kërkimit anuloheshin dhe fokusi ikte te lista: filtri nuk ndryshohej dot
    // fare me tastierë. Shigjetat u përkasin rreshtave vetëm kur fokusi është mbi
    // një rresht.
    if (!(event.target as HTMLElement).closest("button.row")) return;
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    if (visible.length === 0) return;
    event.preventDefault();

    const current = selected ? visible.indexOf(selected) : -1;
    const step = event.key === "ArrowDown" ? 1 : -1;
    const next = Math.min(Math.max(current + step, 0), visible.length - 1);
    choose(visible[next]);
    listRef.current?.querySelectorAll<HTMLButtonElement>("button.row")[next]?.focus();
  }

  /** Zgjedh një vend, dhe me të erën e tij më të rëndë. */
  function choose(site: Site, smell?: Smell): void {
    setSelected(site);
    // Parazgjedhja është më e rënda e vendit, sepse ajo është ajo që lexuesi
    // pa te rreshti. Një rekomandim e emërton erën që ka rishkrim, e cila nuk
    // është gjithnjë e njëjta.
    setShownSmell(smell ?? site.smells[0]);
  }

  /**
   * Ndërro pamjen dhe çoje fokusin te përmbajtja e re.
   *
   * Pa këtë, një përdorues me tastierë shtyp skedën dhe fokusi mbetet mbi butonin:
   * ekrani ndryshon tërësisht poshtë tij dhe asgjë nuk e thotë. Tabulimi i radhës
   * nis nga koka, jo nga ajo që sapo u hap.
   */
  /** Kthen listën te gjendja e saj e plotë, pa e prekur analizën. */
  function clearFilters(): void {
    setSeverity("all");
    setKind("all");
    setQuery("");
    setAgreed(false);
  }

  /**
   * Majtas dhe djathtas lëvizin mes skedave.
   *
   * Kjo është ajo që pret dikush që njeh modelin `tablist`: tabulimi hyn te grupi
   * një herë, dhe shigjetat zgjedhin brenda tij. Pa të, `tabIndex={-1}` mbi skedën
   * e pazgjedhur do ta bënte atë të paarritshme fare.
   */
  function moveTab(event: React.KeyboardEvent): void {
    // Lart e poshtë sepse rreshti është vertikal; majtas e djathtas mbahen
    // gjithashtu, sepse dikush që e mësoi ndërfaqen e vjetër horizontale nuk
    // duhet ta gjejë tastierën të pafunksionale.
    const moves = ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"];
    if (!moves.includes(event.key)) return;
    event.preventDefault();
    const next = view === "analysis" ? "results" : "analysis";
    show(next);
    requestAnimationFrame(() => document.getElementById(`tab-${next}`)?.focus());
  }

  function show(next: View): void {
    setView(next);
    // Pas renderimit, ndryshe fokusi shkon te përmbajtja e vjetër.
    requestAnimationFrame(() => document.getElementById("content")?.focus());
  }

  return (
    <div className="page">
      <a className="skip" href="#content">
        Kalo te përmbajtja
      </a>
      <header>
        <h1>JavaSmell</h1>
        <p className="tagline">Detektim i code smells dhe rekomandime refaktorimi</p>
      </header>

      {/* Rreshti anësor. `aria-pressed` i thoshte lexuesit se butoni është i
          shtypur, jo se është skedë mes skedash; `tablist` e thotë sa janë, cila
          është e zgjedhura, dhe se ato drejtojnë një panel — çka është e vërteta
          e kësaj ndërfaqeje. Orientimi deklarohet, ose lexuesi i ekranit do t'i
          premtonte përdoruesit shigjetat e gabuara. */}
      <nav className="rail" role="tablist" aria-orientation="vertical" aria-label="Pamjet">
          <button
            role="tab"
            id="tab-analysis"
            aria-selected={view === "analysis"}
            aria-controls="panel"
            tabIndex={view === "analysis" ? 0 : -1}
            className={view === "analysis" ? "tab on" : "tab"}
            title="Analizo një projekt"
            onClick={() => show("analysis")}
            onKeyDown={moveTab}
          >
            <span className="glyph" aria-hidden="true">
              ⌕
            </span>
            <span className="label">Analizo një projekt</span>
          </button>
          <button
            role="tab"
            id="tab-results"
            aria-selected={view === "results"}
            aria-controls="panel"
            tabIndex={view === "results" ? 0 : -1}
            className={view === "results" ? "tab on" : "tab"}
            title="Rezultatet e vlerësimit"
            onClick={() => show("results")}
            onKeyDown={moveTab}
          >
            <span className="glyph" aria-hidden="true">
              ▤
            </span>
            <span className="label">Rezultatet e vlerësimit</span>
          </button>
      </nav>

      {/* `role="tabpanel"` mbi vetë `<main>` e mbivendos rolin e tij të nënkuptuar,
          dhe faqja mbetet pa landmark kryesor. Të dy rolet i duhen: njëri i thotë
          lexuesit ku nis përmbajtja, tjetri se cila skedë e drejton. */}
      <main id="content" tabIndex={-1}>
      <div
        id="panel"
        role="tabpanel"
        aria-labelledby={view === "results" ? "tab-results" : "tab-analysis"}
      >
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
        {screen.state === "loading" && (
          <button type="button" className="stop" onClick={stop}>
            Ndalo
          </button>
        )}
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

      {screen.state === "idle" && <Landing root={root} />}

      {screen.state === "loading" && (
        <p className="empty" role="status">
          Duke matur skedarët…
        </p>
      )}

      {screen.state === "error" && (
        <p className="failure" role="alert">
          {screen.message}
        </p>
      )}

      {screen.state === "ready" && (
        <>
          {/* Konteksti para totaleve: çfarë u lexua, pastaj çfarë u gjet aty.
              E kundërta i jep lexuesit një numër para se t'i japë emëruesin. */}
          <Context
            path={screen.path}
            analysis={screen.analysis}
            seconds={screen.seconds}
            askedModel={screen.askedModel}
          />
          <Unparsed summary={screen.analysis.summary} />
          {screen.analysis.smells.length === 0 ? (
            <p className="empty">Asnjë erë e detektuar. Kodi kaloi çdo strategji.</p>
          ) : (
            <>
            <Dashboard
              analysis={screen.analysis}
              sites={allSites}
              onPick={setQuery}
              onChoose={choose}
              tools={
                <Tools
                  session={patchSession}
                  path={screen.path}
                  ready={automatable(allSites)}
                  total={allSites.length}
                  tree={tree}
                  askedModel={screen.askedModel}
                  onReanalyse={() => void rerun()}
                  onEvaluation={() => show("results")}
                />
              }
            />
            {screen.analysis.model && <ModelBar block={screen.analysis.model} />}
            <ModelOnly predictions={modelOnly(model, screen.analysis.smells)} />
            <PatchOutput session={patchSession} path={screen.path} />
            <div className="layout">
              <section
                className="list"
                aria-label="Vendet e gjetura"
                ref={listRef}
                onKeyDown={navigate}
              >
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
                {/* Ndryshon me çdo filtër dhe me çdo analizë, ndaj është vendi i
                    natyrshëm ku një lexues ekrani duhet ta marrë vesh se sa mbetën. */}
                <p className="count" aria-live="polite">
                  {shown.length} nga {allSites.length} {allSites.length === 1 ? "vend" : "vende"}
                  {", "}
                  {shown.reduce((total, site) => total + site.smells.length, 0)} erëra
                </p>
                {shown.length === 0 && (
                  <p className="empty">
                    Asnjë vend nuk i plotëson filtrat.{" "}
                    <button className="link" onClick={clearFilters}>
                      Pastro filtrat
                    </button>
                  </p>
                )}
                <ul>
                  {visible.map((site) => (
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
                                <span className="both">
                                  <span aria-hidden="true">A∩B</span>
                                  <span className="sr-only">Modeli e shënoi po ashtu.</span>
                                </span>
                              )}
                              {site.automated && (
                                <span className="auto">
                                  <span aria-hidden="true">✎</span>
                                  <span className="sr-only">Motori e rishkruan vetë.</span>
                                </span>
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
                {shown.length > visible.length && (
                  <p className="more">
                    <button className="link" onClick={() => setLimit((n) => n + PAGE)}>
                      Shfaq {Math.min(PAGE, shown.length - visible.length)} të tjera
                    </button>{" "}
                    <span className="quiet">
                      nga {shown.length - visible.length} që mbeten, të renditura më poshtë
                    </span>
                  </p>
                )}
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
                      path={screen.path}
                      prediction={agreementOn(model, shownSmell)}
                      asked={model !== null}
                    />
                  </>
                ) : (
                  <Hotspots sites={allSites} onPick={setQuery} />
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
      </main>
    </div>
  );
}
