// Pritja, si skicë e panelit që po vjen.
//
// `/analyze` kthen një përgjigje të vetme dhe nuk raporton përparim, ndaj këtu nuk
// ka shirit që pretendon një përqindje. Ka dy gjëra të vërteta për të treguar:
// forma e asaj që vjen, dhe sa kohë ka kaluar. Mbi `apache/ambari` pritja zgjat
// rreth njëzet sekonda, dhe një rresht teksti mbi një faqe bosh dukej si ngecje
// (VD-111).

import { useEffect, useState } from "react";

export function Loading() {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const started = performance.now();
    const timer = window.setInterval(
      () => setSeconds(Math.floor((performance.now() - started) / 1000)),
      1000,
    );
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="space-y-4">
      <p className="flex items-center gap-2 text-sm text-ink-600 dark:text-ink-300">
        <span
          className="h-2 w-2 rounded-full bg-brand-500 motion-safe:animate-pulse"
          aria-hidden="true"
        />
        {/* Vetëm teksti i palëvizshëm është `status`. Sekondat ndryshojnë çdo
            sekondë, dhe një lexues ekrani do t'i lexonte të gjitha. */}
        <span role="status">Duke matur skedarët…</span>
        {seconds > 0 && (
          <span className="tabular-nums text-ink-600 dark:text-ink-400" aria-hidden="true">
            {seconds} s
          </span>
        )}
      </p>
      <div className="grid gap-4 lg:grid-cols-4" aria-hidden="true">
        {[0, 1, 2, 3].map((index) => (
          <Block key={index} className="h-[120px]" />
        ))}
        <Block className="h-[260px] lg:col-span-2" />
        <Block className="h-[260px] lg:col-span-2" />
      </div>
    </div>
  );
}

function Block({ className }: { className: string }) {
  return (
    <div
      className={`rounded-xl border border-ink-200 bg-white motion-safe:animate-pulse dark:border-ink-800 dark:bg-ink-900 ${className}`}
    />
  );
}
