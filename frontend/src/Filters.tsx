import { useSimple } from "./mode";
import { severityName, smellName } from "./plain";
import type { Analysis, Severity } from "./types";

/** Si renditet lista. Ashpërsia e para është ajo që një lexues pret. */
export type Order = "severity" | "score" | "file";

export const ORDER_LABELS: Record<Order, string> = {
  severity: "ashpërsia",
  score: "teprica",
  file: "skedari",
};

/** Të njëjtat renditje, me fjalë që nuk kërkojnë të dish si derivohet ashpërsia. */
const ORDER_PLAIN: Record<Order, string> = {
  severity: "më të rëndat së pari",
  score: "sa e kalojnë kufirin",
  file: "sipas skedarit",
};

export function Filters({
  analysis,
  severity,
  kind,
  order,
  query,
  agreed,
  hasModel,
  onSeverity,
  onKind,
  onOrder,
  onQuery,
  onAgreed,
}: {
  analysis: Analysis;
  severity: Severity | "all";
  kind: string;
  order: Order;
  query: string;
  agreed: boolean;
  hasModel: boolean;
  onSeverity: (value: Severity | "all") => void;
  onKind: (value: string) => void;
  onOrder: (value: Order) => void;
  onQuery: (value: string) => void;
  onAgreed: (value: boolean) => void;
}) {
  const simple = useSimple();
  const severities: Severity[] = ["critical", "major", "minor"];
  return (
    <div className="filters">
      <label>
        Ashpërsia
        <select value={severity} onChange={(e) => onSeverity(e.target.value as Severity | "all")}>
          <option value="all">të gjitha</option>
          {severities.map((level) => (
            <option key={level} value={level}>
              {simple ? severityName(level) : level}
            </option>
          ))}
        </select>
      </label>
      <label>
        Lloji
        <select value={kind} onChange={(e) => onKind(e.target.value)}>
          <option value="all">të gjitha</option>
          {Object.keys(analysis.summary.by_type).map((name) => (
            <option key={name} value={name}>
              {simple ? smellName(name) : name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Radhitur sipas
        <select value={order} onChange={(e) => onOrder(e.target.value as Order)}>
          {(Object.keys(ORDER_LABELS) as Order[]).map((name) => (
            <option key={name} value={name}>
              {simple ? ORDER_PLAIN[name] : ORDER_LABELS[name]}
            </option>
          ))}
        </select>
      </label>
      <label className="grow">
        Kërko
        <input
          type="search"
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder="klasë, metodë ose skedar"
        />
      </label>
      {hasModel && (
        <label
          className="only-agreed"
          title={
            simple
              ? "Vetëm vendet ku edhe rregullat, edhe modeli thonë se ka problem"
              : "Prerja e dy qasjeve — sinjali më i fortë i matur"
          }
        >
          <input
            type="checkbox"
            checked={agreed}
            aria-label="Vetëm ku pajtohen të dyja qasjet"
            onChange={(e) => onAgreed(e.target.checked)}
          />
          Vetëm ku pajtohen
        </label>
      )}
    </div>
  );
}
