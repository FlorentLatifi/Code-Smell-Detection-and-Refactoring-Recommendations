// A ka çdo gabim që serveri mund ta kthejë një fjali shqip?
//
// I njëjti defekt si te verdiktet e panelit: pa përkthim, mesazhi anglisht del
// mes tekstit shqip dhe duket i saktë, sepse asgjë nuk prishet. «the path does
// not exist» qëndroi ashtu derisa dikush e pa në ekran.
//
// Lista më poshtë është kopje me dorë e kodeve që prodhon backend-i. Ajo anë e ka
// testin e vet (`test_api_paths.py::REJECTION_CODES`), ndaj një kod i ri i thyen
// të dyja: atje sepse bashkësia nuk përputhet, këtu sepse përkthimi mungon.

import { describe, expect, it } from "vitest";

import { ERROR_SQ } from "./api";

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
