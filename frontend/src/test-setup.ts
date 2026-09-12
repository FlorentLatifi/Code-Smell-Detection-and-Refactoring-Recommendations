// Çfarë i mungon `jsdom`-it dhe i duhet kodit që testohet.
//
// `ResizeObserver` nuk ekziston te jsdom, dhe kontejneri i Recharts-it e thërret
// sapo montohet: pa të, çdo test që rendit një grafik bie me një përjashtim të
// pakapur, dhe dështimi duket sikur vjen nga komponenti. Stubi nuk mat asgjë,
// sepse jsdom nuk ka paraqitje për të matur — grafikët e deklarojnë përmbajtjen
// me `aria-label`, dhe testet lexojnë atë e jo pikselë.

class NoopResizeObserver implements ResizeObserver {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

if (!("ResizeObserver" in globalThis)) {
  globalThis.ResizeObserver = NoopResizeObserver;
}
