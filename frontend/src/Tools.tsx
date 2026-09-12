// Kolona e djathtë: çfarë mund të bësh, dhe me çfarë.
//
// Maketi e quan «LOCAL TOOLS» dhe liston katër veprime, nga të cilat dy nuk kanë
// asgjë pas vetes te ky sistem: zgjedhja e rregullave të PMD-së dhe të
// Checkstyle-it, dhe konfigurimi i pragjeve. PMD përdoret vetëm te krahasimi i
// Kapitullit 5 e jo te rruga e produktit, Checkstyle nuk përdoret fare, dhe
// pragjet janë të fiksuara e të cituara — ndryshimi i tyre nga ekrani do ta
// prishte riprodhueshmërinë që shtojca premton.
//
// Prandaj këtu rrinë vetëm veprimet që ekzistojnë, dhe poshtë tyre gjendja që i
// kushtëzon: a u gjet `javac`, a u pyet modeli, a lejohet shkrimi. Një buton që
// nuk do të punojë duhet ta thotë përpara e jo pasi shtypet.

import type { PatchSession } from "./Patch";
import { PatchTrigger } from "./Patch";
import type { TreeState } from "./types";

export function Tools({
  session,
  path,
  ready,
  total,
  tree,
  askedModel,
  onReanalyse,
  onEvaluation,
}: {
  session: PatchSession;
  path: string;
  ready: number;
  total: number;
  /** Null derisa serveri të përgjigjet; mungesa nuk është e njëjta gjë me «jo». */
  tree: TreeState | null;
  askedModel: boolean;
  onReanalyse: () => void;
  onEvaluation: () => void;
}) {
  return (
    <>
      <section className="card" aria-label="Veglat">
        <h2>Veglat</h2>
        <PatchTrigger session={session} ready={ready} total={total} path={path} />
        <div className="stack">
          <button onClick={onReanalyse} disabled={session.busy}>
            Analizo sërish
          </button>
          <button onClick={onEvaluation}>Rezultatet e vlerësimit</button>
        </div>
      </section>

      <section className="card" aria-label="Gjendja">
        <h2>Gjendja</h2>
        <ul className="state">
          <State
            on={session.result?.verified_with_javac ?? null}
            yes="javac u gjet; rishkrimet verifikohen"
            no="javac nuk u gjet; verifikimi ndalet te sintaksa"
            unknown="verifikimi njihet pasi përgatitet patch-i"
          />
          <State
            on={askedModel}
            yes="modeli u pyet për këtë analizë"
            no="vetëm rregullat; modeli nuk u pyet"
          />
          <State
            on={tree === null ? null : tree.writable}
            yes="pema e punës është e pastër; shkrimi lejohet"
            no={tree?.detail ? `shkrimi nuk lejohet: ${tree.detail}` : "shkrimi nuk lejohet këtu"}
            unknown="gjendja e pemës po lexohet"
          />
        </ul>
      </section>
    </>
  );
}

/**
 * Një rresht gjendjeje me tri vlera, e jo dy.
 *
 * «Nuk dihet ende» dhe «jo» janë gjëra të ndryshme, dhe ngatërrimi i tyre është
 * pikërisht si një ekran i thotë përdoruesit se diçka dështoi ndërsa ajo nuk ka
 * nisur.
 */
function State({
  on,
  yes,
  no,
  unknown,
}: {
  on: boolean | null;
  yes: string;
  no: string;
  unknown?: string;
}) {
  if (on === null) {
    return (
      <li className="unknown">
        <span className="dot" aria-hidden="true" />
        {unknown ?? "nuk dihet ende"}
      </li>
    );
  }
  return (
    <li className={on ? "yes" : "no"}>
      <span className="dot" aria-hidden="true" />
      {on ? yes : no}
    </li>
  );
}
