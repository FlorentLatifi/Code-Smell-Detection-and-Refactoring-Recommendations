// A ka çdo gabim që serveri mund ta kthejë një fjali shqip?
//
// I njëjti defekt si te verdiktet e panelit: pa përkthim, mesazhi anglisht del
// mes tekstit shqip dhe duket i saktë, sepse asgjë nuk prishet. «the path does
// not exist» qëndroi ashtu derisa dikush e pa në ekran.
//
// Lista më poshtë është kopje me dorë e kodeve që prodhon backend-i. Ajo anë e ka
// testin e vet (`test_api_paths.py::REJECTION_CODES`), ndaj një kod i ri i thyen
// të dyja: atje sepse bashkësia nuk përputhet, këtu sepse përkthimi mungon.

import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ERROR_SQ,
  MODEL_REFUSAL_SQ,
  REFUSAL_DETAIL_SQ,
  explanationText,
  noteText,
  patch,
  within,
} from "./api";

// Serveri e jep `file_path` relativ ndaj dosjes së analizuar, ose ndaj dosjes së
// skedarit kur analizohet një skedar i vetëm (`_relative` te `api/app.py`). Çdo
// pritje më poshtë del nga ai rregull, jo nga dalja e funksionit (VD-120).
describe("shtegu i skedarit të një gjetjeje", () => {
  it("e ngjit te dosja e analizuar", () => {
    expect(within("jsoup", "src/main/Node.java")).toBe("jsoup/src/main/Node.java");
  });

  it("nuk dyfishon vijën kur dosja mbaron me të", () => {
    expect(within("jsoup/", "src/main/Node.java")).toBe("jsoup/src/main/Node.java");
  });

  it("e gjen skedarin e vetëm pa e ngjitur te vetja", () => {
    // Defekti: dilte `OrderManager.java/OrderManager.java`.
    expect(within("OrderManager.java", "OrderManager.java")).toBe("OrderManager.java");
  });

  it("ruan dosjen e skedarit të vetëm", () => {
    expect(within("demo/shop/OrderManager.java", "OrderManager.java")).toBe(
      "demo/shop/OrderManager.java",
    );
  });

  it("kthen shtegun e analizuar kur gjetja nuk ka skedar", () => {
    expect(within("jsoup/", "")).toBe("jsoup");
  });

  it("ngjit skedarin te një dosje që quhet si skedar Java", () => {
    // Defekti: pa `scope`, dosja `Orders.java` hiqej nga shtegu (VD-121).
    expect(within("Orders.java", "Ledger.java", "directory")).toBe("Orders.java/Ledger.java");
  });

  it("i beson serverit kur ai thotë se u lexua një skedar", () => {
    expect(within("shop/OrderManager.java", "OrderManager.java", "file")).toBe(
      "shop/OrderManager.java",
    );
  });
});

/** Nga `api/paths.py` dhe nga thirrjet e `error(...)` te `api/app.py`. */
const CODES_FROM_BACKEND = [
  "path_empty",
  "root_missing",
  "path_outside_root",
  "path_not_found",
  "too_many_files",
  "too_much_source",
  "no_java_files",
  "not_a_file",
  "bad_range",
  "unreadable",
  "advisory_only",
  "not_found",
  "path_not_directory",
  // Nga `ImportRejected(...)` te `projects/github.py`, plus hartëzimi i statusit
  // te `api/app.py`. Ana tjetër ka kopjen e vet te `test_github.py` (VD-126).
  "link_empty",
  "not_github",
  "bad_scheme",
  "credentials_in_link",
  "no_repository",
  "bad_repository",
  "bad_ref",
  "repository_not_found",
  "rate_limited",
  "http_error",
  "network",
  "timeout",
  "archive_too_large",
  "archive_broken",
  "too_many_java_files",
];

describe("mesazhet e gabimit", () => {
  it("çdo kod i backend-it ka fjali shqip", () => {
    const missing = CODES_FROM_BACKEND.filter((code) => !(code in ERROR_SQ));

    expect(missing).toEqual([]);
  });

  it("asnjë përkthim nuk rri për një kod që nuk ekziston", () => {
    // Drejtimi tjetër: një hartë që rritet pa u pastruar mbledh hyrje për kode të
    // hequra, dhe ato duken si mbulim që nuk ekziston.
    const extra = Object.keys(ERROR_SQ).filter((code) => !CODES_FROM_BACKEND.includes(code));

    expect(extra).toEqual([]);
  });

  it("asnjë mesazh nuk mbaron pa i thënë përdoruesit ku është", () => {
    for (const [code, text] of Object.entries(ERROR_SQ)) {
      expect(text.length, code).toBeGreaterThan(15);
      expect(text.trim(), code).toBe(text);
      expect(text.endsWith(".") || text.endsWith("?"), code).toBe(true);
    }
  });
});

/**
 * Nga `ModelUnavailable(...)` te `ml/serving.py`, plus `needs_project` nga
 * `api/app.py`. Ana tjetër ka kopjen e vet (`test_serving.py::REFUSAL_CODES`).
 */
const MODEL_CODES_FROM_BACKEND = [
  "needs_project",
  "not_trained",
  "library_mismatch",
  "dataset_missing",
  "feature_missing",
];

describe("arsyet pse modeli nuk u pyet", () => {
  it("çdo kod ka fjali shqip dhe asnjë fjali nuk rri pa kod", () => {
    // Pa këtë, «a model verdict needs project-wide measurement…» dilte anglisht mes
    // tekstit shqip sa herë analizohej një skedar i vetëm (VD-121).
    expect(Object.keys(MODEL_REFUSAL_SQ).sort()).toEqual([...MODEL_CODES_FROM_BACKEND].sort());
  });

  it("çdo fjali vazhdon pas dy pikave dhe mbaron me pikë", () => {
    for (const [code, text] of Object.entries(MODEL_REFUSAL_SQ)) {
      expect(text.charAt(0), code).toBe(text.charAt(0).toLowerCase());
      expect(text.endsWith("."), code).toBe(true);
    }
  });
});

/**
 * Nga `DETAILS` te `refactor/base.py`. Ana tjetër ka kopjen e vet
 * (`test_refactor_base.py::DETAIL_CODES`).
 */
const DETAIL_CODES_FROM_BACKEND = [
  "needs_void",
  "no_body",
  "not_single_conditional",
  "has_else",
  "branch_not_block",
  "branch_empty",
  "no_condition",
  "irregular_indent",
  "not_method",
  "not_private",
  "generic_method",
  "nested_enclosing_type",
  "no_parameter_list",
  "varargs_or_annotated",
  "too_few_parameters",
  "overloaded",
  "unresolvable_reference",
  "constructor",
  "no_body_to_extract",
  "no_large_block",
  "escaping_statement",
  "not_assigned",
  "several_outputs",
  "untyped_names",
  "type_parameters",
  "entity_not_found",
];

describe("hollësitë e refuzimit", () => {
  it("çdo kod i motorit ka fjali shqip dhe asnjë fjali nuk rri pa kod", () => {
    // Pa këtë, «not private, so the call sites are not local» dilte anglisht te
    // detaji i çdo metode publike me shumë parametra (VD-123).
    expect(Object.keys(REFUSAL_DETAIL_SQ).sort()).toEqual([...DETAIL_CODES_FROM_BACKEND].sort());
  });

  it("çdo fjali i fut vlerat e veta dhe mbaron me pikë", () => {
    const values = { count: 3, names: "attempts, excellent, failed", name: "total", lines: 5, statement: "return" };
    for (const [code, build] of Object.entries(REFUSAL_DETAIL_SQ)) {
      const text = build({ code, ...values });
      expect(text.endsWith("."), code).toBe(true);
      expect(text, code).not.toContain("undefined");
    }
  });

  it("i shkruan numrat dhe emrat ashtu si i dërgon motori", () => {
    expect(
      explanationText({ code: "several_outputs", count: 3, names: "attempts, excellent, failed" }),
    ).toBe("nga blloku dalin 3 vlera (attempts, excellent, failed), ndërsa një metodë kthen vetëm një.");
    expect(explanationText({ code: "escaping_statement", statement: "labelled break" })).toBe(
      "blloku përmban një break me etiketë që del jashtë tij.",
    );
  });

  it("kthen null për një kod që ende nuk njihet, që ekrani të bjerë te fjalia e motorit", () => {
    expect(explanationText({ code: "something_new" })).toBeNull();
    expect(explanationText(null)).toBeNull();
    expect(explanationText(undefined)).toBeNull();
  });
});

describe("noteText", () => {
  it("writes the wide-parameter note in Albanian with its own numbers", () => {
    // Serveri dërgon kodin dhe numrat; fjalia ndërtohet këtu, si te gabimet.
    const text = noteText({ code: "wide_parameter_list", parameters: 8, threshold: 5 });

    expect(text).toContain("8 parametra");
    expect(text).toContain("kufirin 5");
  });

  it("says in Albanian that the parameter object's constructor is as wide as the method was", () => {
    // VD-124: gjashtë parametra kalojnë te konstruktori, një mbi kufirin pesë.
    const text = noteText({ code: "wide_constructor", parameters: 6, threshold: 5 });

    expect(text).toContain("Konstruktori i objektit të ri merr 6 parametra");
    expect(text).toContain("kufirin 5");
  });

  it("falls back to the code when a note has no translation yet", () => {
    // I shëmtuar, por i sinqertë: më mirë kodi se një fjali e trilluar.
    expect(noteText({ code: "something_new" })).toBe("something_new");
  });
});

describe("patch, si rrjedhë", () => {
  /** Një trup përgjigjeje që i lëshon copat pikërisht ashtu si u dhanë. */
  function streamed(chunks: string[]): Response {
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        const encoder = new TextEncoder();
        for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
        controller.close();
      },
    });
    return new Response(body, {
      status: 200,
      headers: { "Content-Type": "application/x-ndjson" },
    });
  }

  const RESULT = { diff: "d", files: 1, changes: 2, declines: [], dropped: [] };

  afterEach(() => vi.unstubAllGlobals());

  it("reports each progress line and returns the last result", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        streamed([
          '{"progress":{"files_done":1,"files_total":2,"changes":0}}\n',
          '{"progress":{"files_done":2,"files_total":2,"changes":2}}\n',
          `{"result":${JSON.stringify(RESULT)}}\n`,
        ]),
      ),
    );

    const seen: number[] = [];
    const result = await patch("src", undefined, (p) => seen.push(p.files_done));

    expect(seen).toEqual([1, 2]);
    expect(result.changes).toBe(2);
  });

  it("survives an object split across two network chunks", async () => {
    // Një copë e lexuar nga rrjeti nuk përkon me një rresht. Pa mbajtësin e
    // bishtit, çdo gjë pas një ndarjeje të keqe do të prishej.
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        streamed(['{"progress":{"files_done":1,"files_', 'total":3,"changes":0}}\n']),
      ),
    );

    const seen: number[] = [];
    await patch("src", undefined, (p) => seen.push(p.files_total)).catch(() => undefined);

    expect(seen).toEqual([3]);
  });

  it("refuses a stream that ended without a result", async () => {
    // Heshtja këtu do ta linte ekranin te «Duke përgatitur…» përgjithmonë.
    vi.stubGlobal("fetch", vi.fn(async () => streamed(['{"progress":{"files_done":1,"files_total":1,"changes":0}}\n'])));

    await expect(patch("src")).rejects.toThrow(/para se patch-i/);
  });

  it("turns a rejected path into its Albanian message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ error: { code: "path_outside_root", message: "x" } }), {
            status: 400,
            headers: { "Content-Type": "application/json" },
          }),
      ),
    );

    await expect(patch("../x")).rejects.toThrow(ERROR_SQ.path_outside_root);
  });
});
