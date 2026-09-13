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

// `window.scrollTo` te jsdom nuk lëviz asgjë dhe ankohet me një rresht gabimi për
// çdo thirrje. Aplikacioni e thërret sa herë ndërrohet pamja, ndaj dalja e testeve
// mbushej me zhurmë që nuk tregon asnjë defekt.
//
// Kushti nuk është dekor: skedarët që nuk prekin DOM-in ekzekutohen te mjedisi
// `node`, ku `window` nuk ekziston fare, dhe një caktim i pakushtëzuar i rrëzon
// të pesë ata para se të nisë testi i parë.
if (typeof window !== "undefined") {
  window.scrollTo = () => {};
}

// `scrollIntoView` nuk ekziston fare te jsdom. Aplikacioni e thërret kur hap një
// vend nga paneli ose një skedar nga tabela, dhe pa këtë thirrja do të hidhte një
// përjashtim brenda `requestAnimationFrame`, larg testit që e shkaktoi.
if (typeof Element !== "undefined" && !Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}
