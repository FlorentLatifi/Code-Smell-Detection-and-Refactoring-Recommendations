"""Whether the rewrites are ones a developer would keep, judged by hand.

    python scripts/review_rewrites.py --sample     # build the sheet and the diffs
    python scripts/review_rewrites.py --score      # after filling the sheet in

``--sample`` draws a seeded, stratified sample of the sites the engine actually
rewrote, regenerates each rewrite, and writes two things: a review bundle of
diffs to read (``data/review/rewrites.md``) and a blind sheet to fill in
(``data/results/rewrite_quality_sample.csv``). ``--score`` reads the filled
sheet back and writes ``data/results/rewrite_quality.json``. Minutes, not hours:
only the sampled files are parsed, and ``javac`` is never called.

**Why this exists.** Every automatic check the engine has answers a compiler's
question. ``refactoring_evaluation.json`` reports that 3 558 of 3 633 rewrites
add no new kind of error, and nothing anywhere reports whether one of them is
worth merging. The gap is the whole of the second half of Fowler's definition of
a refactoring, and no amount of further compiling closes it.

**The sheet is filled by the author, and that is a limitation, not a feature.**
One reviewer, who is also the author of the engine, is the weakest form this
measure can take. It is the form available: the alternative is a second reviewer
there is no way to recruit. The thesis reports it as one reviewer's judgement,
with the rubric fixed in advance and the sheet committed, so a reader can
disagree with a named row rather than with a number.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from javasmell.evaluation.provenance import environment  # noqa: E402
from javasmell.evaluation.quality import (  # noqa: E402
    DIMENSIONS,
    SAMPLE_PER_REFACTORING,
    SAMPLE_SEED,
    SHEET_COLUMNS,
    Site,
    applied_sites,
    diff_text,
    label_sample,
    population,
    read_judgements,
    stratified_sample,
    summarise,
)
from javasmell.evaluation.sites import sites_in  # noqa: E402
from javasmell.parsing.java_parser import JavaParser  # noqa: E402
from javasmell.refactor.edits import EditConflict, apply_edits  # noqa: E402
from javasmell.refactor.locate import FileIndex  # noqa: E402
from javasmell.refactor.registry import for_smell  # noqa: E402

DEFAULT_SITES = Path("data/results/refactoring_sites.csv")
DEFAULT_CORPUS = Path("data/corpus")
DEFAULT_OUT = Path("data/results")
DEFAULT_BUNDLE = Path("data/review/rewrites.md")

SHEET_NAME = "rewrite_quality_sample.csv"
RESULT_NAME = "rewrite_quality.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--sample", action="store_true", help="Draw the sample and write the sheet")
    mode.add_argument("--score", action="store_true", help="Summarise the filled sheet")
    parser.add_argument("--sites", type=Path, default=DEFAULT_SITES)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--per-refactoring", type=int, default=SAMPLE_PER_REFACTORING)
    parser.add_argument("--seed", type=int, default=SAMPLE_SEED)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite a sheet that already carries judgements",
    )
    return parser


def within_corpus(file: str, corpus: Path) -> str:
    """The path as the sheet records it: relative to the corpus root.

    ``refactoring_sites.csv`` stores absolute paths, which name the machine that
    produced it. A sheet is a committed result that a reader is meant to be able
    to regenerate byte for byte, and it cannot be if a column carries someone's
    home directory. Anything outside the corpus is kept as it stands rather than
    mangled into a relative path that would point somewhere else.
    """
    try:
        return Path(file).resolve().relative_to(corpus.resolve()).as_posix()
    except (OSError, ValueError):
        return file


def regenerate(labelled: list[tuple[str, Site]]) -> tuple[dict[str, str], list[str]]:
    """The diff for each sampled site, by replaying the walk that recorded it.

    A file is parsed once and its sites are walked in the recorded order, so the
    ordinal in the sheet addresses the same site the evaluation did. The class,
    method and smell are checked against the row rather than trusted: if the two
    disagree the corpus has moved under the CSV, and a diff for the wrong site is
    worse than no diff at all.
    """
    wanted: dict[str, dict[int, tuple[str, Site]]] = {}
    for review_id, site in labelled:
        wanted.setdefault(site.file, {})[site.ordinal] = (review_id, site)

    diffs: dict[str, str] = {}
    missed: list[str] = []
    for path, by_ordinal in wanted.items():
        try:
            source = Path(path).read_bytes()
        except OSError:
            missed.extend(review_id for review_id, _ in by_ordinal.values())
            continue

        index = FileIndex(str(path), source, JavaParser().parse_tree(source))
        ordinal = -1
        for class_name, method, smell_type, refactoring, line in sites_in(source, str(path)):
            automated = for_smell(smell_type)
            if automated is None:
                continue
            located = index.find(class_name, line, method)
            if located is None:
                # Not counted: the evaluation wrote no row for it either, so
                # counting it here would shift every later ordinal by one.
                continue
            ordinal += 1
            if ordinal not in by_ordinal:
                continue
            review_id, site = by_ordinal[ordinal]
            if (site.class_name, site.method, site.smell, site.refactoring) != (
                class_name,
                method,
                smell_type,
                refactoring,
            ):
                continue

            outcome = automated[1](located)
            if not outcome.applied:
                continue
            try:
                rewritten = apply_edits(source, outcome.edits)
            except (EditConflict, ValueError):
                continue
            label = f"{site.class_name}.{site.method} ({site.smell}, line {line})"
            diffs[review_id] = diff_text(source, rewritten, label)

        missed.extend(
            review_id for review_id, _ in by_ordinal.values() if review_id not in diffs
        )
    return diffs, missed


def write_bundle(
    path: Path, labelled: list[tuple[str, Site]], diffs: dict[str, str], corpus: Path
) -> None:
    """One file holding every diff to read, in the order of the sheet."""
    lines = [
        "# Rishkrimet per vleresim",
        "",
        "Nje seksion per rresht te `rewrite_quality_sample.csv`. Lexo diff-in, mbush",
        "kolonat e meposhtme te fletes, dhe `note` kur arsyeja nuk duket nga diff-i.",
        "",
    ]
    for name, enumeration in DIMENSIONS.items():
        allowed = " | ".join(member.value for member in enumeration)
        lines.append(f"- `{name}`: {allowed}")
    lines.append("")

    for review_id, site in labelled:
        diff = diffs.get(review_id)
        if diff is None:
            continue
        lines.extend(
            [
                f"## {review_id}",
                "",
                f"- rishkrimi: `{site.refactoring}`",
                f"- era: `{site.smell}`",
                f"- vendi: `{site.class_name}.{site.method}`",
                f"- skedari: `{within_corpus(site.file, corpus)}`",
                "",
                "```diff",
                diff.rstrip("\n"),
                "```",
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def filled_rows(path: Path) -> int:
    """How many rows of an existing sheet already carry a judgement."""
    if not path.exists():
        return 0
    with path.open(encoding="utf-8", newline="") as handle:
        return sum(
            1
            for row in csv.DictReader(handle)
            if any((row.get(name) or "").strip() for name in DIMENSIONS)
        )


def do_sample(args: argparse.Namespace) -> int:
    sites = applied_sites(args.sites)
    labelled = label_sample(stratified_sample(sites, args.per_refactoring, args.seed))

    sheet_path = args.out / SHEET_NAME
    already = filled_rows(sheet_path)
    if already and not args.force:
        print(
            f"{sheet_path} already carries {already} judgement(s); pass --force to discard them.",
            file=sys.stderr,
        )
        return 1

    diffs, missed = regenerate(labelled)
    args.out.mkdir(parents=True, exist_ok=True)
    with sheet_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        for review_id, site in labelled:
            if review_id not in diffs:
                continue
            writer.writerow(
                {
                    "review_id": review_id,
                    "refactoring": site.refactoring,
                    "smell": site.smell,
                    "class_name": site.class_name,
                    "method": site.method,
                    "file": within_corpus(site.file, args.corpus),
                    "ordinal": site.ordinal,
                    **{name: "" for name in DIMENSIONS},
                    "note": "",
                }
            )
    write_bundle(args.bundle, labelled, diffs, args.corpus)

    print(f"drawn        {len(labelled):>4}")
    print(f"regenerated  {len(diffs):>4}")
    print(f"unreachable  {len(missed):>4}")
    for review_id in missed:
        print(f"  {review_id}")
    print()
    print(f"Read {args.bundle}, fill {sheet_path}, then run with --score.")
    return 0


def verdicts_for(sites_path: Path, labelled: list[tuple[str, Site]]) -> dict[str, str]:
    """What ``javac`` said about each sampled site, joined by the same ordinal."""
    wanted = {(site.file, site.ordinal): review_id for review_id, site in labelled}
    found: dict[str, str] = {}
    seen: dict[str, int] = {}
    with sites_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            ordinal = seen.get(row["file"], 0)
            seen[row["file"]] = ordinal + 1
            review_id = wanted.get((row["file"], ordinal))
            if review_id is not None:
                found[review_id] = row["verdict"]
    return found


def do_score(args: argparse.Namespace) -> int:
    sheet_path = args.out / SHEET_NAME
    if not sheet_path.exists():
        print(f"sheet not found: {sheet_path}; run with --sample first", file=sys.stderr)
        return 1

    sites = applied_sites(args.sites)
    labelled = label_sample(stratified_sample(sites, args.per_refactoring, args.seed))
    by_review_id = {review_id: site for review_id, site in labelled}

    judgements = read_judgements(sheet_path)
    if not judgements:
        print(f"{sheet_path} carries no judgements yet", file=sys.stderr)
        return 1

    # The sheet is filled by hand and the sample is regenerated here, so nothing
    # but this check stands between a changed corpus and a judgement scored
    # against the wrong rewrite.
    for judgement in judgements:
        site = by_review_id.get(judgement.review_id)
        if site is None or site.ordinal != judgement.ordinal:
            print(
                f"{judgement.review_id} in the sheet is not the site the sample draws "
                "now; the sheet and refactoring_sites.csv disagree.",
                file=sys.stderr,
            )
            return 1

    summary = summarise(judgements, population(sites), verdicts_for(args.sites, labelled))
    summary["drawn"] = len(labelled)
    summary["per_refactoring"] = args.per_refactoring
    summary["seed"] = args.seed
    summary["environment"] = environment()

    result_path = args.out / RESULT_NAME
    result_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    by_refactoring = summary["by_refactoring"]
    assert isinstance(by_refactoring, dict)
    print(f"{'refactoring':<38}{'seen':>6}{'merged':>8}{'95% CI':>18}")
    print("-" * 70)
    for name, entry in by_refactoring.items():
        low, high = entry["acceptable_ci"]
        print(
            f"{name:<38}{entry['reviewed']:>6}{entry['acceptable']:>8.2f}"
            f"{f'[{low:.2f}, {high:.2f}]':>18}"
        )
    print()
    pooled = summary["acceptable_reweighted"]
    print(
        "reweighted over all applied sites: "
        + ("not computable, no stratum size known" if pooled is None else str(pooled))
    )
    print(f"Wrote {result_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.sites.exists():
        print(f"sites csv not found: {args.sites}", file=sys.stderr)
        return 1
    return do_sample(args) if args.sample else do_score(args)


if __name__ == "__main__":
    raise SystemExit(main())
