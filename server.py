import csv
import io
import json
import os
import tempfile
import threading
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from zipfile import BadZipFile

import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

from main import main as run_pipeline
from src.cpcb import CPCBError, get_station_data
from src.hotspot_detection import detect_hotspots
from src.preprocessing import _read_csv_tolerant, prepare
from src.priority_scoring import calculate_priority

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
PORT = 8000
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
VERCEL_UPLOAD_BYTES = 4 * 1024 * 1024
VERCEL_OUT = Path(tempfile.gettempdir()) / "asphaltair" / "processed"

_pipeline_lock = threading.Lock()
_last_signature = None


def upload_limit_bytes():
    return VERCEL_UPLOAD_BYTES if os.environ.get("VERCEL") else MAX_UPLOAD_BYTES


def upload_limit_message():
    return f"Choose a non-empty file no larger than {upload_limit_bytes() // (1024 * 1024)} MB."


def input_signature():
    return tuple(
        (path.name, path.stat().st_mtime_ns, path.stat().st_size)
        for path in sorted(RAW.iterdir())
        if path.suffix.lower() in {".csv", ".xlsx", ".xls"}
    )


def refresh_pipeline(output_dir=None):
    global _last_signature
    signature = input_signature()
    if signature == _last_signature:
        return
    with _pipeline_lock:
        if signature != _last_signature:
            if output_dir is None:
                run_pipeline()
            else:
                run_pipeline(output_dir=output_dir)
            _last_signature = signature


def csv_json(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def analyze_upload(name, content, mapping):
    suffix = Path(name).suffix.lower()
    if not content or len(content) > upload_limit_bytes():
        raise ValueError(upload_limit_message())
    if suffix not in {".csv", ".xlsx"}:
        raise ValueError("Upload a CSV or XLSX file.")

    if suffix == ".csv":
        skipped_rows = []

        def skip_malformed_row(fields):
            skipped_rows.append(len(fields))
            return None

        source = _read_csv_tolerant(
            io.BytesIO(content),
            source_name=name,
            on_bad_line=skip_malformed_row,
        )
    else:
        skipped_rows = []
        source = pd.read_excel(io.BytesIO(content), engine="openpyxl")
    if source.empty:
        raise ValueError("The dataset has no data rows.")
    if "time" in mapping and "timestamp" not in mapping:
        raise ValueError("Map the date column as well when mapping a time column.")

    cleaned = prepare(source, name, mapping, allow_missing_timestamp=True)
    priority = calculate_priority(detect_hotspots(cleaned))
    return {
        "cleaned": json.loads(cleaned.to_json(orient="records", date_format="iso")),
        "priority": json.loads(priority.to_json(orient="records")),
        "cleaned_csv": cleaned.to_csv(index=False),
        "input_rows": len(source) + len(skipped_rows),
        "output_rows": len(cleaned),
        "has_timestamp": bool(cleaned["timestamp"].notna().any()),
        "skipped_malformed_rows": len(skipped_rows),
    }


class DashboardHandler(SimpleHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/upload":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        origin = self.headers.get("Origin")
        host = self.headers.get("Host", "")
        if origin and origin not in {f"http://{host}", f"https://{host}"}:
            self.send_json(HTTPStatus.FORBIDDEN, {"error": "Cross-origin uploads are not allowed."})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > upload_limit_bytes():
                raise ValueError(upload_limit_message())
            name = Path(unquote(self.headers.get("X-File-Name", "")).replace("\\", "/")).name
            content = self.rfile.read(length)
            if len(content) != length:
                raise ValueError("The upload was incomplete.")
            params = parse_qs(parsed.query)
            mapping = {key: values[0] for key, values in params.items()}
            self.send_json(HTTPStatus.OK, analyze_upload(name, content, mapping))
        except (ValueError, UnicodeDecodeError, pd.errors.ParserError, BadZipFile) as error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except Exception as error:
            self.log_error("Upload failed: %s", error)
            self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Could not process the uploaded file."})

    def translate_path(self, path):
        relative = super().translate_path(path).replace(str(ROOT), "").lstrip("\\/")
        if not relative:
            relative = "frontend\\index.html"
        elif relative in {"script.js", "style.css"}:
            relative = "frontend\\" + relative
        return str(ROOT / relative)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/cpcb":
            params = parse_qs(parsed.query)
            try:
                self.send_json(HTTPStatus.OK, get_station_data(
                    params.get("city", [""])[0], params.get("state", [""])[0]
                ))
            except ValueError as error:
                self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            except CPCBError as error:
                self.send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": str(error)})
            return
        if parsed.path == "/api/dashboard":
            try:
                output_dir = VERCEL_OUT if os.environ.get("VERCEL") else None
                refresh_pipeline(output_dir)
                out_dir = output_dir if output_dir is not None else OUT
                payload = {
                    "cleaned": csv_json(out_dir / "cleaned_data.csv"),
                    "priority": csv_json(out_dir / "intervention_priority.csv"),
                    "upload_limit_bytes": upload_limit_bytes(),
                }
                self.send_json(HTTPStatus.OK, payload)
            except Exception as error:
                self.log_error("Dashboard refresh failed: %s", error)
                self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(error)})
            return

        super().do_GET()


app = Flask(__name__, static_folder=None)


@app.get("/")
def dashboard():
    return send_from_directory(ROOT / "frontend", "index.html")


@app.get("/<path:asset>")
def dashboard_asset(asset):
    if asset not in {"script.js", "style.css"}:
        return jsonify({"error": "Not found."}), HTTPStatus.NOT_FOUND
    return send_from_directory(ROOT / "frontend", asset)


@app.get("/api/dashboard")
def api_dashboard():
    try:
        output_dir = VERCEL_OUT if os.environ.get("VERCEL") else None
        refresh_pipeline(output_dir)
        out_dir = output_dir if output_dir is not None else OUT
        response = jsonify({
            "cleaned": csv_json(out_dir / "cleaned_data.csv"),
            "priority": csv_json(out_dir / "intervention_priority.csv"),
            "upload_limit_bytes": upload_limit_bytes(),
        })
        response.headers["Cache-Control"] = "no-store"
        return response
    except Exception as error:
        app.logger.exception("Dashboard refresh failed")
        return jsonify({"error": str(error)}), HTTPStatus.INTERNAL_SERVER_ERROR


@app.get("/api/cpcb")
def api_cpcb():
    try:
        response = jsonify(get_station_data(
            request.args.get("city", ""), request.args.get("state", "")
        ))
        response.headers["Cache-Control"] = "no-store"
        return response
    except ValueError as error:
        return jsonify({"error": str(error)}), HTTPStatus.BAD_REQUEST
    except CPCBError as error:
        return jsonify({"error": str(error)}), HTTPStatus.SERVICE_UNAVAILABLE


@app.post("/api/upload")
def api_upload():
    origin = request.headers.get("Origin")
    if origin and origin not in {f"http://{request.host}", f"https://{request.host}"}:
        return jsonify({"error": "Cross-origin uploads are not allowed."}), HTTPStatus.FORBIDDEN

    try:
        length = request.content_length
        if length is None or length <= 0 or length > upload_limit_bytes():
            raise ValueError(upload_limit_message())
        name = Path(
            unquote(request.headers.get("X-File-Name", "")).replace("\\", "/")
        ).name
        content = request.get_data(cache=False)
        if len(content) != length:
            raise ValueError("The upload was incomplete.")
        return jsonify(analyze_upload(name, content, request.args.to_dict(flat=True)))
    except (ValueError, UnicodeDecodeError, pd.errors.ParserError, BadZipFile) as error:
        return jsonify({"error": str(error)}), HTTPStatus.BAD_REQUEST
    except Exception:
        app.logger.exception("Upload failed")
        return jsonify({"error": "Could not process the uploaded file."}), HTTPStatus.INTERNAL_SERVER_ERROR


if __name__ == "__main__":
    print(f"Dashboard running at http://localhost:{PORT}")
    print("Watching data/raw for changes. Press Ctrl+C to stop.")
    server = ThreadingHTTPServer(("localhost", PORT), DashboardHandler)
    server.serve_forever()
