// Si ndahen gjetjet, në të dy drejtimet që një lexues i kërkon menjëherë.
//
// Shiriti përmbledhës i jep totalet dhe lista i jep rreshtat, dhe mes tyre
// mungonte forma: cila erë dominon, dhe sa rëndë. Ato dy shifra ishin te
// përgjigjja që në fillim — `by_type` dhe `by_severity` — dhe nuk shiheshin
// askund veç si distinktivë të shpërndarë nëpër rreshta.
//
// Të njëjtat primitive si te skeda e vlerësimit, e jo një bibliotekë grafikësh:
// një shirit horizontal me përqindjen pranë lexohet njësoj si ato, dhe nuk shton
// asnjë varësi për të vizatuar katër rreshta.

import { Distribution, Panel } from "./Panels";
import type { Summary } from "./types";

/** Ashpërsitë në radhën e tyre, që një erë e rëndë të mos dalë poshtë një të lehtë. */
const SEVERITY_ORDER = ["critical", "major", "minor"];

export function Breakdown({ summary }: { summary: Summary }) {
  const types = Object.keys(summary.by_type).length;
  if (summary.smells === 0 || types === 0) return null;

  return (
    <div className="distributions">
      <Panel
        title="Sipas llojit"
        note={`${types} ${types === 1 ? "lloj ere" : "lloje erërash"} në ${summary.smells.toLocaleString("sq")} gjetje.`}
      >
        <Distribution counts={summary.by_type} labels={{}} total={summary.smells} />
      </Panel>

      <Panel title="Sipas ashpërsisë" note="Ashpërsia derivohet nga teprica mbi pragun.">
        <Distribution
          counts={summary.by_severity}
          labels={{}}
          total={summary.smells}
          order={SEVERITY_ORDER}
          tone="severe"
        />
      </Panel>
    </div>
  );
}
