// Rekomandimet që motori di t'i kryejë vetë, të veçuara nga lista e plotë.
//
// Lista i tregon të gjitha gjetjet dhe e shënon me një distinktiv të vogël atë
// që rishkruhet automatikisht. Kjo është e saktë dhe e fshehur: dallimi mes
// «ja çfarë gjeta» dhe «ja çfarë mund të ndreq» është pikërisht ai që dikush
// kërkon i pari, dhe ai rrinte si një shenjë tetë pikëshe mes pesëdhjetë
// rreshtash.
//
// Kartat nuk e dyfishojnë listën: klikimi e zgjedh të njëjtin vend që do të
// zgjidhte rreshti, dhe diff-i hapet aty ku hapet gjithnjë. Një rrugë e dytë
// drejt të njëjtit panel do të ishte një panel i dytë për t'u mbajtur.

import type { Site } from "./sites";
import type { Smell } from "./types";

/**
 * Sa karta shfaqen.
 *
 * Pesë, sepse kjo është listë për të nisur punën e jo për ta inventarizuar: mbi
 * një projekt real numri i vendeve të rishkrueshme shkon me qindra, dhe një
 * listë e tillë do të ishte lista e plotë me një emër tjetër.
 */
const SHOWN = 5;

export function Recommendations({
  sites,
  onChoose,
}: {
  sites: Site[];
  onChoose: (site: Site, smell: Smell) => void;
}) {
  const actionable = sites.filter((site) => site.automated);
  if (actionable.length === 0) return null;

  const shown = actionable.slice(0, SHOWN);
  return (
    <section className="recommendations" aria-label="Rekomandimet e refaktorimit">
      <h2>Rekomandimet e refaktorimit</h2>
      <p className="caption">
        {actionable.length === 1
          ? "Një vend që motori e rishkruan vetë"
          : `${actionable.length} vende që motori i rishkruan vetë`}
        , më e rënda e para. Çdo rishkrim shfaqet si diff para se të prekë gjë.
      </p>

      <ol className="suggestions">
        {shown.map((site) => (
          <Suggestion key={site.key} site={site} onChoose={onChoose} />
        ))}
      </ol>

      {actionable.length > shown.length && (
        <p className="caption">
          Edhe {actionable.length - shown.length} të tjera te lista poshtë, me shenjën ✎.
        </p>
      )}
    </section>
  );
}

function Suggestion({
  site,
  onChoose,
}: {
  site: Site;
  onChoose: (site: Site, smell: Smell) => void;
}) {
  // Era e automatizuar e këtij vendi, e jo thjesht e para: një metodë e gjatë
  // dhe e folezuar mban të dyja, dhe vetëm njëra prej tyre ka rishkrim.
  const smell = site.smells.find((s) => s.automated);
  if (!smell) return null;

  return (
    <li className={`suggestion ${site.worst}`}>
      <div className="what">
        <h3>
          {smell.refactorings[0]} te <code>{label(site)}</code>
        </h3>
        <p className="why">
          {smell.smell_type}: {smell.rationale}
        </p>
        <p className="file">
          {site.file_path}:{site.start_line}
        </p>
      </div>
      <button onClick={() => onChoose(site, smell)}>Shfaq ndryshimin</button>
    </li>
  );
}

/** Klasa dhe metoda, pa nënshkrimin që e bën rreshtin dy herë më të gjatë. */
function label(site: Site): string {
  const method = site.method ? `.${site.method.replace(/\(.*$/, "")}` : "";
  return `${site.class_name}${method}`;
}
