// Dy panelet e mbetura: krahasimi i dy qasjeve, dhe skedarët më të ndotur.

import { Suspense, lazy, memo } from "react";
import { Card } from "./DashboardLayout";

/** Vizatimi vjen në copën e vet, sepse Recharts-i nuk i duhet ekranit të parë. */
const ScoreBars = lazy(() => import("./ScoreBars"));

export interface ScoreRow {
  smell: string;
  rules: number | null;
  model: number | null;
}

/**
 * MCC për secilën erë, të dyja qasjet krah për krah.
 *
 * MCC e jo saktësia: mbi një bashkësi ku shumica e etiketave janë «asnjë», një
 * detektor që nuk ndez kurrë merr saktësi të lartë dhe MCC zero. Boshti ndalet
 * te 1 sepse ai është maksimumi, dhe një bosht që rritet me të dhënat i bën 0.27
 * e 0.29 të duken larg njëra-tjetrës.
 */
function PerformanceChartsView({ scores }: { scores: ScoreRow[] }) {
  const label = scores
    .map((row) => `${row.smell}: rregullat ${row.rules ?? "—"}, modeli ${row.model ?? "—"}`)
    .join("; ");
  return (
    <Card title="Rregullat kundrejt modelit, MCC">
      <div className="h-[270px] px-4 pt-2 pb-4" role="img" aria-label={label}>
        {/* Si te llojet: etiketa e mban përmbajtjen, vizatimi fshihet. Etiketa
            është këtu e jo te copa e vonuar, që të lexohet pa pritur vizatimin;
            hapësira ka lartësinë e vet, që faqja të mos kërcejë kur ai mbërrin. */}
        <div className="h-full w-full" aria-hidden="true">
          <Suspense fallback={null}>
            <ScoreBars scores={scores} />
          </Suspense>
        </div>
      </div>
    </Card>
  );
}

export type Severity = "critical" | "major" | "minor";

export interface FileRow {
  cls: string;
  path: string;
  file: string;
  /** Çelësi i renditjes: sa vende për t'u ndrequr, jo sa erëra (`hotspots`). */
  sites: number;
  smells: number;
  severity: Severity;
}

/** Ashpërsia si fjalë me ngjyrë, e njëjta gjuhë si te lista e vendeve. */
const SEVERITY_INK: Record<Severity, string> = {
  critical: "text-high-ink",
  major: "text-medium-ink",
  minor: "text-low-ink",
};

function SmellyFilesTableView({
  rows,
  onPick,
}: {
  rows: FileRow[];
  onPick: (file: string) => void;
}) {
  if (rows.length === 0) return null;
  return (
    <Card title="Skedarët më të ndotur">
      <div className="overflow-x-auto px-4 pb-2">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-ink-200 text-left dark:border-ink-800">
              <Th>Klasa</Th>
              <Th>Shtegu</Th>
              {/* Renditja është sipas vendeve, ndaj kolona e tyre shfaqet e para.
                  Pa të, `TestRelation` me 53 erëra dilte mbi `RelationalOperations`
                  me 117, dhe asgjë e dukshme nuk e shpjegonte (VD-110). */}
              <Th align="right">Vende</Th>
              <Th align="right">Erëra</Th>
              <Th>Ashpërsia</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-200 dark:divide-ink-800">
            {rows.map((row) => (
              <tr key={row.file} className="transition hover:bg-ink-50 dark:hover:bg-ink-800/40">
                <td className="py-2.5 pr-4">
                  {/* Buton e jo `onClick` mbi rreshtin: një `tr` nuk merr fokus, ndaj
                      tabela nuk përdorej dot fare me tastierë. */}
                  <button
                    type="button"
                    onClick={() => onPick(row.file)}
                    title="Shfaq vendet e këtij skedari te lista"
                    className="h-auto max-w-full truncate rounded-sm border-0 bg-transparent p-0 text-left font-mono text-[13px] font-medium text-ink-900 underline-offset-2 hover:underline dark:text-white"
                  >
                    {row.cls}
                  </button>
                </td>
                <td
                  className="max-w-[220px] truncate py-2.5 pr-4 font-mono text-xs text-ink-500 dark:text-ink-400"
                  title={row.path}
                >
                  {row.path}
                </td>
                <td className="py-2.5 pr-4 text-right font-semibold tabular-nums text-ink-900 dark:text-white">
                  {row.sites}
                </td>
                <td className="py-2.5 pr-4 text-right tabular-nums text-ink-600 dark:text-ink-300">
                  {row.smells}
                </td>
                <td className={`py-2.5 text-xs font-medium ${SEVERITY_INK[row.severity]}`}>
                  {row.severity}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function Th({ children, align = "left" }: { children: React.ReactNode; align?: "left" | "right" }) {
  return (
    <th
      scope="col"
      className={`py-2 pr-4 text-xs font-medium text-ink-500 last:pr-0 dark:text-ink-400 ${
        align === "right" ? "text-right" : ""
      }`}
    >
      {children}
    </th>
  );
}

// Asnjëri nuk varet nga filtrat, ndaj nuk kanë pse rivizatohen me çdo shkronjë të
// kërkimit. Grafiku i Recharts-it është pjesa më e shtrenjtë e një rivizatimi.
export const PerformanceCharts = memo(PerformanceChartsView);
export const SmellyFilesTable = memo(SmellyFilesTableView);
