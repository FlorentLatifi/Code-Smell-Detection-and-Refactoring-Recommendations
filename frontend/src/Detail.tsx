import { useEffect, useState } from "react";
import { explanationText, noteText, preview, source } from "./api";
import { Diff } from "./Diff";
import { REFUSAL_SQ } from "./evaluation";
import { useSimple } from "./mode";
import {
  conditionSentence,
  metricEntry,
  metricName,
  reading,
  refactoringEntry,
  severityEntry,
  smellEntry,
} from "./plain";
import type { Prediction, Preview, Smell, Source, Summary } from "./types";

/**
 * Everything known about one finding: the code, why it fired, and what it would
 * take to fix it.
 *
 * Split out of `App` because it is the half of the screen that grows: the list
 * beside it has one shape, while this side gained the source, the conditions and
 * the diff and will gain more.
 */
export function Detail({
  smell,
  path,
  scope,
  prediction,
  asked,
}: {
  smell: Smell;
  path: string;
  /** Whether `path` is one file or a directory, as the analysis reported it. */
  scope?: Summary["scope"];
  /** The model's verdict on this same entity, when it flagged it too. */
  prediction: Prediction | null;
  /** Whether the model was consulted at all, which is what makes silence mean something. */
  asked: boolean;
}) {
  const [result, setResult] = useState<Preview | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const simple = useSimple();
  const plain = smellEntry(smell.smell_type);

  async function ask() {
    setBusy(true);
    setFailure(null);
    setResult(null);
    try {
      setResult(await preview(path, smell, scope));
    } catch (error) {
      setFailure((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <article>
      {simple && plain ? (
        <>
          <h2>{plain.name}</h2>
          <p className="caption">
            Emri teknik: <code>{smell.smell_type}</code>
          </p>
        </>
      ) : (
        <h2 title={plain?.name}>{smell.smell_type}</h2>
      )}
      <p className="where">
        {smell.package ? `${smell.package}.` : ""}
        {smell.class_name}
        {smell.method ? `.${smell.method}` : ""}
      </p>
      <p className="file">
        {smell.file_path}:{smell.start_line}–{smell.end_line}
      </p>

      {simple && plain && <Meaning smell={smell} what={plain.what} why={plain.why} />}

      <h3>Kodi</h3>
      <SourceView smell={smell} path={path} scope={scope} />

      <h3>Pse u shënua</h3>
      {simple ? (
        <PlainConditions smell={smell} />
      ) : (
        <>
          <Conditions smell={smell} />
          {smell.conditions.length > 0 && <p className="caption">{EXCESS_NOTE}</p>}
        </>
      )}

      {asked && (simple ? <PlainVerdict prediction={prediction} /> : <ModelVerdict prediction={prediction} />)}

      {simple ? (
        <details className="all-metrics">
          <summary>Të gjitha matjet e këtij vendi</summary>
          <Metrics metrics={smell.metrics} simple />
        </details>
      ) : (
        <>
          <h3>Metrikat e matura</h3>
          <Metrics metrics={smell.metrics} simple={false} />
        </>
      )}

      {simple ? (
        <>
          <h3>Si mund të ndreqet</h3>
          {plain && <p>{plain.fix}</p>}
          <ul className="refactorings plain">
            {smell.refactorings.map((name) => {
              const step = refactoringEntry(name);
              return (
                <li key={name}>
                  <b>{step?.name ?? name}</b>
                  {step && <> — {step.what}</>}
                </li>
              );
            })}
          </ul>
        </>
      ) : (
        <>
          <h3>Refaktorimet e propozuara</h3>
          <ul className="refactorings">
            {smell.refactorings.map((name) => (
              <li key={name} title={refactoringEntry(name)?.name}>
                {name}
              </li>
            ))}
          </ul>
        </>
      )}

      {smell.automated ? (
        <button className="primary" onClick={ask} disabled={busy}>
          {busy
            ? "Duke përgatitur…"
            : simple
              ? "Shiko si do ta ndreqte mjeti"
              : "Shfaq ndryshimin e propozuar"}
        </button>
      ) : simple ? (
        <p className="note">
          Mjeti nuk e ndreq dot vetë këtë problem: do t'i duhej të gjente çdo vend në projekt ku
          përdoret kjo pjesë kodi, dhe këtë nuk e provon dot. Ndreqja mbetet për ty, me hapat më
          sipër.
        </p>
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

      {result && !result.applied && <Refused result={result} simple={simple} />}

      {result?.applied && result.notes?.length ? (
        <ul className="note rewrite-notes">
          {result.notes.map((note) => (
            <li key={note.code}>{noteText(note)}</li>
          ))}
        </ul>
      ) : null}

      {result?.applied && result.before && result.after && (
        <Diff before={result.before} after={result.after} />
      )}
    </article>
  );
}

/**
 * Pse motori nuk e rishkroi vendin.
 *
 * Hollësia vjen si kod dhe shkruhet shqip (VD-123). Vetëm kur kodi mungon ose
 * nuk njihet, ekrani bie te arsyeja e përgjithshme dhe te fjalia anglisht e
 * motorit, e shënuar si e tillë e jo si pjesë e fjalisë (VD-122).
 */
function Refused({ result, simple }: { result: Preview; simple: boolean }) {
  const explained = explanationText(result.explanation);
  if (simple) {
    const reason = explained ?? `${REFUSAL_SQ[result.refusal ?? ""] ?? result.refusal}.`;
    return (
      <p className="note">
        Mjeti nuk e ndreqi këtë vend: {reason} Kjo është e qëllimshme: mjeti e prek kodin vetëm
        kur është i sigurt që ndreqja nuk e prish programin.
      </p>
    );
  }
  if (explained) {
    return (
      <p className="note">
        Motori nuk e rishkroi këtë vend: {explained} Refuzimi është rezultat i saktë, jo
        dështim.
      </p>
    );
  }
  return (
    <p className="note">
      Motori nuk e rishkroi këtë vend: {REFUSAL_SQ[result.refusal ?? ""] ?? result.refusal}.
      Refuzimi është rezultat i saktë, jo dështim.
      {result.detail && (
        <>
          {" "}
          <span className="refusal-detail">
            Hollësia e motorit, anglisht: <code>{result.detail}</code>
          </span>
        </>
      )}
    </p>
  );
}

/**
 * Çfarë do të thotë era, pse ka rëndësi dhe sa e rëndë është, para çdo numri.
 *
 * Në mënyrën teknike këto i jep vetë emri, për atë që e njeh literaturën. Për një
 * lexues tjetër emri nuk thotë asgjë, dhe pa këtë seksion paneli fillon me kod dhe
 * matje pa i thënë çfarë po kërkon te to (VD-144).
 */
function Meaning({ smell, what, why }: { smell: Smell; what: string; why: string }) {
  const grade = severityEntry(smell.severity);
  return (
    <section className="meaning" aria-label="Çfarë do të thotë">
      <p>
        <b>Çfarë do të thotë.</b> {what}
      </p>
      <p>
        <b>Pse ka rëndësi.</b> {why}
      </p>
      {grade && (
        <p>
          <b>Ashpërsia: {grade.name.toLowerCase()}.</b> {grade.what}
        </p>
      )}
    </section>
  );
}

/** Çdo klauzolë si fjali: emri i matjes, vlera dhe kufiri. */
function PlainConditions({ smell }: { smell: Smell }) {
  if (smell.conditions.length === 0) {
    return <p className="empty">{smell.rationale}</p>;
  }
  return (
    <>
      <p className="caption">
        Mjeti e mat kodin dhe e shënon kur matjet kalojnë kufijtë e botuar në literaturë. Këtu i
        kaloi të gjithë këta:
      </p>
      <ul className="plain-conditions">
        {smell.conditions.map((condition) => {
          const entry = metricEntry(condition.metric);
          return (
            <li key={`${condition.metric}${condition.operator}`}>
              {conditionSentence(condition)}
              {entry && <span className="hint"> {entry.what}</span>}
            </li>
          );
        })}
      </ul>
    </>
  );
}

/**
 * Matjet e entitetit, me emrin e thjeshtë ose me atë teknik.
 *
 * Në mënyrën teknike emri i thjeshtë rri te `title`, që edhe dikush që i njeh
 * shkurtimet ta gjejë kuptimin e një metrike të rrallë pa dalë nga paneli.
 */
function Metrics({ metrics, simple }: { metrics: Record<string, number>; simple: boolean }) {
  return (
    <table className="metrics">
      <tbody>
        {Object.entries(metrics).map(([name, value]) => {
          const entry = metricEntry(name);
          return (
            <tr key={name}>
              {simple ? (
                <th title={entry?.what}>
                  {entry?.name ?? name} <code className="quiet">{name}</code>
                </th>
              ) : (
                <th title={entry ? `${entry.name}. ${entry.what}` : undefined}>{name}</th>
              )}
              <td>{simple ? reading(value) : value}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

/**
 * Mendimi i modelit, si fjali e jo si tabelë me rënie gjasash.
 *
 * Mbetet i njëjti verdikt dhe e njëjta matje vendimtare si te `ModelVerdict`;
 * vetëm thuhet me fjalë.
 */
function PlainVerdict({ prediction }: { prediction: Prediction | null }) {
  if (!prediction) {
    return (
      <>
        <h3>Mendimi i modelit</h3>
        <p className="note">
          Modeli, që ka mësuar nga gjykimet e zhvilluesve me përvojë, nuk e shënoi këtë vend.
          Problemi mbështetet vetëm te rregullat, ndaj mund të jetë më pak i sigurt.
        </p>
      </>
    );
  }
  const decisive = prediction.contributions.find((c) => c.decisive) ?? null;
  return (
    <>
      <h3>Mendimi i modelit</h3>
      <p className="verdict">
        Edhe modeli e shënon këtë vend: sipas tij, gjasa që këtu të ketë problem është{" "}
        <b>{(prediction.probability * 100).toFixed(0)}%</b>. Kur rregullat dhe modeli pajtohen,
        gjetja është më e besueshme.
      </p>
      <p className="caption">
        {decisive
          ? `Arsyeja kryesore: ${metricName(decisive.feature).toLowerCase()} është ` +
            `${reading(decisive.value)}, ndërsa zakonisht është ${reading(decisive.typical)}. ` +
            `Po të ishte e zakonshme, modeli nuk do ta shënonte.`
          : "Asnjë matje e vetme nuk e shpjegon vendimin e modelit: disa matje që thonë të " +
            "njëjtën gjë e mbajnë atë së bashku."}
      </p>
    </>
  );
}

/**
 * The flagged lines themselves.
 *
 * A tool that measures code and never shows it asks to be taken on trust. The
 * span comes from the detector, so what is displayed is exactly what was
 * measured — no more, and never a different part of the file.
 */
function SourceView({
  smell,
  path,
  scope,
}: {
  smell: Smell;
  path: string;
  scope?: Summary["scope"];
}) {
  const [lines, setLines] = useState<Source | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    setLines(null);
    setFailure(null);
    source(path, smell, scope)
      .then((body) => live && setLines(body))
      .catch((error: Error) => live && setFailure(error.message));
    return () => {
      live = false;
    };
    // The finding identifies the span, so it is the only thing worth watching:
    // listing its fields as well would be the same dependency written twice.
  }, [path, smell, scope]);

  if (failure) return <p className="note">Kodi nuk u lexua dot: {failure}</p>;
  if (!lines) return <p className="note">Duke lexuar…</p>;

  return (
    <>
      {/* Rrëshqet horizontalisht kur një rresht është i gjatë, ndaj duhet të jetë
          i arritshëm me tastierë: përndryshe pjesa e djathtë e kodit nuk shihet
          dot pa mouse. `tabIndex` e bën fokusabël, dhe emri thotë çfarë është. */}
      <pre className="source" tabIndex={0} role="region" aria-label="Kodi i gjetjes">
        {lines.lines.map((text, index) => (
          <span className="line" key={lines.start_line + index}>
            <span className="gutter">{lines.start_line + index}</span>
            {text}
          </span>
        ))}
      </pre>
      {lines.truncated && (
        <p className="caption">Shkurtuar; entiteti vazhdon përtej rreshtit {lines.end_line}.</p>
      )}
    </>
  );
}

/**
 * Why the detector fired: the measurement beside the bound it passed.
 *
 * The API sends the clauses as data as well as as a sentence, so the value and
 * the threshold can be put in the same column and compared by eye.
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
                {/* Vija vertikale është pragu, te 1×. Shiriti nis aty dhe mbaron te
                    teprica e matur, e kufizuar në 5× si te ashpërsia: lexuesi sheh
                    sa larg vijës është kodi, jo vetëm dy numra (VD-119). */}
                <span className="gauge" title={`${excess.toFixed(1)}× pragu`} aria-hidden="true">
                  <span className="fill" style={{ left: "20%", width: `${(width - 0.2) * 100}%` }} />
                  <span className="tick" />
                </span>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

/**
 * What the classifier says about the same entity, in the same shape as a rule.
 *
 * The standing objection to machine-learned smell detection is that it wins on
 * the numbers and says nothing about any particular class. So the verdict is not
 * shown alone: beside it is the measurement that holds it up, and what the
 * probability falls to when that measurement is made typical. A reader compares
 * this table with the one above it and sees two approaches answering in the same
 * units.
 *
 * Silence is a result too. When the model was asked and did not flag the entity,
 * that disagreement is stated, because A∩B is the strongest signal the thesis
 * reports and a reader needs to know which side of it a finding sits on.
 */
function ModelVerdict({ prediction }: { prediction: Prediction | null }) {
  if (!prediction) {
    return (
      <>
        <h3>Qasja B — modeli</h3>
        <p className="note">
          Modeli nuk e shënoi këtë entitet. Të dyja qasjet nuk pajtohen këtu, ndaj gjetja
          mbështetet vetëm te strategjia e botuar.
        </p>
      </>
    );
  }

  const decisive = prediction.contributions.find((c) => c.decisive) ?? null;

  return (
    <>
      <h3>Qasja B — modeli</h3>
      <p className="verdict">
        <b>{(prediction.probability * 100).toFixed(0)}%</b> gjasë sipas modelit — të dyja qasjet
        pajtohen për këtë entitet.
      </p>

      <table className="conditions contributions">
        <tbody>
          {prediction.contributions.map((contribution) => {
            // The drop is a probability, so it already sits between 0 and 1.
            const width = Math.min(Math.max(contribution.drop, 0), 1);
            return (
              <tr
                key={contribution.feature}
                className={contribution.decisive ? "decisive" : undefined}
              >
                <th>{contribution.feature}</th>
                <td className="measured">{contribution.value}</td>
                <td className="bound">tipike {contribution.typical}</td>
                <td className="excess">
                  <span
                    style={{ width: `${width * 100}%` }}
                    title={`bie ${contribution.drop.toFixed(3)}`}
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <p className="caption">
        {decisive
          ? `Po të ishte ${decisive.feature} tipike (${decisive.typical}) në vend të ` +
            `${decisive.value}, modeli nuk do ta shënonte. Shiriti tregon sa bie gjasa kur ` +
            `secila matje kthehet në tipike.`
          : MASKED_NOTE}
      </p>
    </>
  );
}

/**
 * When no single measurement carries the verdict, that is said rather than hidden.
 *
 * Two measurements that say the same thing mask each other: replacing either one
 * alone moves nothing, and the entity looks unexplained. It is a real limit of
 * explaining one measurement at a time, and the thesis reports it as one.
 */
const MASKED_NOTE =
  "Asnjë matje e vetme nuk e mban verdiktin: kur dy matje thonë të njëjtën gjë, " +
  "zëvendësimi i njërës nuk e lëviz gjasën. Ky është kufi i njohur i shpjegimit " +
  "matje-për-matje, jo mungesë arsyeje.";

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
  "Vija vertikale është pragu. Shiriti tregon sa e kalon matja, deri në 5×, e njëjta " +
  "tepricë nga e cila derivohet ashpërsia.";
