// @vitest-environment jsdom
//
// Testet e renderimit, të ndara nga ato të logjikës së pastër.
//
// Deri tani testet mbulonin funksione — diff-in, grupimin, bashkimin e dy
// qasjeve — dhe asnjë nga rrugët që një përdorues i prek vërtet. Kjo do të thoshte
// se çdo defekt i gjetur nga auditimi ishte i kapshëm vetëm duke e hapur mjetin
// me dorë, dhe asnjëri prej tyre nuk kishte test që ta ndalonte kthimin.
//
// Prandaj secili test këtu i përgjigjet një defekti të vërtetë të VD-85 dhe VD-86,
// jo një rruge të zgjedhur për mbulim. Emri i testit e thotë cilit.
//
// Mjedisi është `jsdom`, i deklaruar te rreshti i parë e jo te konfigurimi, që
// testet e logjikës të mbeten mbi `node` dhe të shpejta.

import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import type { Analysis, Smell } from "./types";

/** Emri i arritshëm i një rreshti nis me klasën dhe metodën; hotspot-i me skedarin. */
const ROW = /^Ledger\.m\d/;

function smell(overrides: Partial<Smell> = {}): Smell {
  return {
    smell_type: "LongMethod",
    scope: "method",
    class_name: "Ledger",
    method: "post(int)",
    package: "com.acme",
    file_path: "com/acme/Ledger.java",
    start_line: 10,
    end_line: 60,
    severity: "critical",
    score: 2.5,
    rationale: "MLOC = 50 (> 30)",
    conditions: [{ metric: "MLOC", operator: ">", threshold: 30, value: 50 }],
    refactorings: ["ExtractMethod"],
    metrics: { MLOC: 50 },
    automated: true,
    ...overrides,
  };
}

function counted(values: string[]): Record<string, number> {
  const tally: Record<string, number> = {};
  for (const value of values) tally[value] = (tally[value] ?? 0) + 1;
  return tally;
}

/** Përmbledhja derivohet nga vetë erërat, që fikstuara të mos bjerë ndesh me vetveten. */
function analysis(smells: Smell[]): Analysis {
  return {
    summary: {
      files: 1,
      classes: 1,
      methods: smells.length,
      smells: smells.length,
      by_severity: counted(smells.map((s) => s.severity)),
      by_type: counted(smells.map((s) => s.smell_type)),
    },
    smells,
  };
}

/** Sa vende do të prodhonte një analizë me `count` metoda të ndryshme. */
function many(count: number): Analysis {
  return analysis(
    Array.from({ length: count }, (_, i) =>
      smell({ method: `m${i}(int)`, start_line: 10 + i * 100 }),
    ),
  );
}

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  window.localStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

/** Përgjigje e vetme për `/analyze`; çdo rrugë tjetër dështon si e paparashikuar. */
function serve(body: Analysis): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (String(url).endsWith("/analyze")) {
        return new Response(JSON.stringify(body), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response(JSON.stringify({ error: { code: "not_found", message: "x" } }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
}

async function analyse(path = "src"): Promise<void> {
  fireEvent.change(screen.getByLabelText("Shtegu i projektit"), { target: { value: path } });
  fireEvent.click(screen.getByRole("button", { name: "Analizo" }));
  // `findByRole` kërkon një të vetëm dhe dështon mbi dyqind rreshta.
  await screen.findAllByRole("button", { name: ROW });
}

describe("gjendjet e ekranit", () => {
  it("hapet me një ftesë, jo me një listë bosh", () => {
    render(<App />);

    expect(screen.getByText(/Shkruaj shtegun e një projekti/)).toBeDefined();
  });

  it("e ndalon analizën derisa të ketë një shteg", () => {
    render(<App />);

    expect(screen.getByRole("button", { name: "Analizo" }).hasAttribute("disabled")).toBe(true);
  });

  it("e përkthen gabimin e serverit në shqip", async () => {
    // VD-85: «the path does not exist» dilte anglisht mes tekstit shqip.
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({ error: { code: "path_not_found", message: "the path does not exist" } }),
            { status: 400, headers: { "Content-Type": "application/json" } },
          ),
      ),
    );
    render(<App />);
    fireEvent.change(screen.getByLabelText("Shtegu i projektit"), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: "Analizo" }));

    const alert = await screen.findByRole("alert");

    expect(alert.textContent).toContain("Nuk ka asgjë te ky shteg");
    expect(alert.textContent).not.toContain("does not exist");
  });
});

describe("lista", () => {
  it("pret te dyqind rreshta dhe e thotë sa mbeten", async () => {
    // VD-86: 4 249 rreshta te DOM-i bënin 146 ms bllokim për çdo shkronjë.
    serve(many(250));
    render(<App />);
    await analyse();

    expect(screen.getAllByRole("button", { name: ROW })).toHaveLength(200);
    expect(screen.getByText(/Shfaq 50 të tjera/)).toBeDefined();
  });

  // Afat i shkruar shprehimisht, e jo pesë sekondat e parazgjedhura. Testi
  // ndërton 450 vende dhe pastaj rendit 400 rreshta te DOM-i: u mat rreth 7
  // sekonda mbi këtë makinë, ndaj parazgjedhja e bën kalimin të varet nga sa e
  // ngarkuar është makina në atë çast. Pohimi mbetet i njëjti; largohet vetëm
  // varësia nga shpejtësia (VD-98).
  it(
    "shton dyqind të tjera kur kërkohet",
    async () => {
      serve(many(450));
      render(<App />);
      await analyse();

      fireEvent.click(screen.getByRole("button", { name: /Shfaq 200 të tjera/ }));

      expect(screen.getAllByRole("button", { name: ROW })).toHaveLength(400);
    },
    30_000,
  );

  it("e mban numërimin mbi tërë listën, jo mbi dritaren", async () => {
    // Numri që lexohet duhet të mbetet emëruesi i vërtetë, ndryshe prerja fsheh
    // punë në vend që ta shtyjë.
    serve(many(250));
    render(<App />);
    await analyse();

    // I njëjti varg del edhe te shiriti i patch-it, ndaj kërkohet brenda listës.
    const list = screen.getByRole("region", { name: "Vendet e gjetura" });

    expect(within(list).getByText(/250 nga 250 vende/)).toBeDefined();
  });

  it("ofron dalje kur filtri nuk përputh asgjë", async () => {
    serve(many(3));
    render(<App />);
    await analyse();

    fireEvent.change(screen.getByPlaceholderText("klasë, metodë ose skedar"), {
      target: { value: "asgjenukperputhet" },
    });

    expect(screen.getByText(/Asnjë vend nuk i plotëson filtrat/)).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Pastro filtrat" }));
    expect(screen.getAllByRole("button", { name: ROW })).toHaveLength(3);
  });
});

describe("tastiera", () => {
  it("i lë shigjetat te filtrat, ku ato u përkasin", async () => {
    // VD-85: trajtuesi i listës i rrëmbente, dhe filtri i ashpërsisë nuk
    // ndryshohej dot fare me tastierë.
    serve(many(5));
    render(<App />);
    await analyse();

    const severity = screen.getByLabelText(/Ashpërsia/);
    const handled = fireEvent.keyDown(severity, { key: "ArrowDown" });

    // `fireEvent` kthen false kur ngjarja u anulua.
    expect(handled).toBe(true);
  });

  it("i përdor shigjetat mbi një rresht për të lëvizur përzgjedhjen", async () => {
    serve(many(5));
    render(<App />);
    await analyse();

    const rows = screen.getAllByRole("button", { name: ROW });
    const handled = fireEvent.keyDown(rows[0], { key: "ArrowDown" });

    expect(handled).toBe(false);
  });
});

describe("skedat", () => {
  it("i deklaron si skeda, jo si butona të shtypur", () => {
    render(<App />);

    const tabs = screen.getAllByRole("tab");

    expect(tabs).toHaveLength(2);
    expect(tabs[0].getAttribute("aria-selected")).toBe("true");
    expect(tabs[1].getAttribute("aria-selected")).toBe("false");
  });

  it("kalon mes tyre me shigjetat", () => {
    render(<App />);

    fireEvent.keyDown(screen.getByRole("tab", { name: /Analizo një projekt/ }), {
      key: "ArrowRight",
    });

    expect(screen.getByRole("tab", { name: /Rezultatet/ }).getAttribute("aria-selected")).toBe(
      "true",
    );
  });
});

describe("adresa", () => {
  it("e mban shtegun, që një link të hapë atë që premton", async () => {
    serve(many(2));
    render(<App />);
    await analyse("src/main");

    expect(window.location.search).toContain("path=src%2Fmain");
  });

  it("e lexon shtegun nga adresa në ngarkim", () => {
    window.history.replaceState(null, "", "/?path=nga%2Fadresa");

    render(<App />);

    expect((screen.getByLabelText("Shtegu i projektit") as HTMLInputElement).value).toBe(
      "nga/adresa",
    );
  });
});

describe("struktura e faqes", () => {
  it("ka një landmark kryesor dhe një lidhje që e kapërcen kokën", () => {
    render(<App />);

    expect(screen.getByRole("main")).toBeDefined();
    expect(screen.getByRole("link", { name: /Kalo te përmbajtja/ })).toBeDefined();
  });

  it("i jep listës emër, që të mos jetë një rajon pa identitet", async () => {
    serve(many(2));
    render(<App />);
    await analyse();

    const list = screen.getByRole("region", { name: "Vendet e gjetura" });

    expect(within(list).getAllByRole("button", { name: ROW })).toHaveLength(2);
  });
});

describe("gjetjet që i shënoi vetëm modeli", () => {
  /** Analizë me një erë rregulli dhe një verdikt modeli mbi një entitet tjetër. */
  function withModel(): Analysis {
    return {
      ...analysis([smell({ method: "m0(int)" })]),
      model: {
        available: true,
        smells: [
          {
            smell: "data class",
            rule_equivalent: ["DataClass"],
            considered: 2,
            incomplete: 0,
            flagged: 2,
            predictions: [
              {
                smell: "data class",
                file_path: "com/acme/Ledger.java",
                class_name: "Ledger",
                method: "post",
                start_line: 10,
                end_line: 60,
                probability: 0.8,
                contributions: [],
              },
              {
                smell: "data class",
                file_path: "com/acme/Basket.java",
                class_name: "Basket",
                method: null,
                start_line: 4,
                end_line: 30,
                probability: 0.93,
                contributions: [
                  { feature: "c_WOC", value: 0, typical: 0.6, drop: 0.5, decisive: true },
                ],
              },
            ],
          },
        ],
      },
    };
  }

  it("shfaq entitetin që asnjë rregull nuk e gjeti", async () => {
    // `Ledger` është te lista sepse një rregull e gjeti; `Basket` nuk ishte
    // askund, ndonëse kutiza e Qasjes B e numëronte (VD-93).
    serve(withModel());
    render(<App />);
    await analyse();

    const section = screen.getByRole("region", { name: "Gjetjet vetëm të modelit" });

    expect(within(section).getByText("Basket")).toBeDefined();
    expect(within(section).queryByText("Ledger")).toBeNull();
  });

  it("jep gjasën dhe matjen vendimtare, jo vetëm emrin", async () => {
    serve(withModel());
    render(<App />);
    await analyse();

    const section = screen.getByRole("region", { name: "Gjetjet vetëm të modelit" });

    expect(within(section).getByText("93%")).toBeDefined();
    expect(within(section).getByText("c_WOC = 0")).toBeDefined();
  });

  it("nuk shfaqet fare kur modeli nuk u pyet", async () => {
    serve(analysis([smell({ method: "m0(int)" })]));
    render(<App />);
    await analyse();

    expect(screen.queryByRole("region", { name: "Gjetjet vetëm të modelit" })).toBeNull();
  });
});

describe("skedarët që nuk parsohen dhe dosja e lejuar", () => {
  it("paralajmëron kur një skedar nuk u parsua pastër", async () => {
    // Tree-sitter-i kthen pemë edhe për një skedar të prishur, ndaj heshtja
    // do të lexohej si kod i pastër (VD-91).
    const body = analysis([smell({ method: "m0(int)" })]);
    serve({ ...body, summary: { ...body.summary, files: 4, unparsed: 2 } });
    render(<App />);
    await analyse();

    expect(screen.getByText(/nuk u parsua pastër/)).toBeDefined();
    expect(screen.getByText(/2 nga 4/)).toBeDefined();
  });

  it("hesht kur çdo skedar u parsua", async () => {
    const body = analysis([smell({ method: "m0(int)" })]);
    serve({ ...body, summary: { ...body.summary, unparsed: 0 } });
    render(<App />);
    await analyse();

    expect(screen.queryByText(/nuk u parsua pastër/)).toBeNull();
  });

  it("nuk paralajmëron kur serveri nuk e dërgon fare shifrën", async () => {
    // Mungesa lexohet si «nuk dihet», jo si zero.
    serve(analysis([smell({ method: "m0(int)" })]));
    render(<App />);
    await analyse();

    expect(screen.queryByText(/nuk u parsua pastër/)).toBeNull();
  });
});

describe("progresi i patch-it", () => {
  /** Një rrjedhë NDJSON e dorëzuar copë-copë, si te rrjeti. */
  function streamedPatch(lines: string[]): Response {
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        const encoder = new TextEncoder();
        for (const line of lines) controller.enqueue(encoder.encode(line));
        controller.close();
      },
    });
    return new Response(body, {
      status: 200,
      headers: { "Content-Type": "application/x-ndjson" },
    });
  }

  it("tregon sa skedarë kanë mbaruar ndërsa pret", async () => {
    // Deri tani e gjithë pritja dukej njësoj si një mjet i ngecur (VD-98).
    const body = analysis([smell({ method: "m0(int)" })]);
    // Mbahet e hapur derisa ekrani të jetë te gjendja «duke përgatitur», që
    // testi ta shohë shiritin e jo vetëm rezultatin.
    let release = () => {};
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });

    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (String(url).endsWith("/analyze")) {
          return new Response(JSON.stringify(body), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        if (String(url).endsWith("/refactor/patch/stream")) {
          await held;
          return streamedPatch(['{"progress":{"files_done":3,"files_total":8,"changes":1}}\n']);
        }
        return new Response("{}", { status: 404 });
      }),
    );

    render(<App />);
    await analyse();
    fireEvent.click(screen.getByRole("button", { name: "Përgatit patch-in" }));
    release();

    // Teksti ndahet në disa nyje nga interpolimi, ndaj lexohet i tëri.
    const status = await screen.findByText(/3 nga 8 skedarë/);

    expect(status.textContent).toContain("(38%)");
    expect(status.textContent).toContain("1 ndryshim deri tani");
  });
});

describe("shpërndarja e gjetjeve", () => {
  it("tregon llojet si unazë me legjendë të numëruar", async () => {
    // Ngjyra e vetme si çelës do të detyronte lexuesin të kalonte sytë mes dy
    // vendeve, dhe dikush që nuk i dallon ngjyrat nuk do ta lexonte fare.
    serve(
      analysis([
        smell({ method: "m0(int)" }),
        smell({ method: "m1(int)", start_line: 200, smell_type: "DeepNesting", severity: "minor" }),
      ]),
    );
    render(<App />);
    await analyse();

    const overview = screen.getByRole("region", { name: "Përmbledhja" });
    const legend = within(overview).getByRole("list");

    expect(within(legend).getByText("LongMethod")).toBeDefined();
    expect(within(legend).getByText("DeepNesting")).toBeDefined();
    // Unaza vetë është pamje, ndaj e përshkruan veten për një lexues ekrani.
    expect(within(overview).getByRole("img").getAttribute("aria-label")).toContain("2 erëra");
  });

  it("rendit ashpërsitë nga më e rënda, jo nga më e shpeshta", async () => {
    // Dy kritike duhet të rrinë majtas njëzet të lehtave.
    const smells = [
      smell({ method: "m0(int)", severity: "critical" }),
      ...Array.from({ length: 3 }, (_, i) =>
        smell({ method: `m${i + 1}(int)`, start_line: 200 + i * 50, severity: "minor" }),
      ),
    ];
    serve(analysis(smells));
    render(<App />);
    await analyse();

    const panel = screen.getByRole("region", { name: "Sipas ashpërsisë" });
    const chart = within(panel).getByRole("img");

    expect(chart.getAttribute("aria-label")).toBe("critical 1, major 0, minor 3");
  });

  it("numëron vendet, jo erërat, që shuma të barazojë listën", async () => {
    // I njëjti vend mban dy erëra: një vend kritik, e jo dy gjetje.
    serve(
      analysis([
        smell({ method: "m0(int)", severity: "critical" }),
        smell({ method: "m0(int)", smell_type: "DeepNesting", severity: "minor" }),
      ]),
    );
    render(<App />);
    await analyse();

    const panel = screen.getByRole("region", { name: "Sipas ashpërsisë" });

    expect(within(panel).getByRole("img").getAttribute("aria-label")).toBe(
      "critical 1, major 0, minor 0",
    );
  });

  it("nuk shfaqet kur nuk u gjet asnjë erë", async () => {
    serve(analysis([]));
    render(<App />);
    fireEvent.change(screen.getByLabelText("Shtegu i projektit"), { target: { value: "src" } });
    fireEvent.click(screen.getByRole("button", { name: "Analizo" }));

    expect(await screen.findByText(/Asnjë erë e detektuar/)).toBeDefined();
    expect(screen.queryByRole("region", { name: "Përmbledhja" })).toBeNull();
  });
});

describe("aplikimi mbi skedarët", () => {
  const PATCH = {
    diff: "--- a/x\n+++ b/x\n",
    files: 2,
    changes: 3,
    declined: 0,
    declines: [],
    deferred: 0,
    unreached: 0,
    verified_with_javac: true,
    dropped: [],
    applied: [],
  };

  /** Serven analizën, patch-in si rrjedhë, dhe përgjigjet e shkrimit. */
  function serveApply(tree: unknown, apply?: { status: number; body: unknown }) {
    const body = analysis([smell({ method: "m0(int)" })]);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        const target = String(url);
        if (target.endsWith("/analyze")) return json(body);
        if (target.endsWith("/refactor/tree")) return json(tree);
        if (target.endsWith("/refactor/apply")) {
          return new Response(JSON.stringify(apply?.body ?? {}), {
            status: apply?.status ?? 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        if (target.endsWith("/refactor/patch/stream")) {
          return new Response(
            new ReadableStream<Uint8Array>({
              start(controller) {
                controller.enqueue(
                  new TextEncoder().encode(`{"result":${JSON.stringify(PATCH)}}\n`),
                );
                controller.close();
              },
            }),
            { status: 200, headers: { "Content-Type": "application/x-ndjson" } },
          );
        }
        return new Response("{}", { status: 404 });
      }),
    );
  }

  function json(value: unknown): Response {
    return new Response(JSON.stringify(value), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  async function preparePatch(): Promise<void> {
    render(<App />);
    await analyse();
    fireEvent.click(screen.getByRole("button", { name: "Përgatit patch-in" }));
    await screen.findByRole("button", { name: "Kopjo patch-in" });
  }

  it("nuk e ofron shkrimin kur pema nuk është e pastër", async () => {
    // Pa depo git nuk ka kthim, dhe motori nuk shkruan pa një të tillë.
    serveApply({ writable: false, reason: "tree_not_clean", detail: "2 file(s)" });
    await preparePatch();

    expect(await screen.findByText(/ndryshime të paruajtura/)).toBeDefined();
    expect(screen.queryByRole("button", { name: "Apliko te skedarët" })).toBeNull();
  });

  it("kërkon një hap të dytë para se të shkruajë", async () => {
    // Veprimi i vetëm që e ndryshon kodin është i vetmi me dy hapa.
    serveApply({ writable: true, reason: null, detail: "" });
    await preparePatch();

    fireEvent.click(await screen.findByRole("button", { name: "Apliko te skedarët" }));

    expect(screen.getByText(/do të rishkruajë/)).toBeDefined();
    expect(screen.getByRole("button", { name: "Po, shkruaji" })).toBeDefined();
  });

  it("emërton skedarët e shkruar dhe komandën që i kthen", async () => {
    serveApply(
      { writable: true, reason: null, detail: "" },
      {
        status: 200,
        body: { written: ["A.java", "B.java"], revert: "git restore .", changes: 3, verified_with_javac: true },
      },
    );
    await preparePatch();

    fireEvent.click(await screen.findByRole("button", { name: "Apliko te skedarët" }));
    fireEvent.click(screen.getByRole("button", { name: "Po, shkruaji" }));

    expect(await screen.findByText(/2 skedarë u shkruan/)).toBeDefined();
    expect(screen.getByText("git restore .")).toBeDefined();
    expect(screen.getByText("A.java")).toBeDefined();
  });

  it("e thotë shqip kur serveri e refuzon shkrimin", async () => {
    serveApply(
      { writable: true, reason: null, detail: "" },
      { status: 409, body: { error: { code: "tree_not_clean", message: "tree_not_clean" } } },
    );
    await preparePatch();

    fireEvent.click(await screen.findByRole("button", { name: "Apliko te skedarët" }));
    fireEvent.click(screen.getByRole("button", { name: "Po, shkruaji" }));

    expect(await screen.findByRole("alert")).toBeDefined();
  });
});

describe("konteksti dhe rekomandimet", () => {
  it("thotë çfarë u lexua përpara se të thotë sa u gjet", async () => {
    // Dyzet erëra mbi treqind rreshta dhe dyzet mbi tridhjetë mijë janë dy
    // gjendje krejt të ndryshme, dhe emëruesi mungonte.
    const body = analysis([smell({ method: "m0(int)" })]);
    serve({ ...body, summary: { ...body.summary, loc: 1234 } });
    render(<App />);
    await analyse();

    const context = document.querySelector(".context");

    // Formatimi i numrit varet nga `Intl` e ambientit, ndaj kërkohet i njëjti
    // që prodhon komponenti e jo një varg i shtypur me dorë.
    expect(context?.textContent).toContain((1234).toLocaleString("sq"));
    expect(context?.textContent).toContain("rreshta kodi");
    expect(context?.textContent).toContain("vetëm rregullat");
  });

  it("hesht për rreshtat kur serveri nuk i dërgon", async () => {
    serve(analysis([smell({ method: "m0(int)" })]));
    render(<App />);
    await analyse();

    expect(document.querySelector(".context")?.textContent).not.toContain("rreshta kodi");
  });

  it("i veçon rekomandimet që motori i rishkruan vetë", async () => {
    // Dallimi mes «ja çfarë gjeta» dhe «ja çfarë mund të ndreq» rrinte si një
    // distinktiv tetë pikësh mes pesëdhjetë rreshtash.
    serve(
      analysis([
        smell({ method: "m0(int)", automated: true }),
        smell({ method: "m1(int)", start_line: 300, smell_type: "DataClass", automated: false }),
      ]),
    );
    render(<App />);
    await analyse();

    const panel = screen.getByRole("region", { name: "Rekomandimet e refaktorimit" });

    expect(within(panel).getAllByRole("listitem")).toHaveLength(1);
    expect(within(panel).getByText(/ExtractMethod/)).toBeDefined();
  });

  it("nuk shfaqet kur asgjë nuk rishkruhet vetë", async () => {
    serve(analysis([smell({ method: "m0(int)", automated: false, refactorings: [] })]));
    render(<App />);
    await analyse();

    expect(screen.queryByRole("region", { name: "Rekomandimet e refaktorimit" })).toBeNull();
  });

  it("hap erën që ka rishkrim, e jo më të rëndën e vendit", async () => {
    // Një metodë e gjatë dhe e folezuar mban të dyja, dhe vetëm njëra rishkruhet.
    const critical = smell({ method: "m0(int)", smell_type: "DataClass", automated: false });
    const fixable = smell({
      method: "m0(int)",
      smell_type: "DeepNesting",
      severity: "minor",
      automated: true,
      refactorings: ["ReplaceNestedConditionalWithGuardClauses"],
    });
    serve(analysis([critical, fixable]));
    render(<App />);
    await analyse();

    const panel = screen.getByRole("region", { name: "Rekomandimet e refaktorimit" });
    fireEvent.click(within(panel).getByRole("button", { name: "Shfaq ndryshimin" }));

    const detail = document.querySelector(".detail");

    expect(detail?.querySelector("h2")?.textContent).toBe("DeepNesting");
  });
});

describe("rreshti anësor", () => {
  it("e deklaron veten vertikal, që shigjetat e premtuara të jenë ato që punojnë", async () => {
    render(<App />);

    const rail = screen.getByRole("tablist", { name: "Pamjet" });

    expect(rail.getAttribute("aria-orientation")).toBe("vertical");
  });

  it("kalon mes pamjeve me shigjetën poshtë", async () => {
    render(<App />);
    const analysisTab = screen.getByRole("tab", { name: /Analizo një projekt/ });

    fireEvent.keyDown(analysisTab, { key: "ArrowDown" });

    expect(screen.getByRole("tab", { name: /Rezultatet/ }).getAttribute("aria-selected")).toBe(
      "true",
    );
  });
});

describe("paneli i djathtë para zgjedhjes", () => {
  it("thotë çfarë merret me klikimin, e jo vetëm «zgjidh diçka»", async () => {
    // Aty rrinte tabela e skedarëve, e cila tani ka vendin e vet majtas: dy
    // panele që i përgjigjen «nga t'ia nis» janë një më shumë se sa ka pyetje.
    serve(analysis([smell({ method: "m0(int)" })]));
    render(<App />);
    await analyse();

    expect(screen.getByText(/Klauzolat/)).toBeDefined();
    expect(screen.getByText(/Verdikti i modelit/)).toBeDefined();
  });

  it("ia lë vendin detajit sapo zgjidhet një gjetje", async () => {
    serve(analysis([smell({ method: "m0(int)" })]));
    render(<App />);
    await analyse();

    fireEvent.click(screen.getAllByRole("button", { name: ROW })[0]);

    expect(screen.queryByText(/Verdikti i modelit/)).toBeNull();
  });
});
