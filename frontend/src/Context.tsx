// Konteksti i një analize: çfarë u lexua, sa ishte, dhe kur.
//
// Rezultatet rrinin pa asnjë prej tyre. Numri i erërave nuk do të thotë asgjë pa
// madhësinë nga e cila doli — dyzet erëra mbi treqind rreshta dhe dyzet mbi
// tridhjetë mijë janë dy gjendje krejt të ndryshme — dhe pa kohën askush nuk e
// di nëse po shikon atë që sapo kërkoi apo atë që mbeti në ekran.

import type { Analysis } from "./types";

export function Context({
  path,
  analysis,
  seconds,
  askedModel,
}: {
  path: string;
  analysis: Analysis;
  /** Sa zgjati kërkesa, matur te klienti sepse vetëm ai e di kur e nisi. */
  seconds: number;
  askedModel: boolean;
}) {
  const { loc } = analysis.summary;
  return (
    <div className="context">
      <span className="where" title={path}>
        {path}
      </span>
      <span className="facts">
        {loc !== undefined && (
          <span>
            <b>{loc.toLocaleString("sq")}</b> rreshta kodi
          </span>
        )}
        <span>
          <b>{analysis.summary.files.toLocaleString("sq")}</b> skedarë
        </span>
        <span>
          <b>{analysis.summary.classes.toLocaleString("sq")}</b> klasa
        </span>
        <span>
          <b>{analysis.summary.methods.toLocaleString("sq")}</b> metoda
        </span>
        <span>u analizua për {seconds < 1 ? "nën një sekondë" : `${Math.round(seconds)} s`}</span>
        <span>{askedModel ? "me modelin" : "vetëm rregullat"}</span>
      </span>
    </div>
  );
}
