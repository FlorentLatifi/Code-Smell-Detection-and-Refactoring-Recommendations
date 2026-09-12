// @vitest-environment jsdom
//
// Aksesueshmëria e kontrolluar nga një mjet, jo nga kujdesi im.
//
// Auditimi i VD-85 i gjeti gabimet duke i lexuar: mungesa e landmark-ut, emri i
// listës, kontrasti nën kufirin. Kjo funksionon një herë. Rregullat e axe-core-it
// i kontrollojnë të njëjtat gjëra në çdo ekzekutim, ndaj një regres nuk pret që
// dikush ta shohë.
//
// **Çfarë mbulon dhe çfarë jo.** axe mbi jsdom kontrollon strukturën: role,
// emërtime, atribute, hierarkinë e titujve. Nuk kontrollon kontrastin, sepse
// jsdom nuk llogarit ngjyra të trashëguara, dhe një mjet që pretendon më shumë se
// sa mat është më keq se asnjë mjet. Kontrasti matet te `e2e/a11y.spec.ts`, mbi
// Chromium, ku ngjyrat e llogaritura ekzistojnë vërtet (VD-108).

import axe from "axe-core";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import type { Analysis } from "./types";

/** Vetëm shkeljet; çdo gjë tjetër te raporti i axe-it është informacion. */
async function violations(container: HTMLElement): Promise<string[]> {
  const result = await axe.run(container, {
    // Rregullat që kërkojnë një faqe të plotë nuk kanë kuptim mbi një fragment,
    // dhe ato që kërkojnë ngjyra të llogaritura nuk maten dot mbi jsdom.
    rules: {
      "color-contrast": { enabled: false },
      region: { enabled: false },
    },
  });
  return result.violations.map((v) => `${v.id}: ${v.nodes.length} — ${v.help}`);
}

const sample: Analysis = {
  summary: {
    files: 1,
    classes: 1,
    methods: 2,
    smells: 2,
    by_severity: { critical: 1, minor: 1 },
    by_type: { LongMethod: 1, DataClass: 1 },
  },
  smells: [
    {
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
    },
    {
      smell_type: "DataClass",
      scope: "class",
      class_name: "Row",
      method: null,
      package: "com.acme",
      file_path: "com/acme/Row.java",
      start_line: 3,
      end_line: 40,
      severity: "minor",
      score: 1.2,
      rationale: "WOC = 0.1 (< 0.33)",
      conditions: [{ metric: "WOC", operator: "<", threshold: 0.33, value: 0.1 }],
      refactorings: ["EncapsulateField"],
      metrics: { WOC: 0.1 },
      automated: false,
    },
  ],
};

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  window.localStorage.clear();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (String(url).endsWith("/analyze")) {
        return new Response(JSON.stringify(sample), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response(JSON.stringify({ start_line: 10, end_line: 12, truncated: false, lines: ["a"] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("axe", () => {
  it("nuk gjen shkelje te ekrani i parë", async () => {
    const { container } = render(<App />);

    expect(await violations(container)).toEqual([]);
  });

  it("nuk gjen shkelje te lista me gjetje", async () => {
    const { container } = render(<App />);
    fireEvent.change(screen.getByLabelText("Shtegu i projektit"), { target: { value: "src" } });
    fireEvent.click(screen.getByRole("button", { name: "Analizo" }));
    await screen.findAllByRole("button", { name: /^Ledger\.post/ });

    expect(await violations(container)).toEqual([]);
  });

  it("nuk gjen shkelje te paneli i një gjetjeje", async () => {
    const { container } = render(<App />);
    fireEvent.change(screen.getByLabelText("Shtegu i projektit"), { target: { value: "src" } });
    fireEvent.click(screen.getByRole("button", { name: "Analizo" }));
    const rows = await screen.findAllByRole("button", { name: /^Ledger\.post/ });
    fireEvent.click(rows[0]);
    await screen.findByRole("heading", { name: "LongMethod" });

    expect(await violations(container)).toEqual([]);
  });

  it("nuk gjen shkelje te paneli i rezultateve", async () => {
    const { container } = render(<App />);
    fireEvent.click(screen.getByRole("tab", { name: /Rezultatet/ }));
    await screen.findByRole("heading", { name: /Qasja A kundrejt Qasjes B/ });

    expect(await violations(container)).toEqual([]);
  });

  it("nuk gjen shkelje te gjendja e gabimit", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ error: { code: "path_not_found", message: "x" } }), {
            status: 400,
            headers: { "Content-Type": "application/json" },
          }),
      ),
    );
    const { container } = render(<App />);
    fireEvent.change(screen.getByLabelText("Shtegu i projektit"), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: "Analizo" }));
    await screen.findByRole("alert");

    expect(await violations(container)).toEqual([]);
  });
});
