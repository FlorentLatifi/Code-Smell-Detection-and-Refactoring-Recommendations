"""JavaSmell: code smell detection and verified refactoring for Java."""

# The one place the release version is written. The API reports it at `/health`,
# the CLI puts it in SARIF, and a release tag must match it (VD-156, VD-163).
__version__ = "1.1.0"
