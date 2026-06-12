"""Locate the external review-parsers package directory.

The parsers live in a sibling checkout of the `medservice_parsers` repo. Depending
on how it was cloned, the directory on disk may be named either:

  * ``medservice_parsers`` — the canonical name (git repo, ``deploy.sh`` clone
    target, Dockerfile ``COPY``); this is what production uses, and
  * ``parsers`` — a bare local clone (``git clone …/medservice_parsers parsers``).

Both the in-process runner (``app/parsers/runner.py``) and the subprocess cron
worker (``scripts/verify_reviews.py``) must agree on the same directory, so the
lookup is centralised here and resolved by *content* (the dir actually contains
the parser packages) rather than by a single hard-coded name.
"""

from pathlib import Path

# Repo root = parent of medservice-backend/ (…/app/parsers/paths.py → parents[3]).
_REPO_ROOT = Path(__file__).resolve().parents[3]

# Candidate directory names, in priority order (canonical first).
_CANDIDATE_NAMES = ("medservice_parsers", "parsers")

# A directory is the parsers root only if it contains the parser packages.
_MARKER_PACKAGE = "yandex_reviews"


def find_parsers_root() -> Path | None:
    """Return the parsers package directory, or ``None`` if it isn't present.

    Resolves whichever candidate directory actually contains the parser
    packages, so a checkout named either ``medservice_parsers`` or ``parsers``
    works without configuration.
    """
    for name in _CANDIDATE_NAMES:
        candidate = _REPO_ROOT / name
        if (candidate / _MARKER_PACKAGE).is_dir():
            return candidate
    return None
