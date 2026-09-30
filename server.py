"""
Drex Desk - local server.

Serves the dashboard and forwards requests to the Drex API so your key
never touches the browser.

PowerShell:
    $env:DREX_API_KEY = "nace_sk_..."
    python server.py

Then open http://localhost:8765
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORT = int(os.environ.get("DREX_DESK_PORT", "8765"))
BASE = os.environ.get("DREX_BASE", "https://drex.nace.ai").rstrip("/")
KEY = os.environ.get("DREX_API_KEY", "").strip()
MODEL = os.environ.get("DREX_MODEL", "drex-v1.5")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stdout.write("  %s\n" % (fmt % args))

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, (HERE / "desk.html").read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/status":
            self._send(200, json.dumps({"key": bool(KEY), "model": MODEL, "base": BASE}))
        else:
            self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        if self.path != "/api/decide":
            return self._send(404, json.dumps({"error": "not found"}))
        if not KEY:
            return self._send(400, json.dumps({"error": "DREX_API_KEY is not set. Set it in PowerShell and restart server.py"}))
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send(400, json.dumps({"error": "bad JSON from dashboard"}))
        payload.setdefault("model", MODEL)

        req = urllib.request.Request(
            BASE + "/v1/systemone",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + KEY,
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
                self._send(200, json.dumps(body))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:2000]
            self._send(e.code, json.dumps({"error": "Drex returned %s" % e.code, "detail": detail}))
        except Exception as e:  # network, timeout
            self._send(502, json.dumps({"error": "Could not reach Drex", "detail": str(e)}))


def main():
    if not KEY:
        print("\n  ! DREX_API_KEY is not set - the desk will open but decisions will fail.")
        print('    PowerShell:  $env:DREX_API_KEY = "nace_sk_..."\n')
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = "http://localhost:%d" % PORT
    print("  Drex Desk running at %s  (model %s)  - Ctrl+C to stop" % (url, MODEL))
    if os.environ.get("DREX_NO_BROWSER") != "1":
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
