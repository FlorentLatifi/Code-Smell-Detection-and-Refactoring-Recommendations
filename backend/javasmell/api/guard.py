"""What every request must be before a route sees it: local, and from a local page.

The server binds to localhost and has one user, so ENGINEERING.md §6 leaves
authentication out of scope. Binding to localhost does not, on its own, keep the
rest of the web out. Two attacks reach a localhost service through the user's
own browser, and both were measured against this server before this module
existed (VD-127):

* **DNS rebinding.** A page on ``evil.example`` re-points its own name at
  127.0.0.1. The browser then treats the server as same-origin with the attacker
  and hands the responses over. A request with ``Host: evil.example`` to
  ``/browse`` and to ``/source`` came back 200: the folder listing and the source
  code were readable by any site the user happened to visit. The defence is the
  ``Host`` header: a rebound request still names the attacker's domain.
* **Cross-site requests.** A foreign page can send a POST without reading the
  answer. FastAPI refused the "simple" content types with 422, but only because
  a JSON body happens to need a JSON content type; that is a property of the
  parser, not a decision. The ``Origin`` header makes it one: every browser sends
  it on a POST, and a foreign origin is refused before any route runs.

Requests with no ``Origin`` at all -- curl, the CLI, a script -- pass, since they
do not come from a web page and a local program already has the user's access.

The same middleware adds the headers that stop the interface being framed by
another site, which is the third attack on a local tool with a button that
writes to disk.
"""

from __future__ import annotations

import json
import urllib.parse
from collections.abc import Awaitable, Callable, Iterable, MutableMapping
from typing import Any

#: Emrat me të cilët shërbimi arrihet nga vetë makina. «::1» pa kllapa, sepse
#: krahasohet emri i zgjidhur e jo teksti i kokës.
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

#: Kokat që i shtohen çdo përgjigjeje. `no-store` sepse përgjigjet mbajnë kod
#: burimor, i cili nuk ka arsye të mbetet në cache-in e shfletuesit.
SECURITY_HEADERS = (
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"content-security-policy", b"frame-ancestors 'none'"),
    (b"referrer-policy", b"no-referrer"),
    (b"cache-control", b"no-store"),
)

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


def host_name(header: str) -> str:
    """Emri i hostit nga koka ``Host``, pa portë dhe pa kllapat e IPv6.

    ``localhost:5173`` jep ``localhost``, ``[::1]:8000`` jep ``::1``. Një kokë
    që nuk lexohet dot kthen bosh, e cila nuk është kurrë host i lejuar.
    """
    value = header.strip().lower()
    if value.startswith("["):
        end = value.find("]")
        return value[1:end] if end > 0 else ""
    return value.rsplit(":", 1)[0] if value.count(":") == 1 else value


def origin_is_local(origin: str, hosts: Iterable[str]) -> bool:
    """A vjen kërkesa nga një faqe e shërbyer nga vetë kjo makinë.

    ``null`` refuzohet: e dërgojnë faqet e hapura nga disku dhe iframe-t e
    izoluara, dhe kjo e dyta është pikërisht mënyra si një faqe e huaj do ta
    fshihte origjinën e vet.
    """
    if origin == "null":
        return False
    parsed = urllib.parse.urlsplit(origin)
    if parsed.scheme not in {"http", "https"}:
        return False
    return (parsed.hostname or "") in set(hosts)


class LocalOnly:
    """Middleware ASGI që refuzon çdo kërkesë që nuk është lokale.

    ASGI e pastër e jo `BaseHTTPMiddleware`, sepse ky i fundit e mbledh trupin e
    përgjigjes në memorie, dhe `/refactor/patch/stream` duhet të rrjedhë.
    """

    def __init__(self, app: ASGIApp, hosts: Iterable[str] = LOCAL_HOSTS) -> None:
        self.app = app
        self.hosts = frozenset(host.lower() for host in hosts)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1"): value.decode("latin-1") for key, value in scope["headers"]
        }
        if host_name(headers.get("host", "")) not in self.hosts:
            await _refuse(
                send, "host_not_allowed", "requests must address this machine by a local name"
            )
            return
        origin = headers.get("origin")
        if origin is not None and not origin_is_local(origin, self.hosts):
            await _refuse(send, "origin_not_allowed", "requests from other sites are not accepted")
            return

        async def with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                present = {name for name, _ in message.get("headers", [])}
                message["headers"] = list(message.get("headers", [])) + [
                    header for header in SECURITY_HEADERS if header[0] not in present
                ]
            await send(message)

        await self.app(scope, receive, with_headers)


async def _refuse(send: Send, code: str, message: str) -> None:
    """E njëjta formë si çdo gabim tjetër i shërbimit, me 403."""
    body = json.dumps({"error": {"code": code, "message": message}}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 403,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                *SECURITY_HEADERS,
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
