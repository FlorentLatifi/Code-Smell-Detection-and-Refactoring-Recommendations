"""One process that serves the built interface and the API together.

Until now the tool ran as two processes: the API on 8000 and Vite's development
server on 5173, proxying ``/api`` to the first. That is right for working on the
interface and wrong for using it. The development server recompiles on demand,
needs Node and ``node_modules`` on every start, and is one more port that can be
taken by a leftover process -- the failure the launcher now checks for (VD-126).

Here the interface is the output of ``npm run build``: static files, served by
the same process as the API. The interface already calls the API under
``/api``, so the API is mounted there and nothing in the frontend changes. Node
is needed once, to build; running the tool needs Python alone (VD-127).

The static files pass through the same guard as the API. The page carries the
button that writes to disk, so it is the page, more than the API, that must not
be framed by another site or served under a rebound host name.
"""

from __future__ import annotations

import os
from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

from javasmell.api.app import create_app
from javasmell.api.guard import LocalOnly
from javasmell.api.settings import Settings

_REPO = Path(__file__).resolve().parents[3]
DEFAULT_UI_DIR = _REPO / "frontend" / "dist"


class InterfaceMissing(RuntimeError):
    """Ndërfaqja nuk është ndërtuar, dhe pa të nuk ka çfarë të shërbehet."""


def create_bundle(settings: Settings | None = None, ui_dir: Path | None = None) -> Starlette:
    """Ndërfaqja te ``/`` dhe API-ja te ``/api``, në një aplikacion të vetëm.

    Refuzon të niset pa ``index.html``: një server që hapet dhe kthen 404 te
    faqja e parë duket si mjet i prishur, ndërsa një mesazh që thotë «ndërtoje
    ndërfaqen» thotë saktësisht çfarë të bëhet.
    """
    config = settings or Settings.from_environment()
    directory = ui_dir or Path(os.environ.get("JAVASMELL_UI", DEFAULT_UI_DIR))
    if not (directory / "index.html").is_file():
        raise InterfaceMissing(
            f"the interface is not built at {directory}; run `npm run build` in frontend/"
        )

    interface = LocalOnly(StaticFiles(directory=directory, html=True), hosts=config.allowed_hosts)
    return Starlette(
        routes=[
            Mount("/api", app=create_app(config)),
            Mount("/", app=interface),
        ]
    )
