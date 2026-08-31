import { Fragment, useState } from "react";
import {
  AGGREGATION_SQ,
  AGGREGATIONS,
  MODEL_SQ,
  REFUSAL_SQ,
  SMELLS,
  SMELL_SQ,
  VERDICT_SQ,
  dataset,
  ml,
  refactoring,
  ruleScore,
  rules,
  sweep,
  variantScore,
} from "./evaluation";
import type { Aggregation } from "./evaluation";

// Agregimi parësor i punimit. Modelet janë trajnuar kundrejt kësaj etikete, ndaj
// krahasimi A↔B mbahet gjithmonë këtu: një tabelë ku njëra anë ndryshon etiketë
// dhe tjetra jo nuk krahason dy qasje, krahason dy pyetje.
const PRIMARY: Aggregation = "mean";

export function Results() {
  const [smell, setSmell] = useState<string>(SMELLS[0]);
  const [aggregation, setAggregation] = useState<Aggregation>(PRIMARY);

  const coverage = (dataset.rows / dataset.samples_considered) * 100;

  return (
    <div className="results">
      <p className="lede">
        Numrat e mëposhtëm janë rezultatet e vlerësimit të sistemit mbi MLCQ-në, të lexuara nga
        skedarët e komituar në <code>data/results/</code>. Nuk maten këtu dhe nuk varen nga
        serveri: janë të njëjtët numra që raporton punimi.
      </p>

      <div className="summary">
        <Figure value={dataset.rows.toLocaleString("sq")} label="mostra të vlerësuara" accent />
        <Figure value={dataset.repositories} label="depo Java" />
        <Figure value={dataset.samples_considered.toLocaleString("sq")} label="mostra në MLCQ" />
        <Figure value={`${coverage.toFixed(1)}%`} label="e MLCQ-së e vlerësuar" />
        <Figure value={ml.folds} label="fold-e sipas depos" />
      </div>

      <Panel
        title="Qasja A kundrejt Qasjes B"
        note="MCC për çdo erë. Zero do të thotë 'sa hamendja'; një detektor që nuk ndez kurrë nuk
              merr dot pikë këtu, çka është arsyeja pse raportohet ky tregues e jo saktësia."
      >
        <table className="grid">
          <thead>
            <tr>
              <th>Erë</th>
              <th>Mostra</th>
              <th>A: rregullat</th>
              <th>B: modeli</th>
              <th>Modeli më i mirë</th>
            </tr>
          </thead>
          <tbody>
            {SMELLS.map((name) => {
              const a = ruleScore(name, PRIMARY);
              const model = ml.per_smell[name];
              const b = model.models[model.best_model];
              // Vetëm `blob` ka variant të dytë: strategjia e botuar plus një detektor
              // që mbështetet vetëm te madhësia. Dallimi mes dy rreshtave tregon sa nga
              // ajo që rishikuesit e quajnë blob shpjegohet me madhësi të thjeshtë.
              const variant = variantScore(name, PRIMARY);
              return (
                <Fragment key={name}>
                  <tr>
                    <th scope="row">{SMELL_SQ[name] ?? name}</th>
                    <td className="figures">{model.data.samples.toLocaleString("sq")}</td>
                    <td>
                      <Bar value={a.mcc} tone="rules" />
                    </td>
                    <td>
                      <Bar value={b.mcc} tone="model" />
                    </td>
                    <td className="quiet">{MODEL_SQ[model.best_model] ?? model.best_model}</td>
                  </tr>
                  {variant && (
                    <tr className="variant">
                      <th scope="row">↳ me madhësinë</th>
                      <td />
                      <td>
                        <Bar value={variant.mcc} tone="rules" />
                      </td>
                      <td />
                      <td className="quiet">varianti i ndjeshmërisë, jo strategji e botuar</td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </Panel>

      <div className="split">
        <Panel
          title="Ndjeshmëria ndaj mospajtimit"
          note="Rishikuesit e MLCQ-së nuk pajtohen për një të katërtën e mostrave. Kjo tabelë
                tregon sa varet rezultati i rregullave nga mënyra si zgjidhet ai mospajtim."
        >
          <div className="chips">
            {AGGREGATIONS.map((name) => (
              <button
                key={name}
                className={name === aggregation ? "chip on" : "chip"}
                onClick={() => setAggregation(name)}
                aria-pressed={name === aggregation}
              >
                {name}
              </button>
            ))}
          </div>
          <p className="quiet">{AGGREGATION_SQ[aggregation]}</p>
          <table className="grid">
            <thead>
              <tr>
                <th>Erë</th>
                <th>P</th>
                <th>R</th>
                <th>F1</th>
                <th>MCC</th>
                <th>Pozitivë</th>
              </tr>
            </thead>
            <tbody>
              {SMELLS.map((name) => {
                const score = ruleScore(name, aggregation);
                return (
                  <tr key={name}>
                    <th scope="row">{SMELL_SQ[name] ?? name}</th>
                    <Cell value={score.precision} />
                    <Cell value={score.recall} />
                    <Cell value={score.f1} />
                    <Cell value={score.mcc} strong />
                    <td className="figures">{score.support_positive}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {aggregation !== PRIMARY && (
            <p className="quiet">
              Krahasimi me Qasjen B mbetet te «{PRIMARY}», sepse modelet janë trajnuar kundrejt
              asaj etikete.
            </p>
          )}
        </Panel>

        <Panel
          title="Motori i refaktorimit"
          note="Një refuzim është rezultat i saktë dhe numërohet si i tillë: motori nuk e prek
                kodin kur parakushti nuk provohet nga pema e analizës."
        >
          <div className="summary tight">
            <Figure value={refactoring.detected.toLocaleString("sq")} label="vende të gjetura" />
            <Figure
              value={refactoring.applied.toLocaleString("sq")}
              label="të transformuara"
              accent
            />
            <Figure
              value={`${((refactoring.applied / refactoring.detected) * 100).toFixed(1)}%`}
              label="e vendeve"
            />
          </div>
          <h4>Pse u refuzuan</h4>
          <Distribution counts={refactoring.refused_by_reason} labels={REFUSAL_SQ} total={refactoring.detected} />
          <h4>Verifikimi i atyre që u aplikuan</h4>
          <Distribution counts={refactoring.verdicts} labels={VERDICT_SQ} total={refactoring.applied} />
        </Panel>
      </div>

      <Panel
        title={`Për erën: ${SMELL_SQ[smell] ?? smell}`}
        note="Zgjidh erën për ta parë të ndarë sipas ashpërsisë, pajtimin mes dy qasjeve, dhe sa
              lëviz rezultati kur zhvendoset një prag."
      >
        <div className="chips">
          {SMELLS.map((name) => (
            <button
              key={name}
              className={name === smell ? "chip on" : "chip"}
              onClick={() => setSmell(name)}
              aria-pressed={name === smell}
            >
              {SMELL_SQ[name] ?? name}
            </button>
          ))}
        </div>

        <div className="split">
          <div>
            <h4>Recall sipas ashpërsisë që caktuan rishikuesit</h4>
            <SeverityRecalls smell={smell} />
            <h4>Pajtimi mes dy qasjeve</h4>
            <AgreementBar smell={smell} />
            <h4>Veçoritë që zgjodhi modeli</h4>
            <p className="features">
              {ml.per_smell[smell].top_features.map((feature) => (
                <code key={feature}>{feature}</code>
              ))}
            </p>
          </div>
          <div>
            <h4>Sa lëviz MCC-ja kur zhvendoset një prag</h4>
            <ThresholdSweep smell={smell} />
          </div>
        </div>
      </Panel>

      <p className="quiet footnote">
        Prodhuar me commit-in <code>{rules.environment.commit.slice(0, 10)}</code>, Python{" "}
        {rules.environment.python}, {rules.environment.platform}. Ndarja mes trajnimit dhe
        testimit është e grupuar sipas depos, kurrë e rastësishme sipas rreshtave.
      </p>
    </div>
  );
}

function SeverityRecalls({ smell }: { smell: string }) {
  const variant = rules.per_smell[smell].strategy;
  const levels = ["critical", "major", "minor"].filter(
    (level) => variant.recall_by_severity[level],
  );
  return (
    <table className="grid">
      <tbody>
        {levels.map((level) => {
          const entry = variant.recall_by_severity[level];
          return (
            <tr key={level}>
              <th scope="row">{level}</th>
              <td>
                <Bar
                  value={entry.recall}
                  tone={level === "minor" ? "rules" : "severe"}
                  format="percent"
                />
              </td>
              <td className="figures quiet">
                {entry.caught}/{entry.support}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function AgreementBar({ smell }: { smell: string }) {
  const { both, only_rules, only_model, neither, kappa, n } = ml.per_smell[smell].vs_rules;
  const cells: Array<[string, number, string]> = [
    ["të dyja", both, "both"],
    ["vetëm A", only_rules, "rules"],
    ["vetëm B", only_model, "model"],
    ["asnjëra", neither, "neither"],
  ];
  return (
    <>
      <div className="stack" role="img" aria-label={`Pajtimi për ${smell}`}>
        {cells.map(([label, value, tone]) => (
          <span
            key={tone}
            className={`slice ${tone}`}
            style={{ flexGrow: value }}
            title={`${label}: ${value}`}
          />
        ))}
      </div>
      <ul className="legend">
        {cells.map(([label, value, tone]) => (
          <li key={tone}>
            <span className={`swatch ${tone}`} />
            {label}: <b>{value}</b>
          </li>
        ))}
      </ul>
      <p className="quiet">
        κ = {kappa.toFixed(3)} mbi {n.toLocaleString("sq")} mostra. Kappa e heq pajtimin që pritet
        nga rastësia, i cili mbi një bashkësi kaq të çekuilibruar është i madh.
      </p>
    </>
  );
}

function ThresholdSweep({ smell }: { smell: string }) {
  const swept = sweep.per_smell[smell];
  return (
    <table className="grid sweep">
      <thead>
        <tr>
          <th>Pragu</th>
          {sweep.factors.map((factor) => (
            <th key={factor} className={factor === 1 ? "published" : undefined}>
              ×{factor}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {Object.entries(swept).map(([name, points]) => (
          <tr key={name}>
            <th scope="row">
              <code>{name}</code>
            </th>
            {points.map((point) => (
              <td
                key={point.factor}
                className={point.factor === 1 ? "published figures" : "figures"}
                title={`vlera ${point.value}, MCC ${point.mcc?.toFixed(3) ?? "—"}`}
              >
                {point.mcc === null ? "—" : point.mcc.toFixed(3)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Distribution({
  counts,
  labels,
  total,
}: {
  counts: Record<string, number>;
  labels: Record<string, string>;
  total: number;
}) {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  return (
    <table className="grid">
      <tbody>
        {entries.map(([key, value]) => (
          <tr key={key}>
            <th scope="row">{labels[key] ?? key}</th>
            <td>
              <Bar value={value / total} tone="rules" format="percent" />
            </td>
            <td className="figures quiet">{value.toLocaleString("sq")}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Bar({
  value,
  tone,
  format = "score",
}: {
  value: number | null;
  tone: string;
  // MCC-ja lexohet si koeficient dhe shkruhet me tri shifra; një pjesë e së tërës
  // lexohet si përqindje. I shkruar njësoj, njëri nga të dy do të dilte i çuditshëm.
  format?: "score" | "percent";
}) {
  if (value === null) return <span className="quiet">i papërcaktuar</span>;
  // MCC-ja shkon nga -1 në 1, por çdo vlerë e matur këtu është jo-negative; një
  // shirit i gjatësisë negative do të ishte i pakuptimtë, ndaj pritet te zeroja.
  const width = Math.max(0, Math.min(1, value)) * 100;
  const text = format === "percent" ? `${(value * 100).toFixed(1)}%` : value.toFixed(3);
  return (
    <span className="bar" title={text}>
      <span className={`fill ${tone}`} style={{ width: `${width}%` }} />
      <b>{text}</b>
    </span>
  );
}

function Cell({ value, strong }: { value: number | null; strong?: boolean }) {
  return (
    <td className={strong ? "figures strong" : "figures"}>
      {value === null ? "—" : value.toFixed(3)}
    </td>
  );
}

function Figure({
  value,
  label,
  accent,
}: {
  value: string | number;
  label: string;
  accent?: boolean;
}) {
  return (
    <div className={accent ? "figure accent" : "figure"}>
      <b>{value}</b>
      <span>{label}</span>
    </div>
  );
}

function Panel({
  title,
  note,
  children,
}: {
  title: string;
  note?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="panel">
      <h3>{title}</h3>
      {note && <p className="quiet">{note}</p>}
      {children}
    </section>
  );
}