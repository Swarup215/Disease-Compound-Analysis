import http.server
import json
import os
import sys
import urllib.parse
# Base directory for static files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Singleton pipeline instance for reuse
_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        from pipeline import BiomedicalPipeline
        _pipeline = BiomedicalPipeline()
    return _pipeline


class BiomedicalHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, code: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            self._send_json(200, {"status": "healthy", "service": "Biomedical AI Pipeline"})
            return

        if path == "/api/validate_disease":
            query_params = urllib.parse.parse_qs(parsed.query)
            disease = query_params.get("disease", [""])[0].strip()
            if not disease:
                self._send_json(400, {
                    "valid": False,
                    "message": "Cannot fetch: Disease name cannot be empty. Please enter a disease name."
                })
                return

            try:
                from disease_normalizer.normalizer import DiseaseNormalizer
                concept = DiseaseNormalizer().normalize(disease)

                candidate_ids = []
                if disease.startswith("MONDO:") or disease.startswith("EFO:") or disease.startswith("MONDO_") or disease.startswith("EFO_"):
                    candidate_ids.append(disease)
                if concept.canonical_id:
                    candidate_ids.append(concept.canonical_id)
                if concept.identifiers.mondo:
                    candidate_ids.append(concept.identifiers.mondo)
                if concept.identifiers.efo:
                    candidate_ids.append(concept.identifiers.efo)
                for cand in concept.candidates:
                    if getattr(cand, "score", 1.0) > 0.0 and cand.ontology in ("mondo", "efo") and cand.id and cand.id not in candidate_ids:
                        candidate_ids.append(cand.id)

                if not candidate_ids:
                    self._send_json(400, {
                        "valid": False,
                        "message": f"Could not recognize '{disease}'. Please enter a valid disease or disorder."
                    })
                    return

                self._send_json(200, {
                    "valid": True,
                    "canonical_name": concept.canonical_name or disease,
                    "candidate_ids": candidate_ids
                })
                return
            except Exception as exc:
                self._send_json(400, {
                    "valid": False,
                    "message": f"Could not recognize '{disease}'. Please enter a valid disease or disorder."
                })
                return

        # Default static file handling
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/analyze":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)

            try:
                payload = json.loads(post_data.decode("utf-8"))
                disease = payload.get("disease", "").strip()
                if not disease:
                    self._send_json(400, {"status": "error", "message": "Please enter a valid disease or disorder."})
                    return

                # Pre-validate before running expensive pipeline
                from disease_normalizer.normalizer import DiseaseNormalizer
                concept = DiseaseNormalizer().normalize(disease)
                candidate_ids = []
                if disease.startswith("MONDO:") or disease.startswith("EFO:") or disease.startswith("MONDO_") or disease.startswith("EFO_"):
                    candidate_ids.append(disease)
                if concept.canonical_id:
                    candidate_ids.append(concept.canonical_id)
                if concept.identifiers.mondo:
                    candidate_ids.append(concept.identifiers.mondo)
                if concept.identifiers.efo:
                    candidate_ids.append(concept.identifiers.efo)
                for cand in concept.candidates:
                    if getattr(cand, "score", 1.0) > 0.0 and cand.ontology in ("mondo", "efo") and cand.id and cand.id not in candidate_ids:
                        candidate_ids.append(cand.id)

                if not candidate_ids:
                    self._send_json(400, {
                        "status": "error",
                        "error_type": "invalid_disease",
                        "message": f"Could not recognize '{disease}'. Please enter a valid disease or disorder."
                    })
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

                self._send_json(200, result)

            except ValueError as exc:
                self._send_json(400, {"status": "error", "message": str(exc)})
            except Exception as exc:
                self._send_json(500, {"status": "error", "message": str(exc)})
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
