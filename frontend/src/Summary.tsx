import { SMELL_SQ } from "./evaluation";
import type { ModelBlock, Summary } from "./types";

/**
 * Sa u mat, në të njëjtat njësi që përdor lista poshtë.
 *
 * Erërat dhe vendet janë të dyja aty me qëllim: numri i erërave është ai që
 * raporton motori, numri i vendeve është ai që lexuesi do të hapë. Pa të dytin,
 * shiriti thoshte 106 dhe lista thoshte 74 pa asgjë që ta shpjegonte dallimin.
 *
 * Ashpërsia numërohet **sipas vendit**, me të njëjtin rregull që përdor
 * distinktivi i çdo rreshti: më e rënda që mban vendi. Kështu shuma e tri
 * shifrave barazon numrin e vendeve, dhe klikimi nga shiriti te lista nuk
 * ndryshon njësi në rrugë.
 */
/**
 * Sa skedarë nuk u parsuan pastër.
 *
 * Ndarë nga shiriti përmbledhës kur ai u hoq për panelin: paralajmërimi nuk i
 * përkiste atij shiriti, i përkiste analizës, dhe humbja e tij bashkë me të do
 * ta kishte kthyer një projekt gjysmë të palexueshëm në një projekt të pastër
 * (VD-91).
 */
export function Unparsed({ summary }: { summary: Summary }) {
  if (!summary.unparsed) return null;
  return (
    <p className="note unparsed" role="status">
      <b>
        {summary.unparsed} nga {summary.files} {summary.files === 1 ? "skedari" : "skedarët"}
      </b>{" "}
      nuk u parsua pastër, ndaj çfarë u gjet brenda tyre është e paplotë. Numrat më poshtë janë të
      sakta për pjesën tjetër.
    </p>
  );
}

/**
 * What the second approach found, kept apart from what the rules found.
 *
 * Deliberately its own row rather than numbers folded into the summary. The two
 * approaches are not interchangeable: A's count is of published strategies
 * firing, B's is of a classifier trained on how reviewers labelled MLCQ, and
 * adding them would suggest a single total that no measurement supports.
 */
export function ModelBar({ block }: { block: ModelBlock }) {
  if (!block.available) {
    return (
      <p className="note model-note">
        Modeli nuk u pyet dot: {block.reason}
      </p>
    );
  }

  const skipped = block.smells.reduce((total, report) => total + report.incomplete, 0);

  return (
    <div className="summary model">
      {/* The row says whose numbers these are. Without it the second row reads
          as more of the first, and the two approaches are not additive. */}
      <div className="figure name">
        <b>Qasja B</b>
        <span>modeli i trajnuar</span>
      </div>
      {block.smells.map((report) => (
        <div className="figure" key={report.smell}>
          <b>{report.flagged}</b>
          <span>{SMELL_SQ[report.smell] ?? report.smell}</span>
        </div>
      ))}
      {skipped > 0 && (
        <p className="caption">
          {skipped} entitete nuk u gjykuan: u mungonte një matje, dhe modeli nuk pyetet mbi një
          zero të shpikur.
        </p>
      )}
    </div>
  );
}
