import http.server
import json
import os
import sys
import urllib.parse
from pipeline import BiomedicalPipeline

from disease_normalizer.suggester import get_disease_suggestions
from compound_retriever import NaturalCompoundRetriever

# Base directory for static files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Singleton pipeline instance for reuse
_pipeline = None
_compound_retriever = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = BiomedicalPipeline()
    return _pipeline


def get_compound_retriever():
    global _compound_retriever
    if _compound_retriever is None:
        _compound_retriever = NaturalCompoundRetriever(
            max_route_a_papers=30,
            max_route_b_activities=200,
            max_route_b_papers=10,
        )
    return _compound_retriever


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

        if path == "/api/compounds":
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
                    self.wfile.write(json.dumps({"status": "error", "message": "Disease name cannot be empty"}).encode("utf-8"))
                    return

                targets = payload.get("targets", [])
                synonyms = payload.get("synonyms", [])

                retriever = get_compound_retriever()
                result = retriever.retrieve(
                    disease_name=disease,
                    targets=targets,
                    disease_synonyms=synonyms,
                )

                # Serialize to JSON-friendly dict
                def compound_to_dict(c):
                    return {
                        "compound_id": c.compound_id,
                        "name": c.name,
                        "synonyms": c.synonyms,
                        "smiles": c.smiles,
                        "inchikey": c.inchikey,
                        "pubchem_cid": c.pubchem_cid,
                        "chembl_id": c.chembl_id,
                        "natural_origin": c.natural_origin,
                        "natural_origin_source": c.natural_origin_source,
                        "natural_product_class": c.natural_product_class,
                        "retrieval_routes": c.retrieval_routes,
                        "targets_targeted": c.targets_targeted,
                        "evidence_sources": c.evidence_sources,
                        "citation_count": c.citation_count,
                        "best_bioactivity_nM": c.best_bioactivity_nM,
                        "is_dual_route": (
                            "disease_natural_literature" in c.retrieval_routes
                            and ("protein_chembl_bioactivity" in c.retrieval_routes or "protein_literature" in c.retrieval_routes)
                        ),
                        "target_relations": [
                            {
                                "target_symbol": tr.target_symbol,
                                "target_name": tr.target_name,
                                "relation_type": tr.relation_type,
                                "best_potency_nM": tr.best_potency_nM,
                                "pmids": tr.pmids,
                                "evidence_snippets": tr.evidence_snippets[:3],
                                "source": tr.source,
                            }
                            for tr in c.target_relations
                        ],
                        "provenance": {
                            "pmids": c.provenance.get("pmids", [])[:10],
                            "snippets": c.provenance.get("snippets", [])[:5],
                        },
                    }

                output = {
                    "status": "success",
                    "disease_name": result.disease_name,
                    "targets_queried": result.targets_queried,
                    "total_compounds": result.total_compounds,
                    "route_a_count": result.route_a_count,
                    "route_b_count": result.route_b_count,
                    "dual_route_count": result.dual_route_count,
                    "compounds": [compound_to_dict(c) for c in result.compounds],
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(output).encode("utf-8"))
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
