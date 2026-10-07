// Çfarë e mbush panelin e djathtë para se të zgjidhet një vend.
//
// Aty rrinte tabela e skedarëve më të ndotur, e cila tani ka vendin e vet te
// paneli majtas. Dy panele që i përgjigjen pyetjes «nga t'ia nis» janë një
// panel më shumë se sa ka pyetje.
//
// Zëvendësimi nuk është një fjali që thotë «zgjidh diçka»: paneli zë gjysmën e
// ekranit, dhe gjysma e ekranit duhet të thotë diçka. Kjo listë thotë çfarë
// merret me atë klikim, e cila është pikërisht ajo që dikush nuk e di ende.

import { useSimple } from "./mode";

export function Waiting() {
  const simple = useSimple();
  if (simple) {
    return (
      <div className="waiting">
        <h2>Zgjidh një vend nga lista</h2>
        <p className="caption">Për çdo vend, këtu do të shohësh:</p>
        <ul>
          <li>
            <b>Çfarë problemi ka</b>, me fjalë të thjeshta, dhe pse ka rëndësi.
          </li>
          <li>
            <b>Kodin</b> ku u gjet problemi.
          </li>
          <li>
            <b>Pse u shënua</b>: cila matje e kaloi kufirin dhe me sa.
          </li>
          <li>
            <b>Si mund të ndreqet</b>, hap pas hapi.
          </li>
          <li>
            <b>Ndreqjen e gatshme</b>, kur mjeti mund ta bëjë vetë, para se të prekë ndonjë skedar.
          </li>
        </ul>
      </div>
    );
  }
  return (
    <div className="waiting">
      <h2>Zgjidh një vend</h2>
      <p className="caption">
        Çdo gjetje hapet këtu e plotë. Asgjë nuk pohohet pa u treguar nga vjen.
      </p>
      <ul>
        <li>
          <b>Kodi</b> pikërisht i rreshtave që u matën, jo një fragment i afërt.
        </li>
        <li>
          <b>Klauzolat</b> që ndezën, me të maturën përballë pragut dhe tepricën mes tyre.
        </li>
        <li>
          <b>Metrikat</b> e entitetit, të gjitha, edhe ato që nuk hyjnë te asnjë klauzolë.
        </li>
        <li>
          <b>Verdikti i modelit</b> për të njëjtin entitet, kur ai u pyet, me matjen vendimtare.
        </li>
        <li>
          <b>Diff-i</b> i rishkrimit, kur motori e provon dot, para se të prekë gjë.
        </li>
      </ul>
    </div>
  );
}
