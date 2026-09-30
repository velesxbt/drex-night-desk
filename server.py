"""
Night Desk - local or hosted server.

Serves the dashboard and forwards decision requests to the Drex API.

Keys:
  - Each visitor can bring their own Drex key. The dashboard sends it in the
    X-Drex-Key header; the server forwards it and never stores or logs it.
  - If DREX_API_KEY is set, it's used as a fallback for visitors without a key.
    Leave it unset on a public deployment, or everyone spends your credits.

Local (macOS / Linux):
    export DREX_API_KEY="nace_sk_..."     # optional
    python3 server.py

Local (PowerShell):
    $env:DREX_API_KEY = "nace_sk_..."     # optional
    python server.py

Hosted (Render, Railway, Fly...): the platform sets PORT; the server then binds
to 0.0.0.0 and skips opening a browser.
"""
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOSTED = "PORT" in os.environ
PORT = int(os.environ.get("PORT") or os.environ.get("DREX_DESK_PORT") or "8765")
HOST = "0.0.0.0" if HOSTED else "127.0.0.1"
BASE = os.environ.get("DREX_BASE", "https://drex.nace.ai").rstrip("/")
SERVER_KEY = os.environ.get("DREX_API_KEY", "").strip()
MODEL = os.environ.get("DREX_MODEL", "drex-v1.5")
INVITE_URL = os.environ.get("DREX_INVITE_URL", "https://drex.nace.ai/invite/j8697dgz")

MAX_BODY = int(os.environ.get("MAX_BODY_BYTES", str(2_000_000)))     # ~128K tokens of text
RATE_LIMIT = int(os.environ.get("RATE_LIMIT_PER_MIN", "30"))         # requests per IP per minute

_hits = defaultdict(deque)
_hits_lock = threading.Lock()


def rate_limited(ip):
    if RATE_LIMIT <= 0:
        return False
    now = time.time()
    with _hits_lock:
        q = _hits[ip]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            return True
        q.append(now)
        return False


class Handler(BaseHTTPRequestHandler):
    server_version = "NightDesk/1.1"

    def log_message(self, fmt, *args):
        sys.stdout.write("  %s - %s\n" % (self.client_ip(), fmt % args))

    def client_ip(self):
        fwd = self.headers.get("X-Forwarded-For", "")
        return fwd.split(",")[0].strip() if fwd else self.client_address[0]

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj))

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._send(200, (HERE / "desk.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/status":
            self._json(200, {"server_key": bool(SERVER_KEY), "model": MODEL, "hosted": HOSTED, "invite": INVITE_URL})
        elif path == "/healthz":
            self._send(200, "ok", "text/plain")
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path.split("?")[0] != "/api/decide":
            return self._json(404, {"error": "not found"})

        key = (self.headers.get("X-Drex-Key") or "").strip() or SERVER_KEY
        if not key:
            return self._json(401, {"error": "No Drex API key. Add yours with the key button in the top right."})

        if rate_limited(self.client_ip()):
            return self._json(429, {"error": "Too many requests - wait a minute and try again."})

        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_BODY:
            return self._json(413, {"error": "Context too large for one request (limit ~%d KB)." % (MAX_BODY // 1000)})
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._json(400, {"error": "Bad JSON from dashboard"})
        payload["model"] = payload.get("model") or MODEL

        req = urllib.request.Request(
            BASE + "/v1/systemone",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = json.loads(r.read() or b"{}")
                body["_roundtrip_ms"] = round((time.perf_counter() - t0) * 1000, 1)
                self._json(200, body)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:2000]
            msg = {401: "Drex rejected the API key - check it and try again.",
                   402: "Out of Drex credits on this key.",
                   429: "Drex rate limit hit - wait a moment."}.get(e.code, "Drex returned %s" % e.code)
            self._json(e.code, {"error": msg, "detail": detail})
        except Exception as e:  # network, timeout
            self._json(502, {"error": "Could not reach Drex", "detail": str(e)})


def main():
    if not SERVER_KEY and not HOSTED:
        print("\n  No DREX_API_KEY set - add your key in the dashboard (top right), or:")
        print('    export DREX_API_KEY="nace_sk_..."      (PowerShell: $env:DREX_API_KEY = "...")\n')
    if SERVER_KEY and HOSTED:
        print("  ! DREX_API_KEY is set on a hosted server - every visitor without a key spends your credits.")
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    url = "http://localhost:%d" % PORT
    print("  Night Desk on %s:%d  (model %s)  - Ctrl+C to stop" % (HOST, PORT, MODEL))
    if not HOSTED and os.environ.get("DREX_NO_BROWSER") != "1":
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
