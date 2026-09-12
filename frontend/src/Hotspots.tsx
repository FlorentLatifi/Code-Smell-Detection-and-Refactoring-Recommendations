import { hotspots } from "./sites";
import type { Site } from "./sites";

/**
 * Ku përqendrohet puna, aty ku më parë rrinte një fjali që nuk thoshte asgjë.
 *
 * Paneli i djathtë ishte bosh derisa zgjidhej diçka, dhe ai bosh zinte gjysmën e
 * ekranit. Ndarja e vendeve nëpër skedarë nuk është e barabartë — mbi projektin e
 * provës një skedar i vetëm mban gati një të tretën — ndaj kjo është pikërisht
 * pyetja që një lexues ka para se të klikojë kudo: nga t'ia nis.
 *
 * Klikimi shkruan te kërkimi, i cili tashmë filtron edhe mbi shtegun. Asnjë
 * dimension i ri filtrimi nuk u shtua për këtë.
 */
export function Hotspots({ sites, onPick }: { sites: Site[]; onPick: (file: string) => void }) {
  const top = hotspots(sites);
  if (top.length === 0) return null;
  const most = top[0].sites;

  return (
    <div className="hotspots">
      <h2>Ku përqendrohet</h2>
      <p className="caption">
        {sites.length} vende në {new Set(sites.map((s) => s.file_path)).size} skedarë. Kliko një
        skedar për ta parë vetëm atë.
      </p>
      <ul>
        {top.map((spot) => (
          <li key={spot.file}>
            <button className="spot" onClick={() => onPick(spot.file)}>
              <span className="name">{spot.file.split(/[\/]/).pop()}</span>
              <span className="track" aria-hidden="true">
                <span className="fill" style={{ width: `${(spot.sites / most) * 100}%` }} />
              </span>
              <span className="tally">
                {spot.sites} {spot.sites === 1 ? "vend" : "vende"}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
