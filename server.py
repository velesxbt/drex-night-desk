"""
Night Desk - local or hosted server.

Serves the dashboard and forwards requests to the Nace API with the visitor's key:
  - /api/decide        -> Drex          POST /v1/systemone
  - /api/docs/...      -> Perception    /v1/documents/*  (NDI: parse, extract, ground)
One console key covers both, billed from the same credit.

Keys:
  - Each visitor can bring their own key. The dashboard sends it in the
    X-Drex-Key header; the server forwards it and never stores or logs it.
  - If DREX_API_KEY is set, it's used as a fallback for visitors without a key.
    Leave it unset on a public deployment, or everyone spends your credits.

Filings don't pass through this server: it mints a single-use upload grant and the
browser posts the file straight to the document service.

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
import mimetypes
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEMO_DIR = HERE / "demo"
HOSTED = "PORT" in os.environ
PORT = int(os.environ.get("PORT") or os.environ.get("DREX_DESK_PORT") or "8765")
HOST = "0.0.0.0" if HOSTED else "127.0.0.1"
BASE = os.environ.get("DREX_BASE", "https://drex.nace.ai").rstrip("/")
SERVER_KEY = os.environ.get("DREX_API_KEY", "").strip()
MODEL = os.environ.get("DREX_MODEL", "drex-v1.5")
INVITE_URL = os.environ.get("DREX_INVITE_URL", "https://drex.nace.ai/invite/j8697dgz")

MAX_BODY = int(os.environ.get("MAX_BODY_BYTES", str(2_000_000)))     # ~128K tokens of text
RATE_LIMIT = int(os.environ.get("RATE_LIMIT_PER_MIN", "30"))         # POSTs per IP per minute
DOC_WAIT = int(os.environ.get("DOC_WAIT_SECONDS", "25"))             # inline wait per document job call
DOC_OPS = ("parse", "extract", "ground")
MAX_ARTIFACT = 20_000_000                                            # crop images, full parsed markdown

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


def upstream_error(code, detail, docs=False):
    """Turn an upstream error into a message a visitor can act on."""
    msg = None
    try:
        err = json.loads(detail).get("error") or {}
        msg = err.get("message") if isinstance(err, dict) else None
    except (ValueError, AttributeError):
        pass
    base = {401: "Nace rejected the API key - check it and try again.",
            402: "Out of credits on this key.",
            429: "Rate limit hit - wait a moment."}.get(code)
    who = "Perception" if docs else "Drex"
    return base or ("%s returned %s%s" % (who, code, (": " + msg) if msg else ""))


class Handler(BaseHTTPRequestHandler):
    server_version = "NightDesk/1.2"

    def log_message(self, fmt, *args):
        sys.stdout.write("  %s - %s\n" % (self.client_ip(), fmt % args))

    def client_ip(self):
        fwd = self.headers.get("X-Forwarded-For", "")
        return fwd.split(",")[0].strip() if fwd else self.client_address[0]

    def _send(self, code, body, ctype="application/json", cache="no-store"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj))

    def _key(self):
        return (self.headers.get("X-Drex-Key") or "").strip() or SERVER_KEY

    def _forward(self, method, path, payload=None, docs=False):
        """Call the Nace API with the visitor's key; return (status, parsed JSON)."""
        req = urllib.request.Request(
            BASE + path,
            data=json.dumps(payload).encode("utf-8") if payload is not None else None,
            headers={"Authorization": "Bearer " + self._key(),
                     "Content-Type": "application/json",
                     "Accept": "application/json"},
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=DOC_WAIT + 35 if docs else 60) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:2000]
            return e.code, {"error": upstream_error(e.code, detail, docs), "detail": detail}
        except Exception as e:  # network, timeout
            return 502, {"error": "Could not reach the Nace API", "detail": str(e)}

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_BODY:
            self._json(413, {"error": "Context too large for one request (limit ~%d KB)." % (MAX_BODY // 1000)})
            return None
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "Bad JSON from dashboard"})
            return None

    # ---------- GET ----------
    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._send(200, (HERE / "desk.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/status":
            self._json(200, {"server_key": bool(SERVER_KEY), "model": MODEL, "hosted": HOSTED, "invite": INVITE_URL,
                             "demo_recording": (DEMO_DIR / "ndi-demo.json").is_file()})
        elif path == "/healthz":
            self._send(200, "ok", "text/plain")
        elif path.startswith("/demo/"):
            self.serve_demo(path[len("/demo/"):])
        elif path.startswith("/api/docs/jobs/"):
            self.docs_job(path[len("/api/docs/jobs/"):])
        else:
            self._json(404, {"error": "not found"})

    def serve_demo(self, rel):
        f = (DEMO_DIR / rel).resolve()
        if DEMO_DIR.resolve() not in f.parents or not f.is_file():
            return self._json(404, {"error": "not found"})
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        self._send(200, f.read_bytes(), ctype, cache="public, max-age=300")

    def docs_job(self, rest):
        """GET /api/docs/jobs/{id} polls a job; /api/docs/jobs/{id}/{artifact...} returns the artifact bytes."""
        if not self._key():
            return self._json(401, {"error": "No API key. Add yours with the key button in the top right."})
        m = re.fullmatch(r"([0-9a-fA-F-]{36})(?:/(.+))?", rest)
        if not m:
            return self._json(400, {"error": "Bad job id"})
        job_id, artifact = m.group(1), m.group(2)
        if not artifact:
            code, body = self._forward("GET", "/v1/documents/jobs/" + job_id, docs=True)
            return self._json(code, body)
        # Stored artifacts (ground crops) come back as a short-lived signed link; others (full
        # parsed markdown) are streamed. Browsers can't read a cross-origin redirect, so fetch
        # the bytes here and hand them over same-origin.
        safe = urllib.parse.quote(artifact, safe="/-_.~")
        req = urllib.request.Request(BASE + "/v1/documents/jobs/%s/%s?redirect=false" % (job_id, safe),
                                     headers={"Authorization": "Bearer " + self._key()})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data, ctype = r.read(MAX_ARTIFACT), r.headers.get("Content-Type", "application/octet-stream")
            if ctype.startswith("application/json"):
                body = json.loads(data or b"{}")
                link = isinstance(body, dict) and (body.get("url") or next(
                    (v for v in body.values() if isinstance(v, str) and v.startswith("https://")), None))
                if link:
                    with urllib.request.urlopen(link, timeout=30) as r:
                        data, ctype = r.read(MAX_ARTIFACT), r.headers.get("Content-Type", "application/octet-stream")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:2000]
            return self._json(e.code, {"error": upstream_error(e.code, detail, True), "detail": detail})
        except Exception as e:
            return self._json(502, {"error": "Could not download the artifact", "detail": str(e)})
        self._send(200, data, ctype, cache="private, max-age=600")

    # ---------- POST ----------
    def do_POST(self):
        path = self.path.split("?")[0]
        routes = {"/api/decide": None, "/api/docs/grant": None}
        routes.update({"/api/docs/" + op: op for op in DOC_OPS})
        if path not in routes:
            return self._json(404, {"error": "not found"})

        if not self._key():
            return self._json(401, {"error": "No API key. Add yours with the key button in the top right."})
        if rate_limited(self.client_ip()):
            return self._json(429, {"error": "Too many requests - wait a minute and try again."})
        payload = self._read_json()
        if payload is None:
            return

        if path == "/api/decide":
            payload["model"] = payload.get("model") or MODEL
            t0 = time.perf_counter()
            code, body = self._forward("POST", "/v1/systemone", payload)
            if code == 200:
                body["_roundtrip_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            return self._json(code, body)

        if path == "/api/docs/grant":
            # The grant is free; the file then goes straight from the browser to the document service.
            name = re.sub(r"[^\w.\- ]+", "_", str(payload.get("file_name") or "")).lstrip(".")[:120] or "filing"
            grant = {"path": "night-desk/%d-%s" % (int(time.time() * 1000), name), "ttl_seconds": 600}
            code, body = self._forward("POST", "/v1/documents/upload-grants", grant, docs=True)
            if code in (200, 201):
                body["path"] = grant["path"]   # the upload's metadata must name the same pinned path
            return self._json(code, body)

        op = routes[path]
        # ?wait=0 returns the job at once, so the desk can poll it and show progressive results
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("wait", [""])[0]
        wait = min(int(q), DOC_WAIT) if q.isdigit() else DOC_WAIT
        code, body = self._forward("POST", "/v1/documents/%s?wait_seconds=%d" % (op, wait), payload, docs=True)
        self._json(code, body)


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
