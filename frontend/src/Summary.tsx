import { SMELL_SQ } from "./evaluation";
import { countByWorst } from "./sites";
import type { Site } from "./sites";
import type { Analysis, ModelBlock } from "./types";

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
export function SummaryBar({ analysis, sites }: { analysis: Analysis; sites: Site[] }) {
  const { summary } = analysis;
  const byWorst = countByWorst(sites);
  return (
    <div className="summary">
      <Figure value={summary.files} label="skedarë" />
      <Figure value={summary.classes} label="klasa" />
      <Figure value={summary.methods} label="metoda" />
      <Figure value={summary.smells} label="erëra" />
      <Figure value={sites.length} label={sites.length === 1 ? "vend" : "vende"} accent />
      <div className="figure breakdown">
        <b>
          {(["critical", "major", "minor"] as const).map((level) =>
            byWorst[level] ? (
              <span key={level} className={level}>
                {byWorst[level]} {level}
              </span>
            ) : null,
          )}
        </b>
        <span>vende sipas më të rëndës</span>
      </div>
    </div>
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

function Figure({
  value,
  label,
  accent,
}: {
  value: number;
  label: string;
  accent?: boolean;
}) {
  return (
    <div className={`figure${accent ? " accent" : ""}`}>
      <b>{value}</b>
      <span>{label}</span>
    </div>
  );
}
