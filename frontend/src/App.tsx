import { useMemo, useState } from "react";
import { analyse, preview } from "./api";
import { Diff } from "./Diff";
import type { Analysis, Preview, Severity, Smell } from "./types";

const SEVERITY_ORDER: Record<Severity, number> = { critical: 0, major: 1, minor: 2 };

type Screen =
  | { state: "idle" }
  | { state: "loading" }
  | { state: "error"; message: string }
  | { state: "ready"; analysis: Analysis };

export function App() {
  const [path, setPath] = useState("");
  const [screen, setScreen] = useState<Screen>({ state: "idle" });
  const [severity, setSeverity] = useState<Severity | "all">("all");
  const [kind, setKind] = useState<string>("all");
  const [selected, setSelected] = useState<Smell | null>(null);

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

  return (
    <div className="page">
      <header>
        <h1>JavaSmell</h1>
        <p className="tagline">Detektim i code smells dhe rekomandime refaktorimi</p>
      </header>

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
              <section className="list">
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
                        className={selected === smell ? "row selected" : "row"}
                        onClick={() => setSelected(smell)}
                      >
                        <span className={`pill ${smell.severity}`}>{smell.severity}</span>
                        <span className="kind">{smell.smell_type}</span>
                        <span className="where">
                          {smell.class_name}
                          {smell.method ? `.${smell.method.replace(/\(.*$/, "")}` : ""}
                        </span>
                        <span className="file">
                          {smell.file_path}:{smell.start_line}
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
      <h2>
        <span className={`pill ${smell.severity}`}>{smell.severity}</span> {smell.smell_type}
      </h2>
      <p className="where">
        {smell.package ? `${smell.package}.` : ""}
        {smell.class_name}
        {smell.method ? `.${smell.method}` : ""}
      </p>
      <p className="file">
        {smell.file_path}:{smell.start_line}–{smell.end_line}
      </p>

      <h3>Pse u shënua</h3>
      <p className="rationale">{smell.rationale}</p>

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
