import csv
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from main import main as run_pipeline

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
PORT = 8000

_pipeline_lock = threading.Lock()
_last_signature = None


def input_signature():
    return tuple(
        (path.name, path.stat().st_mtime_ns, path.stat().st_size)
        for path in sorted(RAW.iterdir())
        if path.suffix.lower() in {".csv", ".xlsx", ".xls"}
    )


def refresh_pipeline():
    global _last_signature
    signature = input_signature()
    if signature == _last_signature:
        return
    with _pipeline_lock:
        if signature != _last_signature:
            run_pipeline()
            _last_signature = signature


def csv_json(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


class DashboardHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        relative = super().translate_path(path).replace(str(ROOT), "").lstrip("\\/")
        if not relative:
            relative = "frontend\\index.html"
        elif relative in {"script.js", "style.css"}:
            relative = "frontend\\" + relative
        return str(ROOT / relative)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/dashboard":
            try:
                refresh_pipeline()
                payload = {
                    "cleaned": csv_json(OUT / "cleaned_data.csv"),
                    "priority": csv_json(OUT / "intervention_priority.csv"),
                }
                body = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as error:
                body = json.dumps({"error": str(error)}).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            return

        super().do_GET()


if __name__ == "__main__":
    print(f"Dashboard running at http://localhost:{PORT}")
    print("Watching data/raw for changes. Press Ctrl+C to stop.")
    server = ThreadingHTTPServer(("localhost", PORT), DashboardHandler)
    server.serve_forever()
