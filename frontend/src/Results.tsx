import { Fragment, useState } from "react";
import { Bar, Cell, Distribution, Figure, Missing, Panel } from "./Panels";
import {
  COMMITS,
  AGGREGATION_SQ,
  AGGREGATIONS,
  MODEL_SQ,
  REFUSAL_SQ,
  SMELLS,
  SMELL_SQ,
  VERDICT_SQ,
  corpusRepositories,
  dataset,
  ml,
  refactoring,
  ruleScore,
  rules,
  sweep,
  variantScore,
  blockingFor,
  pmd,
  PMD_ROW_SQ,
} from "./evaluation";
import type { Aggregation } from "./evaluation";
import { useSimple } from "./mode";
import { metricName, severityName, smellName, term, thresholdName } from "./plain";

// Agregimi parësor i punimit. Modelet janë trajnuar kundrejt kësaj etikete, ndaj
// krahasimi A↔B mbahet gjithmonë këtu: një tabelë ku njëra anë ndryshon etiketë
// dhe tjetra jo nuk krahason dy qasje, krahason dy pyetje.
const PRIMARY: Aggregation = "mean";

/**
 * Sa nga llojet e erërave i gjen modeli më saktë se rregullat, nga të dhënat.
 *
 * Fjalia e udhëzuesit të thjeshtë llogaritet këtu e nuk shkruhet me dorë: po të
 * ndryshonte një rezultat, një fjali e shtypur do të vazhdonte të pohonte të vjetrën.
 */
export function modelWins(): { better: number; total: number } {
  let better = 0;
  for (const name of SMELLS) {
    const a = ruleScore(name, PRIMARY).mcc;
    const per = ml.per_smell[name];
    const b = per.models[per.best_model]?.mcc ?? null;
    if (a !== null && b !== null && b > a) better += 1;
  }
  return { better, total: SMELLS.length };
}

/** Udhëzuesi i leximit: çfarë mat secila shifër, para tabelave (VD-144). */
function ReadingGuide() {
  const { better, total } = modelWins();
  const keys = ["sample", "mcc", "precision", "recall", "f1", "kappa"];
  return (
    <section className="panel guide" aria-labelledby="reading-guide">
      <h2 id="reading-guide">Si t'i lexosh këto shifra</h2>
      <p>
        Mjeti u krahasua me gjykimin e zhvilluesve profesionistë mbi{" "}
        {dataset.rows.toLocaleString("sq")} pjesë kodi nga {corpusRepositories.toLocaleString("sq")}{" "}
        projekte reale. Shkurt: te {better} nga {total} llojet e problemeve, modeli i gjen më saktë
        se rregullat.
      </p>
      <dl>
        {keys.map((key) => (
          <div key={key}>
            <dt>{term(key).name}</dt>
            <dd>{term(key).what}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export function Results() {
  const [smell, setSmell] = useState<string>(SMELLS[0]);
  const commits = COMMITS;
  const [aggregation, setAggregation] = useState<Aggregation>(PRIMARY);
  const simple = useSimple();
  /** Emri i erës: i thjeshtë, ose ai që përdor punimi. */
  const named = (name: string) => (simple ? smellName(name) : (SMELL_SQ[name] ?? name));

  const coverage = (dataset.rows / dataset.samples_considered) * 100;

  return (
    <div className="results">
      {simple ? (
        <ReadingGuide />
      ) : (
        <p className="lede">
          Numrat e mëposhtëm janë rezultatet e vlerësimit të sistemit mbi MLCQ-në, të lexuara nga
          skedarët e komituar në <code>data/results/</code>. Nuk maten këtu dhe nuk varen nga
          serveri: janë të njëjtët numra që raporton punimi.
        </p>
      )}

      <div className="summary">
        <Figure
          value={dataset.rows.toLocaleString("sq")}
          label={simple ? "pjesë kodi të provuara" : "mostra të vlerësuara"}
          accent
        />
        <Figure value={corpusRepositories} label={simple ? "projekte Java" : "depo Java"} />
        <Figure
          value={dataset.samples_considered.toLocaleString("sq")}
          label={simple ? "pjesë kodi të gjykuara nga zhvilluesit" : "mostra në MLCQ"}
        />
        <Figure
          value={`${coverage.toFixed(1)}%`}
          label={simple ? "prej tyre u provuan" : "e MLCQ-së e vlerësuar"}
        />
        <Figure value={ml.folds} label={simple ? "pjesë në të cilat u nda prova" : "fold-e sipas depos"} />
      </div>

      <Panel
        title={simple ? "Rregullat kundrejt modelit" : "Qasja A kundrejt Qasjes B"}
        note={
          simple
            ? "Nota e saktësisë (MCC) për çdo lloj problemi. Sa më e gjatë vija, aq më mirë."
            : "MCC për çdo erë. Zero do të thotë 'sa hamendja'; një detektor që nuk ndez kurrë nuk merr dot pikë këtu, çka është arsyeja pse raportohet ky tregues e jo saktësia."
        }
      >
        <table className="data-grid">
          <thead>
            <tr>
              <th>{simple ? "Problemi" : "Erë"}</th>
              <th>Mostra</th>
              <th>{simple ? "Rregullat" : "A: rregullat"}</th>
              <th>{simple ? "Modeli" : "B: modeli"}</th>
              <th>{simple ? "Lloji i modelit" : "Modeli më i mirë"}</th>
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
                    <th scope="row">{named(name)}</th>
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
                      <th scope="row">{simple ? "↳ edhe me madhësinë e klasës" : "↳ me madhësinë"}</th>
                      <td />
                      <td>
                        <Bar value={variant.mcc} tone="rules" />
                      </td>
                      <td />
                      <td className="quiet">
                        {simple
                          ? "provë shtesë, jo rregull i botuar"
                          : "varianti i ndjeshmërisë, jo strategji e botuar"}
                      </td>
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
          title={simple ? "Kur zhvilluesit nuk pajtohen mes tyre" : "Ndjeshmëria ndaj mospajtimit"}
          note={
            simple
              ? "Për një të katërtën e shembujve, zhvilluesit që i gjykuan nuk ishin të një mendjeje. Butonat më poshtë ndryshojnë si zgjidhet mospajtimi, dhe tabela tregon sa ndikon kjo te rezultati i rregullave."
              : "Rishikuesit e MLCQ-së nuk pajtohen për një të katërtën e mostrave. Kjo tabelë tregon sa varet rezultati i rregullave nga mënyra si zgjidhet ai mospajtim."
          }
        >
          <div className="chips">
            {AGGREGATIONS.map((name) => (
              <button
                key={name}
                className={name === aggregation ? "chip on" : "chip"}
                onClick={() => setAggregation(name)}
                aria-pressed={name === aggregation}
              >
                {simple ? AGGREGATION_SQ[name] : name}
              </button>
            ))}
          </div>
          {!simple && <p className="quiet">{AGGREGATION_SQ[aggregation]}</p>}
          <table className="data-grid">
            <thead>
              <tr>
                <th>{simple ? "Problemi" : "Erë"}</th>
                <th title={term("precision").what}>P</th>
                <th title={term("recall").what}>R</th>
                <th title={term("f1").what}>F1</th>
                <th title={term("mcc").what}>MCC</th>
                <th>{simple ? "Raste të vërteta" : "Pozitivë"}</th>
              </tr>
            </thead>
            <tbody>
              {SMELLS.map((name) => {
                const score = ruleScore(name, aggregation);
                return (
                  <tr key={name}>
                    <th scope="row">{named(name)}</th>
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
          title={simple ? "Ndreqja automatike" : "Motori i refaktorimit"}
          note={
            simple
              ? "Sa nga problemet e gjetura i ndreqi mjeti vetë. Kur nuk është i sigurt që ndreqja nuk e prish programin, mjeti nuk e prek kodin, dhe kjo numërohet si përgjigje e saktë."
              : "Një refuzim është rezultat i saktë dhe numërohet si i tillë: motori nuk e prek kodin kur parakushti nuk provohet nga pema e analizës."
          }
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
          <h3>{simple ? "Pse nuk u ndreqën" : "Pse u refuzuan"}</h3>
          <Distribution counts={refactoring.refused_by_reason} labels={REFUSAL_SQ} total={refactoring.detected} />
          <h3>{simple ? "A kompilohen ato që u ndreqën" : "Verifikimi i atyre që u aplikuan"}</h3>
          <Distribution counts={refactoring.verdicts} labels={VERDICT_SQ} total={refactoring.applied} />
        </Panel>
      </div>

      <Panel
        title={simple ? `Për problemin: ${named(smell)}` : `Për erën: ${named(smell)}`}
        note={
          simple
            ? "Zgjidh një lloj problemi për të parë sa raste gjen sipas rëndësisë, sa pajtohen rregullat me modelin, dhe si ndryshon rezultati kur lëviz një kufi."
            : "Zgjidh erën për ta parë të ndarë sipas ashpërsisë, pajtimin mes dy qasjeve, dhe sa lëviz rezultati kur zhvendoset një prag."
        }
      >
        <div className="chips">
          {SMELLS.map((name) => (
            <button
              key={name}
              className={name === smell ? "chip on" : "chip"}
              onClick={() => setSmell(name)}
              aria-pressed={name === smell}
            >
              {named(name)}
            </button>
          ))}
        </div>

        <div className="split">
          <div>
            <h3>
              {simple
                ? "Sa raste gjen, sipas rëndësisë që u dhanë zhvilluesit"
                : "Recall sipas ashpërsisë që caktuan rishikuesit"}
            </h3>
            <SeverityRecalls smell={smell} simple={simple} />
            <Blockers smell={smell} simple={simple} />
            <h3>{simple ? "Sa pajtohen rregullat me modelin" : "Pajtimi mes dy qasjeve"}</h3>
            <AgreementBar smell={smell} simple={simple} />
            <h3>{simple ? "Matjet që i përdor më shumë modeli" : "Veçoritë që zgjodhi modeli"}</h3>
            <p className="features">
              {ml.per_smell[smell].top_features.map((feature) =>
                simple ? (
                  <span key={feature} className="feature-plain">
                    {metricName(feature)}
                  </span>
                ) : (
                  <code key={feature}>{feature}</code>
                ),
              )}
            </p>
          </div>
          <div>
            <h3>
              {simple
                ? "Si ndryshon nota kur një kufi bëhet më i ulët ose më i lartë"
                : "Sa lëviz MCC-ja kur zhvendoset një prag"}
            </h3>
            <ThresholdSweep smell={smell} simple={simple} />
          </div>
        </div>
      </Panel>

      <ExternalTool simple={simple} />

      <p className="quiet footnote">
        Prodhuar me Python {rules.environment.python}, {rules.environment.platform}
        {commits.length === 1 ? (
          <>
            , commit-i <code>{commits[0]}</code>
          </>
        ) : (
          <>
            . Commit-i ndryshon sipas skedarit të rezultatit — {commits.length} gjithsej,{" "}
            {commits.map((commit, index) => (
              <span key={commit}>
                {index > 0 && ", "}
                <code>{commit}</code>
              </span>
            ))}{" "}
            — sepse eksperimentet u ekzekutuan sipas radhës në të cilën u shkruan
          </>
        )}
        . Ndarja mes trajnimit dhe testimit është e grupuar sipas depos, kurrë e rastësishme
        sipas rreshtave.
      </p>
    </div>
  );
}

function Blockers({ smell, simple }: { smell: string; simple: boolean }) {
  const blocking = blockingFor(smell);
  // Vetëm dy strategjitë që janë konjunksione të pastra e kanë këtë llogari; te
  // të tjerat pyetja «cila klauzolë e ndali» nuk ka përgjigje të vetme.
  if (!blocking) return null;

  const sole = Object.entries(blocking.sole_blocker).sort((a, b) => b[1] - a[1]);
  const many = blocking.missed - blocking.blocked_by_one_clause;
  return (
    <>
      <h3>{simple ? "Pse rregullat nuk i gjetën të gjitha" : "Pse nuk ndezi"}</h3>
      <p className="quiet">
        {simple
          ? `${blocking.missed.toLocaleString("sq")} raste që zhvilluesit i quajtën probleme, por ` +
            `rregullat jo. Te ${many.toLocaleString("sq")} prej tyre mungonte më shumë se një ` +
            "kusht, ndaj nuk ishin raste në kufi."
          : `${blocking.missed.toLocaleString("sq")} raste që rishikuesit i quajtën të tilla dhe ` +
            `strategjia nuk i ndezi. Te ${many.toLocaleString("sq")} prej tyre dështoi më shumë ` +
            "se një klauzolë, ndaj nuk janë raste kufitare."}
      </p>
      <table className="data-grid">
        <thead>
          <tr>
            <th scope="col">{simple ? "Kushti i vetëm që mungoi" : "Klauzola e vetme që ndaloi"}</th>
            <th scope="col">Raste</th>
            <th scope="col">Sa afër erdhi</th>
          </tr>
        </thead>
        <tbody>
          {sole.map(([metric, count]) => (
            <tr key={metric}>
              <th scope="row">{simple ? metricName(metric) : <code>{metric}</code>}</th>
              <td className="figures">{count.toLocaleString("sq")}</td>
              <td>
                <Bar value={blocking.median_shortfall[metric]} tone="rules" format="percent" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="quiet">
        «Sa afër» është mediana e matjes si pjesë e pragut, vetëm për rastet që i ndaloi një
        klauzolë e vetme. Sa më afër njëshit, aq më shumë do të ndihmonte një prag i lëvizur.
      </p>
    </>
  );
}

function ExternalTool({ simple }: { simple: boolean }) {
  const rows = Object.entries(pmd.by_smell);
  return (
    <Panel
      title={simple ? "Krahasim me një mjet të njohur (PMD)" : "Kundrejt një mjeti të gatshëm"}
      note={`PMD ${pmd.pmd_version} mbi të njëjtat depo, me pragjet e veta, i pikëzuar me të njëjtin kod. Intervali është i çiftuar mbi riterheqje depoje: kur e përmban zeron, dy anët nuk dallohen.`}
    >
      <table className="data-grid wide">
        <thead>
          <tr>
            <th scope="col">Era</th>
            <th scope="col">Mostra</th>
            <th scope="col">PMD</th>
            <th scope="col">Ky punim</th>
            <th scope="col">Ndryshimi, IB 95%</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([key, row]) => (
            <tr key={key}>
              <th scope="row">{PMD_ROW_SQ[key] ?? key}</th>
              <td className="figures quiet">{row.scored.toLocaleString("sq")}</td>
              <td>
                <Bar value={row.pmd.mcc} tone="rules" />
              </td>
              <td>{row.ours ? <Bar value={row.ours.mcc} tone="model" /> : <Missing />}</td>
              <td className="figures">
                {row.difference ? (
                  <span className={row.difference.excludes_zero ? "band holds" : "band"}>
                    {row.difference.low >= 0 ? "+" : ""}
                    {row.difference.low.toFixed(3)} deri{" "}
                    {row.difference.high >= 0 ? "+" : ""}
                    {row.difference.high.toFixed(3)}
                  </span>
                ) : (
                  <Missing />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="quiet">
        Feature Envy nuk ka krahasim: PMD nuk ka rregull për të, dhe LawOfDemeter mat zinxhirë
        mesazhesh e jo qasje në të dhëna të huaja. Shifra e tij qëndron nën emrin e vet.{" "}
        {pmd.repositories_failed.length} depo nuk u përpunuan dot dhe{" "}
        {pmd.files_pmd_could_not_read.toLocaleString("sq")} skedarë nuk u lexuan; mostrat e tyre
        dalin nga të dyja kolonat njësoj.
      </p>
    </Panel>
  );
}

function SeverityRecalls({ smell, simple }: { smell: string; simple: boolean }) {
  const variant = rules.per_smell[smell].strategy;
  const levels = ["critical", "major", "minor"].filter(
    (level) => variant.recall_by_severity[level],
  );
  return (
    <table className="data-grid">
      <tbody>
        {levels.map((level) => {
          const entry = variant.recall_by_severity[level];
          return (
            <tr key={level}>
              <th scope="row">{simple ? severityName(level) : level}</th>
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

function AgreementBar({ smell, simple }: { smell: string; simple: boolean }) {
  const { both, only_rules, only_model, neither, kappa, n } = ml.per_smell[smell].vs_rules;
  const cells: Array<[string, number, string]> = [
    ["të dyja", both, "both"],
    [simple ? "vetëm rregullat" : "vetëm A", only_rules, "rules"],
    [simple ? "vetëm modeli" : "vetëm B", only_model, "model"],
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
        κ = {kappa.toFixed(3)} mbi {n.toLocaleString("sq")} mostra.{" "}
        {simple
          ? term("kappa").what
          : "Kappa e heq pajtimin që pritet nga rastësia, i cili mbi një bashkësi kaq të çekuilibruar është i madh."}
      </p>
    </>
  );
}

function ThresholdSweep({ smell, simple }: { smell: string; simple: boolean }) {
  const swept = sweep.per_smell[smell];
  return (
    <table className="data-grid sweep">
      <thead>
        <tr>
          <th>{simple ? "Kufiri" : "Pragu"}</th>
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
            <th scope="row">{simple ? thresholdName(name) : <code>{name}</code>}</th>
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
