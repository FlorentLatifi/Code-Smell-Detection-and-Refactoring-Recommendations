// Çfarë e shënoi vetëm modeli, dhe asnjë strategji nuk e preku.
//
// Këto verdikte ishin gjithnjë te përgjigjja dhe kurrë te ekrani. Kutiza
// përmbledhëse i numëronte — «Qasja B: 2 blob» — ndërsa lista tregonte vetëm
// atë që e kishte gjetur një rregull, ndaj lexuesi merrte një numër dhe asnjë
// rrugë drejt tij. Mbi një projekt me 322 skedarë kështu fshiheshin 515 nga
// 1870 verdikte (VD-93).
//
// Rrinë veç e nuk përzihen me listën e rregullave, sepse nuk kanë atë që ajo
// listë rendit: ashpërsia derivohet nga teprica mbi prag, dhe këtu nuk ka prag
// të tejkaluar. Bashkimi i tyre do të kërkonte një ashpërsi të trilluar, që
// është pikërisht gjëja që ky projekt nuk e bën.

import { useState } from "react";
import type { Prediction } from "./types";

/** Sa rreshta shfaqen para se lista të kërkojë zgjerim. */
const PAGE = 20;

export function ModelOnly({ predictions }: { predictions: Prediction[] }) {
  const [limit, setLimit] = useState(PAGE);
  if (predictions.length === 0) return null;

  const visible = predictions.slice(0, limit);
  return (
    <section className="panel model-only" aria-label="Gjetjet vetëm të modelit">
      <h2>Vetëm modeli i shënoi</h2>
      <p className="caption">
        {predictions.length} {predictions.length === 1 ? "entitet" : "entitete"} që asnjë strategji
        nuk i gjeti. Nuk kanë ashpërsi, sepse ashpërsia derivohet nga teprica mbi një prag dhe këtu
        asnjë prag nuk u tejkalua. Renditur sipas gjasës që jep modeli.
      </p>
      <table className="predictions">
        <thead>
          <tr>
            <th scope="col">Entiteti</th>
            <th scope="col">Era</th>
            <th scope="col">Gjasa</th>
            <th scope="col">Matja vendimtare</th>
            <th scope="col">Vendi</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((prediction) => (
            <Row key={rowKey(prediction)} prediction={prediction} />
          ))}
        </tbody>
      </table>
      {predictions.length > visible.length && (
        <p className="more">
          <button className="link" onClick={() => setLimit((n) => n + PAGE)}>
            Shfaq {Math.min(PAGE, predictions.length - visible.length)} të tjera
          </button>
        </p>
      )}
    </section>
  );
}

function rowKey(prediction: Prediction): string {
  return JSON.stringify([
    prediction.file_path,
    prediction.class_name,
    prediction.start_line,
    prediction.smell,
  ]);
}

function Row({ prediction }: { prediction: Prediction }) {
  // E njëjta matje që paneli i detajit e quan vendimtare: ajo që vetëm ajo e ul
  // gjasën nën kufirin e vendimit. Kur asnjë s'është e tillë, thuhet ashtu e nuk
  // zgjidhet një e afërt në vend të saj.
  const decisive = prediction.contributions.find((c) => c.decisive) ?? null;
  return (
    <tr>
      <th scope="row">
        <span className="where">
          {prediction.class_name}
          {prediction.method ? `.${prediction.method}` : ""}
        </span>
      </th>
      <td>{prediction.smell}</td>
      <td className="number">{(prediction.probability * 100).toFixed(0)}%</td>
      <td>
        {decisive ? (
          `${decisive.feature} = ${decisive.value}`
        ) : (
          <span className="quiet">asnjë e vetme</span>
        )}
      </td>
      <td className="file">
        {prediction.file_path}:{prediction.start_line}
      </td>
    </tr>
  );
}
