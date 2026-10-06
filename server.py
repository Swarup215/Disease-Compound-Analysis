import http.server
import json
import os
import sys
import urllib.parse
from pipeline import BiomedicalPipeline

from disease_normalizer.suggester import get_disease_suggestions

# Base directory for static files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Singleton pipeline instance for reuse
_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = BiomedicalPipeline()
    return _pipeline


class BiomedicalHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy", "service": "Biomedical AI Pipeline"}).encode("utf-8"))
            return

        if path == "/api/suggest":
            query_params = urllib.parse.parse_qs(parsed.query)
            q = query_params.get("q", [""])[0].strip()
            suggestions = get_disease_suggestions(q, limit=8) if q else []
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "query": q, "suggestions": suggestions}).encode("utf-8"))
            return

        # Default static file handling
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/suggest":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode("utf-8"))
                q = payload.get("query", "").strip()
                suggestions = get_disease_suggestions(q, limit=8) if q else []
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "query": q, "suggestions": suggestions}).encode("utf-8"))
            except Exception as exc:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(exc)}).encode("utf-8"))
            return

        if path == "/api/analyze":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)

            try:
                payload = json.loads(post_data.decode("utf-8"))
                disease = payload.get("disease", "").strip()
                if not disease:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "status": "error",
                        "message": "Disease name cannot be empty"
                    }).encode("utf-8"))
                    return

                target_limit = int(payload.get("target_limit", 10))
                papers_per_target = int(payload.get("papers_per_target", 3))
                min_score = float(payload.get("min_score", 0.40))
                structured_weight = float(payload.get("structured_weight", 0.60))
                literature_weight = float(payload.get("literature_weight", 0.40))

                pipeline = get_pipeline()
                result = pipeline.run(
                    disease_query=disease,
                    target_limit=target_limit,
                    papers_per_target=papers_per_target,
                    min_score=min_score,
                    structured_weight=structured_weight,
                    literature_weight=literature_weight
                )

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))

            except ValueError as exc:
                suggestions = getattr(exc, "suggestions", [])
                if not suggestions and 'disease' in locals() and disease:
                    suggestions = get_disease_suggestions(disease)
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "unresolved_disease",
                    "message": str(exc),
                    "query": disease if 'disease' in locals() else "",
                    "suggestions": suggestions
                }).encode("utf-8"))
            except Exception as exc:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(exc)}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()


def start_server(port: int = 8000):
    os.makedirs(FRONTEND_DIR, exist_ok=True)
    server_address = ("", port)
    httpd = http.server.ThreadingHTTPServer(server_address, BiomedicalHTTPRequestHandler)
    print(f"Biomedical AI Server running on http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()


if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    start_server(port)
