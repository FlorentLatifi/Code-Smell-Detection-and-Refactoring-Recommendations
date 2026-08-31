"""The HTTP surface over analysis, detection and refactoring.

Transport only, as the architecture requires (ENGINEERING.md §2): these handlers
validate input, call the packages that do the work, and serialise what comes
back. No detection rule and no transformation lives here, and none should; a
rule that could only be reached through HTTP would be a rule the test suite
cannot exercise.

**Stateless on purpose.** The plan sketched project identifiers and a server-side
cache so a UI could page through results without re-analysing. That is not built,
because it would add eviction, staleness and identity to a single-user tool
running on localhost, and buy little: ``/analyze`` returns everything it found in
one response, and ``/refactor/preview`` re-reads exactly one file, which costs
milliseconds. If a frontend later shows that paging matters, the cache can be
added behind these same routes without changing them.

**Errors carry a code and a message, never a stack trace and never a resolved
path.** An absolute path in an error tells the caller where the root is and
confirms what exists outside it.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from javasmell.analysis import analyze_path
from javasmell.api.paths import PathRejected, confine, java_files_under
from javasmell.api.settings import Settings
from javasmell.detectors.base import Smell
from javasmell.detectors.rules import detect_all
from javasmell.ml.serving import (
    ModelReport,
    ModelUnavailable,
    Prediction,
    load_models,
    predict_all,
    rule_equivalent,
)
from javasmell.model.entities import ProjectModel
from javasmell.refactor.base import Outcome
from javasmell.refactor.edits import apply_edits
from javasmell.refactor.locate import find_site
from javasmell.refactor.registry import ADVISORY_ONLY, for_smell

API_TITLE = "JavaSmell"
API_VERSION = "0.1.0"

# A finding spans a class or a method, not a file. The cap is generous enough for
# the largest God Class in the corpus and small enough that no single response
# carries a generated file.
MAX_SOURCE_LINES = 400

# Contributions come back sorted by how far the verdict falls when a measurement
# is made typical, and every decisive one necessarily outranks every non-decisive
# one: to be decisive a measurement must push the probability below the boundary,
# which is a larger drop than any measurement that leaves it above. Five is
# therefore enough to always carry the decisive measurement when one exists.
MAX_CONTRIBUTIONS = 5

# ATFD and CBO are defined against the types of the *project*, so in a one-file
# "project" they collapse towards zero and the strategies that read them stop
# firing (VD-16). The model reads the same columns, and measured against a corpus
# project it degrades the same way rather than worse -- mostly falling quiet, with
# a small number of flags it would not otherwise raise.
#
# It is refused all the same, and for the explanation rather than the verdict.
# What the interface shows beside a model flag is the measurement holding it up,
# and on a single file that is liable to be one whose value is an artefact of how
# much was read. "CBO is 0, which is why this is a Blob" is a sentence about the
# request, not about the code. `scripts/model_without_project.py` measures both
# effects; VD-48 records the decision.
MODEL_NEEDS_PROJECT = (
    "a model verdict needs project-wide measurement; analyse the project "
    "directory rather than a single file"
)


class PathRequest(BaseModel):
    path: str = Field(min_length=1, max_length=4096, description="File or directory to analyse")


class AnalyseRequest(PathRequest):
    #: Approach B is opt-in. Reading four models and the medians they are
    #: explained against costs about a second, and a caller that wants only the
    #: rules should not pay it on every request.
    include_model: bool = False


class SourceRequest(BaseModel):
    path: str = Field(min_length=1, max_length=4096)
    start_line: int = Field(ge=1, le=10_000_000)
    end_line: int = Field(ge=1, le=10_000_000)


class PreviewRequest(BaseModel):
    path: str = Field(min_length=1, max_length=4096)
    class_name: str = Field(min_length=1, max_length=512)
    method: str | None = Field(default=None, max_length=512)
    start_line: int = Field(ge=1, le=10_000_000)
    smell_type: str = Field(min_length=1, max_length=64)


def error(code: str, message: str, status: int) -> JSONResponse:
    """The single shape every failure takes."""
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application. Settings are injected so tests can narrow the root."""
    config = settings or Settings.from_environment()
    app = FastAPI(title=API_TITLE, version=API_VERSION)
    app.state.settings = config

    @app.exception_handler(PathRejected)
    async def _rejected(_: Request, exc: PathRejected) -> JSONResponse:
        return error("path_rejected", str(exc), 400)

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "version": API_VERSION, "root": config.root.name}

    @app.post("/analyze")
    def analyze(request: AnalyseRequest) -> dict[str, Any]:
        """Measure a path and return every smell found in it."""
        target = confine(request.path, config.root)
        java_files_under(target, max_files=config.max_files, max_bytes=config.max_bytes)

        project = analyze_path(str(target))
        smells = detect_all(project)
        classes = list(project.classes)

        payload: dict[str, Any] = {
            "summary": {
                "files": len(project.units),
                "classes": len(classes),
                "methods": sum(len(c.methods) for c in classes),
                "smells": len(smells),
                "by_severity": _counted(s.severity.value for s in smells),
                "by_type": _counted(s.smell_type for s in smells),
            },
            "smells": [_smell_json(s, target) for s in smells],
        }
        if request.include_model:
            payload["model"] = _model_block(project, target, config)
        return payload

    @app.post("/metrics")
    def metrics(request: PathRequest) -> dict[str, Any]:
        """The measured metrics for every class at a path."""
        target = confine(request.path, config.root)
        java_files_under(target, max_files=config.max_files, max_bytes=config.max_bytes)

        project = analyze_path(str(target))
        return {
            "classes": [
                {
                    "name": cls.name,
                    "package": cls.package,
                    "kind": cls.kind,
                    "file": _relative(cls.file_path, target),
                    "start_line": cls.start_line,
                    "metrics": {k: round(v, 3) for k, v in sorted(cls.metrics.items())},
                    "methods": [
                        {
                            "name": method.name,
                            "signature": method.signature,
                            "start_line": method.start_line,
                            "metrics": {k: round(v, 3) for k, v in sorted(method.metrics.items())},
                        }
                        for method in cls.methods
                    ],
                }
                for unit in project.units
                for cls in unit.classes
            ]
        }

    @app.post("/source", response_model=None)
    def source(request: SourceRequest) -> dict[str, Any] | JSONResponse:
        """The lines of one file around a finding.

        A detector reports a class or a method by position, and the only way to
        judge what it found is to read it. The whole file is not sent: a finding
        has a span, and a caller that wanted more could ask for more.

        Reading is confined to the allowed root by the same check every other
        route uses, and capped in lines so a generated file cannot be pulled
        through this route in one response.
        """
        target = confine(request.path, config.root)
        if not target.is_file():
            return error("not_a_file", "source is read one file at a time", 400)
        if request.end_line < request.start_line:
            return error("bad_range", "the range ends before it starts", 400)

        try:
            text = target.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return error("unreadable", "the file could not be read", 400)

        lines = text.splitlines()
        first = min(request.start_line, len(lines))
        last = min(request.end_line, first + MAX_SOURCE_LINES - 1, len(lines))
        return {
            "start_line": first,
            "end_line": last,
            "truncated": last < min(request.end_line, len(lines)),
            "lines": lines[first - 1 : last],
        }

    # The handler answers either with a body or with a structured error, and
    # FastAPI cannot derive one response model from that union.
    @app.post("/refactor/preview", response_model=None)
    def preview(request: PreviewRequest) -> dict[str, Any] | JSONResponse:
        """What the engine would write, without writing it.

        Nothing here touches the file. The response carries the rewritten text
        so a caller can show a diff and decide; applying it is a separate action
        that does not exist yet, and when it does it will need its own flag and a
        clean working tree (ENGINEERING.md §4).
        """
        target = confine(request.path, config.root)
        if not target.is_file():
            return error("not_a_file", "a preview needs a single file", 400)

        automated = for_smell(request.smell_type)
        if automated is None:
            reason = ADVISORY_ONLY.get(request.smell_type, "no transformation for that smell")
            return error("advisory_only", reason, 422)

        source = target.read_bytes()
        site = find_site(
            str(target), source, request.class_name, request.start_line, request.method
        )
        if site is None:
            return error("not_found", "no such entity at that line", 404)

        outcome = automated[1](site)
        return _outcome_json(outcome, source)

    return app


def _counted(values: Iterable[str]) -> dict[str, int]:
    counted: dict[str, int] = {}
    for value in values:
        counted[value] = counted.get(value, 0) + 1
    return dict(sorted(counted.items()))


def _relative(file_path: str, target: Path) -> str:
    """A path the caller can read, never an absolute one."""
    try:
        base = target if target.is_dir() else target.parent
        return str(Path(file_path).relative_to(base)).replace("\\", "/")
    except ValueError:
        return Path(file_path).name


def _smell_json(smell: Smell, target: Path) -> dict[str, Any]:
    payload: dict[str, Any] = smell.to_dict()
    payload["file_path"] = _relative(smell.file_path, target)
    payload["automated"] = for_smell(smell.smell_type) is not None
    return payload


def _model_block(project: ProjectModel, target: Path, config: Settings) -> dict[str, Any]:
    """Approach B over the same measured project, or why it declined to answer.

    A missing model is not an error for this request: the rules ran and found
    what they found, and a caller that asked for a second opinion gets told why
    there is none rather than losing the first one.
    """
    if target.is_file():
        return {"available": False, "reason": MODEL_NEEDS_PROJECT}
    try:
        models = load_models(config.models_dir, config.dataset_csv)
    except ModelUnavailable as exc:
        return {"available": False, "reason": str(exc)}

    reports = predict_all(models, project)
    return {
        "available": True,
        "smells": [_report_json(report, target) for report in reports],
    }


def _report_json(report: ModelReport, target: Path) -> dict[str, Any]:
    """One model's findings, with the entities it could not judge still counted."""
    flagged = [p for p in report.predictions if p.flagged]
    return {
        "smell": report.smell,
        "rule_equivalent": list(rule_equivalent(report.smell)),
        "considered": report.considered,
        "incomplete": report.incomplete,
        "flagged": len(flagged),
        "predictions": [_prediction_json(p, target) for p in flagged],
    }


def _prediction_json(prediction: Prediction, target: Path) -> dict[str, Any]:
    return {
        "smell": prediction.smell,
        "file_path": _relative(prediction.file_path, target),
        "class_name": prediction.class_name,
        "method": prediction.method,
        "start_line": prediction.start_line,
        "end_line": prediction.end_line,
        "probability": prediction.probability,
        "contributions": [
            {
                "feature": c.feature,
                "value": round(c.value, 3),
                "typical": round(c.typical, 3),
                "drop": c.drop,
                "decisive": c.decisive,
            }
            for c in prediction.contributions[:MAX_CONTRIBUTIONS]
        ],
    }


def _outcome_json(outcome: Outcome, source: bytes) -> dict[str, Any]:
    if not outcome.applied:
        return {
            "applied": False,
            "refactoring": outcome.refactoring,
            "target": outcome.target,
            "refusal": None if outcome.refusal is None else outcome.refusal.value,
            "detail": outcome.detail,
        }
    return {
        "applied": True,
        "refactoring": outcome.refactoring,
        "target": outcome.target,
        "edits": len(outcome.edits),
        "before": source.decode("utf-8", errors="replace"),
        "after": apply_edits(source, outcome.edits).decode("utf-8", errors="replace"),
    }
