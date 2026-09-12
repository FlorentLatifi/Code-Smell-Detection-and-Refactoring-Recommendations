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

import { ERROR_SQ, noteText, patch } from "./api";

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

describe("noteText", () => {
  it("writes the wide-parameter note in Albanian with its own numbers", () => {
    // Serveri dërgon kodin dhe numrat; fjalia ndërtohet këtu, si te gabimet.
    const text = noteText({ code: "wide_parameter_list", parameters: 8, threshold: 5 });

    expect(text).toContain("8 parametra");
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
