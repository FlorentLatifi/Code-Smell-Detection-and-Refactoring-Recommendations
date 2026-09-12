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

function analysis(smells: Smell[]): Analysis {
  return {
    summary: {
      files: 1,
      classes: 1,
      methods: smells.length,
      smells: smells.length,
      by_severity: { critical: smells.length },
      by_type: { LongMethod: smells.length },
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

  it("shton dyqind të tjera kur kërkohet", async () => {
    serve(many(450));
    render(<App />);
    await analyse();

    fireEvent.click(screen.getByRole("button", { name: /Shfaq 200 të tjera/ }));

    expect(screen.getAllByRole("button", { name: ROW })).toHaveLength(400);
  });

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
