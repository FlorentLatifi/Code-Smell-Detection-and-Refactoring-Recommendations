# Changelog

All notable changes to JavaSmell are listed here. Versions follow
[Semantic Versioning](https://semver.org/). Each version is published as a Docker image,
`ghcr.io/florentlatifi/code-smell-detection-and-refactoring-recommendations:v<version>`.
Entries name the decision record (`VD-n` in `docs/DECISIONS.md`) that explains them.

## [Unreleased]

### Changed
- The frontend declares Node 22.19 or newer. npm now warns on an older Node, where three
  test files could not start (VD-161).

## [1.1.0] - 2026-10-26

### Added
- `NOTICE` with the CC BY 4.0 attribution for the MLCQ dataset that the models are
  trained on. It also ships inside the Docker image, together with `LICENSE` (VD-157).
- `SECURITY.md`, this changelog, and an English quick start in the README (VD-157).
- **Native image for Apple Silicon and other arm64 machines.** One tag now serves both
  `linux/amd64` and `linux/arm64`, and each is tested before it is published (VD-158).
- Every image is scanned with Trivy. Publishing stops on any HIGH or CRITICAL
  vulnerability that has a fix (VD-158).
- Dependabot opens weekly update PRs for Python, npm, GitHub Actions and the base
  images (VD-158).

### Changed
- **The image is 943 MB instead of 1.19 GB.** Analysis results and `javac` verdicts are
  unchanged. Base images are pinned by digest, and pip is no longer in the final
  image (VD-158).

## [1.0.1] - 2026-10-26

### Fixed
- **Extract Method no longer produces code that does not compile** when the extracted
  block assigns a local variable without reading it. Such variables are now passed
  in as parameters, and a rewrite is refused when the variable has no value
  before the block (VD-155).
- `/api/health` and the interface now report version `1.0.1`. Version 1.0.0
  reported `0.1.0` (VD-155).

### Changed
- Every image is started and checked before it is published: the server, the page,
  the models, `javac`, and the request guard. A version tag must report its own
  version (VD-156).

### Known limitations
- The effect of the Extract Method fix on the published evaluation numbers was not
  re-measured. Those numbers belong to 1.0.0.

## [1.0.0] - 2026-10-25

First release, and the version evaluated in the bachelor thesis (VD-154).

### Added
- Smell detection with metric-based rules (Lanza & Marinescu) and with machine-learning
  models trained on MLCQ, for Long Method, Feature Envy, Data Class and Blob, plus
  further rule-based smells.
- Refactoring engine: Replace Nested Conditional with Guard Clauses, Extract Method,
  and Introduce Parameter Object (for `private` methods), each verified with `javac`.
- Web interface and CLI, a plain-language mode, and import of public GitHub repositories.

### Known limitations
- A rewrite is checked to compile, or to add no new kind of error. It is not checked
  to preserve behaviour.
- Extract Method can produce code that does not compile in one case. Fixed in 1.0.1.

[Unreleased]: https://github.com/FlorentLatifi/Code-Smell-Detection-and-Refactoring-Recommendations/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/FlorentLatifi/Code-Smell-Detection-and-Refactoring-Recommendations/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/FlorentLatifi/Code-Smell-Detection-and-Refactoring-Recommendations/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/FlorentLatifi/Code-Smell-Detection-and-Refactoring-Recommendations/releases/tag/v1.0.0
