import { useEffect, useState } from "react";
import { preview, source } from "./api";
import { Diff } from "./Diff";
import type { Prediction, Preview, Smell, Source } from "./types";

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
  prediction,
  asked,
}: {
  smell: Smell;
  path: string;
  /** The model's verdict on this same entity, when it flagged it too. */
  prediction: Prediction | null;
  /** Whether the model was consulted at all, which is what makes silence mean something. */
  asked: boolean;
}) {
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

      <h3>Kodi</h3>
      <SourceView smell={smell} path={path} />

      <h3>Pse u shënua</h3>
      <Conditions smell={smell} />
      {smell.conditions.length > 0 && <p className="caption">{EXCESS_NOTE}</p>}

      {asked && <ModelVerdict prediction={prediction} />}

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
          Motori nuk e rishkroi këtë vend: {result.detail || result.refusal}. Refuzimi është
          rezultat i saktë, jo dështim.
        </p>
      )}

      {result?.applied && result.before && result.after && (
        <Diff before={result.before} after={result.after} />
      )}
    </article>
  );
}

/**
 * The flagged lines themselves.
 *
 * A tool that measures code and never shows it asks to be taken on trust. The
 * span comes from the detector, so what is displayed is exactly what was
 * measured — no more, and never a different part of the file.
 */
function SourceView({ smell, path }: { smell: Smell; path: string }) {
  const [lines, setLines] = useState<Source | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    setLines(null);
    setFailure(null);
    source(path, smell)
      .then((body) => live && setLines(body))
      .catch((error: Error) => live && setFailure(error.message));
    return () => {
      live = false;
    };
    // The finding identifies the span, so it is the only thing worth watching:
    // listing its fields as well would be the same dependency written twice.
  }, [path, smell]);

  if (failure) return <p className="note">Kodi nuk u lexua dot: {failure}</p>;
  if (!lines) return <p className="note">Duke lexuar…</p>;

  return (
    <>
      <pre className="source">
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
  "Shiriti tregon tepricën mbi kufirin, e kufizuar në 5× — e njëjta madhësi nga e cila " +
  "derivohet ashpërsia.";
