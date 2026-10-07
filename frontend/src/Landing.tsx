// Ekrani i parë, kur ende nuk është analizuar asgjë.
//
// Ishte një fjali: «Shkruaj shtegun e një projekti Java për të filluar». E saktë
// dhe e padobishme. Dikush që e hap mjetin nuk mëson dot as çfarë bën, as sa
// mirë e bën, as çfarë e mban atë pohim — dhe mjeti duket sikur nuk ka bërë
// asgjë, ndërsa vlerësimi i tij mbi 512 depo është i komituar dy dosje më tutje.
//
// Asnjë shifër këtu nuk shtypet me dorë. Të gjitha lexohen nga `data/results/`,
// nga të njëjtët skedarë që ndërton Kapitulli 5, ndaj ekrani nuk mund të pohojë
// diçka që punimi nuk e raporton.

import {
  corpusRepositories,
  dataset,
  ml,
  refactoring,
  ruleScore,
  SMELL_SQ,
  SMELLS,
} from "./evaluation";
import { useSimple } from "./mode";
import { smellName, term } from "./plain";

export function Landing({ root, onPick }: { root: string | null; onPick: () => void }) {
  const simple = useSimple();
  if (simple) {
    return (
      <div className="landing">
        <section className="lead">
          <h2>Gjej dhe ndreq pjesët e vështira të kodit tënd Java</h2>
          <p>
            Mjeti e lexon projektin tënd dhe gjen pjesët që janë të vështira për t'u lexuar ose
            ndryshuar, të quajtura «erëra kodi». Për secilën të thotë me fjalë të thjeshta çfarë
            nuk shkon, pse ka rëndësi dhe si ndreqet. Disa prej tyre i ndreq edhe vetë, por vetëm
            pasi t'i shikosh dhe t'i pranosh. Gjithçka punon në kompjuterin tënd.
          </p>
          <ol className="steps">
            <li>Zgjidh projektin.</li>
            <li>Shiko listën e problemeve, nga më i rëndi.</li>
            <li>Hap një problem për ta kuptuar dhe për ta ndrequr.</li>
          </ol>
          <p className="start">
            <button type="button" className="primary" onClick={onPick}>
              Zgjidh një projekt Java
            </button>
          </p>
          <p className="hint">
            Zgjidh një dosje nga kompjuteri, ose ngjit lidhjen e një projekti publik te skeda «Nga
            GitHub». Butoni «Teknike» lart djathtas i shfaq gjetjet me emrat dhe matjet e
            literaturës.
          </p>
        </section>

        <div className="approaches">
          {(["rules", "model", "engine"] as const).map((key) => (
            <article className="approach" key={key}>
              <h3>{term(key).name}</h3>
              <p>{term(key).what}</p>
            </article>
          ))}
        </div>

        <section className="evidence">
          <h3>Sa i besueshëm është</h3>
          <p className="hint">
            Mjeti u provua mbi {corpusRepositories.toLocaleString("sq")} projekte reale Java dhe{" "}
            {dataset.rows.toLocaleString("sq")} pjesë kodi, që zhvillues profesionistë i kishin
            gjykuar më parë. Skeda «Vlerësimi» i tregon rezultatet të plota, me shpjegim për çdo
            shifër.
          </p>
          <ScoreRow variant="model" simple />
          <p className="hint">{term("mcc").what}</p>
        </section>
      </div>
    );
  }
  return (
    <div className="landing">
      <section className="lead">
        <h2>Tri qasje mbi të njëjtin kod</h2>
        <p>
          Strategji detektimi me metrika nga literatura, një klasifikues i trajnuar mbi gjykimet e
          rishikuesve, dhe një motor refaktorimi që rishkruan vetëm atë që e provon dot të sigurt.
          Të tria ekzekutohen lokalisht dhe asnjëra nuk e prek kodin tënd.
        </p>
        {/* Nisja është një buton e jo një udhëzim: kushdo që e hap mjetin duhet
            të mund të nisë pa ditur ku lexon serveri (VD-126). */}
        <p className="start">
          <button type="button" className="primary" onClick={onPick}>
            Zgjidh një projekt Java
          </button>
        </p>
        <p className="hint">
          Zgjidh një dosje nga kompjuteri, ose importo një depo publike nga GitHub te skeda «Nga
          GitHub». Analiza lexon vetëm brenda dosjes që serveri e ka të lejuar
          {root ? (
            <>
              , që është <code>{root}</code>, dhe brenda dosjes së depove të importuara.
            </>
          ) : (
            "."
          )}
        </p>
      </section>

      <Approaches />
      <Evidence />
    </div>
  );
}

/** Çfarë bën secila qasje, me shifrën që e mban atë pohim. */
function Approaches() {
  return (
    <div className="approaches">
      <article className="approach">
        <h3>
          <span className="tag">A</span> Rregullat
        </h3>
        <p>
          Strategjitë e Lanza &amp; Marinescu-t dhe të Fowler-it, me pragje të cituara. Çdo gjetje
          vjen me klauzolat e matura, ndaj «pse u shënua» ka gjithnjë përgjigje.
        </p>
        <ScoreRow variant="strategy" />
      </article>

      <article className="approach">
        <h3>
          <span className="tag">B</span> Modeli
        </h3>
        <p>
          I trajnuar mbi MLCQ-në me ndarje sipas depos, që asnjë depo të mos jetë njëherësh te
          trajnimi e te testi. Jep gjasën dhe matjen që e mban atë.
        </p>
        <ScoreRow variant="model" />
      </article>

      <article className="approach">
        <h3>
          <span className="tag">C</span> Refaktorimi
        </h3>
        <p>
          Transformime mbi pemën sintaksore, të verifikuara me <code>javac</code>. Kur parakushtet
          nuk provohen dot, motori refuzon dhe e thotë arsyen.
        </p>
        <dl className="figures-row">
          <Figure value={refactoring.detected} label="vende të gjetura" />
          <Figure value={refactoring.applied} label="të transformuara" />
          <Figure
            value={`${Math.round((refactoring.applied / refactoring.detected) * 100)}%`}
            label="e vendeve"
          />
        </dl>
      </article>
    </div>
  );
}

/**
 * MCC-ja e secilës erë, për njërën nga dy qasjet.
 *
 * MCC e jo saktësia, për të njëjtën arsye si te skeda e vlerësimit: mbi një
 * bashkësi ku shumica e etiketave janë «asnjë», një detektor që nuk ndez kurrë
 * merr saktësi të lartë dhe MCC zero.
 */
function ScoreRow({ variant, simple = false }: { variant: "strategy" | "model"; simple?: boolean }) {
  return (
    <table className="mcc">
      {simple && (
        <caption className="caption">Nota e saktësisë së modelit (MCC), sipas problemit</caption>
      )}
      <tbody>
        {SMELLS.map((smell) => {
          const score = variant === "strategy" ? ruleScore(smell, "mean").mcc : modelMcc(smell);
          return (
            <tr key={smell}>
              <th scope="row">{simple ? smellName(smell) : (SMELL_SQ[smell] ?? smell)}</th>
              <td>{score === null ? "—" : score.toFixed(3)}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

/** MCC-ja e modelit më të mirë për një erë, ose null kur nuk u trajnua asnjë. */
function modelMcc(smell: string): number | null {
  const per = ml.per_smell[smell];
  if (!per) return null;
  return per.models[per.best_model]?.mcc ?? null;
}

/** Sa i madh është bazamenti mbi të cilin qëndrojnë shifrat e mësipërme. */
function Evidence() {
  return (
    <section className="evidence">
      <h3>Mbi çfarë janë matur</h3>
      <dl className="figures-row wide">
        <Figure value={corpusRepositories} label="depo Java" />
        <Figure value={dataset.rows} label="mostra të vlerësuara" />
        <Figure value={dataset.samples_considered} label="mostra në MLCQ" />
        <Figure value={refactoring.files} label="skedarë të rishkruar e verifikuar" />
      </dl>
      <p className="hint">
        Gjykimet vijnë nga zhvillues profesionistë, jo nga vetë mjeti. Çdo shifër këtu lexohet nga
        skedarët e komituar te <code>data/results/</code> dhe është e njëjta që raporton punimi.
        Skeda «Vlerësimi» i hap të plota.
      </p>
    </section>
  );
}

function Figure({ value, label }: { value: number | string; label: string }) {
  return (
    <div className="figure">
      <dt>{typeof value === "number" ? value.toLocaleString("sq") : value}</dt>
      <dd>{label}</dd>
    </div>
  );
}
