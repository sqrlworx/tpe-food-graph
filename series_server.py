"""The series dashboard with editing: create, edit and delete series, take snapshots, mark posts
published, and render posts, from the browser.

  python3 -I series.py serve [--port 8765] [--host 127.0.0.1]

then open http://localhost:8765/ (from a laptop, forward the port first, e.g.
`ssh -L 8765:localhost:8765 <devserver>` or the editor's port forwarding).

The page is series/index.html built fresh on every load, with a token the API requires on every
change, so only the page this server sent can change anything. Each change goes through
the same functions as the series.py commands and rewrites series/index.html, so the read-only copy
stays current. The server answers on localhost only unless --host says otherwise, and serves
only the dashboard, the project ranking pages and the series' rendered posts.

API (JSON in, JSON out; header X-Series-Token):
  POST   /api/scaffold                 {project, top_n, filter, where} -> suggested id, wording, candidate count
  POST   /api/series                   {id, definition} create
  PUT    /api/series/<id>              {definition} replace series.json
  DELETE /api/series/<id>              only a series without snapshots
  POST   /api/series/<id>/adjust       {action: pin|unpin|move|exclude|restore|reset, handle, rank, note, reason}
  POST   /api/series/<id>/snapshot     {label, date, replace}
  POST   /api/series/<id>/publish      {n, url, date, snapshot}
  POST   /api/series/<id>/unpublish    {n, snapshot}
  POST   /api/series/<id>/render       {no_fetch} runs posts.py -s <id> in the background
  GET    /api/jobs/<id>                the render's state and log
"""

import collections
import datetime
import http.server
import json
import mimetypes
import os
import re
import secrets
import subprocess
import sys
import threading
import urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import series  # noqa: E402

TOKEN = secrets.token_urlsafe(24)
MAX_BODY = 1 << 20
# Files the server may send besides the dashboard: project ranking pages, rendered posts.
SERVABLE = re.compile(r"^(projects/[a-z0-9_-]+/output/[^/]+\.(html|png)|series/[a-z0-9-]+/posts/.+|vendor/[^/]+\.js)$")
JOBS = {}  # series id -> {"proc", "log": deque, "started", "args"}
LOCK = threading.Lock()
# Requests that read or change series run one at a time (series.py caches loaded series in a global).
STATE = threading.Lock()


class Error(Exception):
    def __init__(self, status, msg):
        super().__init__(msg)
        self.status = status


def fresh():
    """Forget loaded series, so every request sees the files as they are now."""
    series._loaded.clear()


def body_of(handler):
    n = int(handler.headers.get("Content-Length") or 0)
    if n > MAX_BODY:
        raise Error(413, "request too large")
    raw = handler.rfile.read(n) if n else b"{}"
    try:
        data = json.loads(raw or b"{}")
    except ValueError:
        raise Error(400, "the body must be JSON")
    if not isinstance(data, dict):
        raise Error(400, "the body must be a JSON object")
    return data


def date_of(v):
    v = v or datetime.date.today().isoformat()
    try:
        datetime.date.fromisoformat(v)
    except (TypeError, ValueError):
        raise Error(400, f"{v!r} is not a date (YYYY-MM-DD)")
    return v


def n_of(data):
    n = data.get("n")
    if not isinstance(n, int) or isinstance(n, bool):
        raise Error(400, "n: the post number")
    return n


def snapshot_of(data):
    d = data.get("snapshot")
    return date_of(d) if d else None


# --- Actions ---------------------------------------------------------------------------

def scaffold(data):
    if data.get("project") not in series.project.available():
        raise Error(400, "pick a project")
    top = data.get("top_n")
    top = top if isinstance(top, int) and not isinstance(top, bool) and 0 < top <= 500 else None
    flt = {k: v for k, v in (data.get("filter") or {}).items() if k in series.FILTER_KEYS and v}
    return series.scaffold(data["project"], top, flt, data.get("where") or None)


def create(data):
    s = series.save_definition(data.get("id"), data.get("definition"), create=True)
    return {"id": s.id, "candidates": len(s.pool()[0])}


def update(sid, data):
    d = data.get("definition")
    # The form doesn't carry hand edits; keep the ones series.json has.
    if isinstance(d, dict) and "adjust" not in d and series.load(sid).defn.get("adjust"):
        d = {**d, "adjust": series.load(sid).defn["adjust"]}
    s = series.save_definition(sid, d, create=False)
    return {"id": s.id, "candidates": len(s.pool()[0])}


def adjust(sid, data):
    action = data.get("action")
    if action not in ("pin", "unpin", "move", "exclude", "restore", "reset"):
        raise Error(400, "action: pin, unpin, move, exclude, restore or reset")
    handle = data.get("handle")
    if action != "reset" and not (isinstance(handle, str) and re.fullmatch(r"[A-Za-z0-9._]{1,60}", handle)):
        raise Error(400, "handle: an Instagram handle")
    note = data.get("note") or None
    if note is not None and (not isinstance(note, str) or len(note) > 200):
        raise Error(400, "note: up to 200 characters")
    reason = data.get("reason")
    if reason is not None and (not isinstance(reason, str) or len(reason) > 200):
        raise Error(400, "reason: up to 200 characters")
    s = series.edit_adjust(series.load(sid), action, handle, data.get("rank"), note, reason)
    return {"ok": True, "entries": len(s.entries())}


def delete(sid):
    if sid in JOBS and JOBS[sid]["proc"].poll() is None:
        raise Error(409, f"{sid} is rendering; wait for it to finish")
    series.delete_series(sid)
    return {"deleted": sid}


def snapshot(sid, data):
    s = series.load(sid)
    label = data.get("label") or ""
    if not isinstance(label, str) or len(label) > 100:
        raise Error(400, "label: up to 100 characters")
    date = date_of(data.get("date"))
    if os.path.exists(s.snapshot_path(date)) and not data.get("replace"):
        raise Error(409, f"there is already a {date} snapshot")
    series.take_snapshot(s, date, label.strip(), bool(data.get("replace")))
    return {"date": date}


def publish(sid, data, on):
    s = series.load(sid)
    value = None
    if on:
        url = (data.get("url") or "").strip()
        if url and not re.fullmatch(r"https://(www\.)?instagram\.com/\S+", url):
            raise Error(400, "the link should be an https://www.instagram.com/... post")
        value = {"date": date_of(data.get("date")), **({"url": url} if url else {})}
    series.set_published(s, n_of(data), snapshot_of(data), value)
    return {"ok": True}


def render(sid, data):
    series.load(sid)  # exists
    with LOCK:
        job = JOBS.get(sid)
        if job and job["proc"].poll() is None:
            raise Error(409, f"{sid} is already rendering")
        args = [sys.executable, "-I", "posts.py", "-s", sid] + (["--no-fetch"] if data.get("no_fetch") else [])
        proc = subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        job = JOBS[sid] = {"proc": proc, "log": collections.deque(maxlen=400),
                           "started": datetime.datetime.now().isoformat(timespec="seconds"),
                           "args": " ".join(["python3 -I", *args[2:]])}
    threading.Thread(target=lambda: [job["log"].append(line.rstrip("\n")) for line in proc.stdout], daemon=True).start()
    return job_state(sid)


def job_state(sid):
    job = JOBS.get(sid)
    if not job:
        return {"running": False, "log": [], "returncode": None}
    code = job["proc"].poll()
    return {"running": code is None, "returncode": code, "started": job["started"], "command": job["args"],
            "log": list(job["log"])}


# --- HTTP ------------------------------------------------------------------------------

class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "series"

    def log_message(self, fmt, *args):
        sys.stderr.write(f"  {self.command} {self.path} {args[1] if len(args) > 1 else ''}\n")

    def send(self, status, body, ctype="application/json"):
        if not isinstance(body, bytes):
            body = (json.dumps(body, ensure_ascii=False) if ctype == "application/json" else body).encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith(("text/", "application/json")) else ""))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def host_ok(self):
        # Only answer to the names this server is reached by on this machine (defeats DNS rebinding).
        if self.server.server_address[0] not in ("127.0.0.1", "::1", "localhost"):
            return True  # --host chose to listen beyond this machine; the token still guards changes
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]")
        return host in ("localhost", "127.0.0.1", "::1")

    def do_GET(self):
        if not self.host_ok():
            return self.send(403, {"error": "unexpected Host"})
        path = urllib.parse.urlparse(self.path).path
        try:
            if path in ("/", "/series", "/series/"):
                self.send_response(302)
                self.send_header("Location", "/series/index.html")
                self.end_headers()
                return
            if path == "/series/index.html":
                with STATE:
                    fresh()
                    html, _ = series.dashboard_html(live={"token": TOKEN})
                return self.send(200, html, "text/html")
            m = re.fullmatch(r"/api/jobs/([a-z0-9-]+)", path)
            if m:
                self.check_token()
                return self.send(200, job_state(m.group(1)))
            rel = urllib.parse.unquote(path.lstrip("/"))
            full = os.path.realpath(os.path.join(ROOT, rel))
            if not SERVABLE.match(rel) or ".." in rel.split("/") or not full.startswith(ROOT + os.sep) \
                    or not os.path.isfile(full):
                return self.send(404, "not found", "text/plain")
            ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
            with open(full, "rb") as f:
                return self.send(200, f.read(), ctype)
        except Error as e:
            return self.send(e.status, {"error": str(e)})

    def check_token(self):
        if not secrets.compare_digest(self.headers.get("X-Series-Token") or "", TOKEN):
            raise Error(403, "reload the dashboard (the server was restarted)")

    def change(self, method):
        if not self.host_ok():
            return self.send(403, {"error": "unexpected Host"})
        path = urllib.parse.urlparse(self.path).path
        try:
            self.check_token()
            if "application/json" not in (self.headers.get("Content-Type") or ""):
                raise Error(415, "send JSON")
            data = body_of(self)
            fresh()
            m = re.fullmatch(r"/api/series/([a-z0-9-]+)(?:/([a-z]+))?", path)
            if method == "POST" and path == "/api/scaffold":
                return self.send(200, scaffold(data))
            if method == "POST" and path == "/api/series":
                out = create(data)
            elif m and method == "PUT" and not m.group(2):
                out = update(m.group(1), data)
            elif m and method == "DELETE" and not m.group(2):
                out = delete(m.group(1))
            elif m and method == "POST" and m.group(2) == "adjust":
                out = adjust(m.group(1), data)
            elif m and method == "POST" and m.group(2) == "snapshot":
                out = snapshot(m.group(1), data)
            elif m and method == "POST" and m.group(2) in ("publish", "unpublish"):
                out = publish(m.group(1), data, m.group(2) == "publish")
            elif m and method == "POST" and m.group(2) == "render":
                return self.send(202, render(m.group(1), data))
            else:
                raise Error(404, f"no {method} {path}")
            fresh()
            series.write_dashboard()
            return self.send(200, out)
        except Error as e:
            return self.send(e.status, {"error": str(e)})
        except SystemExit as e:  # the series.py functions report bad input this way
            return self.send(400, {"error": str(e)})

    def do_POST(self):
        with STATE:
            self.change("POST")

    def do_PUT(self):
        with STATE:
            self.change("PUT")

    def do_DELETE(self):
        with STATE:
            self.change("DELETE")


def serve(host, port):
    server = http.server.ThreadingHTTPServer((host, port), Handler)
    shown = "localhost" if host in ("127.0.0.1", "::1", "localhost") else host
    print(f"series dashboard: http://{shown}:{port}/   (Ctrl-C to stop)")
    if host not in ("127.0.0.1", "::1", "localhost"):
        print(f"  listening on {host}: anyone who can reach it can open the page and make changes")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
