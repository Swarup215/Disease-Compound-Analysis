import http.server
import json
import os
import sys
import urllib.parse
from pipeline import BiomedicalPipeline

from disease_normalizer.suggester import get_disease_suggestions
from compound_retriever import NaturalCompoundRetriever
from compound_verifier import CompoundVerifier

# Base directory for static files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Singleton pipeline instances for reuse
_pipeline = None
_compound_retriever = None
_compound_verifier = None


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


def get_compound_verifier():
    global _compound_verifier
    if _compound_verifier is None:
        _compound_verifier = CompoundVerifier(timeout=15, enable_pubchem=True)
    return _compound_verifier


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

                # Step 6: Candidate Retrieval
                retriever = get_compound_retriever()
                result = retriever.retrieve(
                    disease_name=disease,
                    targets=targets,
                    disease_synonyms=synonyms,
                )

                # Step 7: Identity & Natural-Origin Verification
                verifier = get_compound_verifier()
                verified_batch = verifier.verify_batch(
                    candidates=result.compounds,
                    disease_name=disease
                )

                # Serialize verified compounds to JSON-friendly dict
                def verified_compound_to_dict(vc):
                    return {
                        "compound_id": vc.compound_id,
                        "name": vc.name,
                        "pubchem_cid": vc.identity.pubchem_cid,
                        "inchikey": vc.identity.inchikey,
                        "smiles": vc.identity.canonical_smiles,
                        "canonical_smiles": vc.identity.canonical_smiles,
                        "isomeric_smiles": vc.identity.isomeric_smiles,
                        "iupac_name": vc.identity.iupac_name,
                        "molecular_formula": vc.identity.molecular_formula,
                        "molecular_weight": vc.identity.molecular_weight,
                        "synonyms": vc.identity.synonyms,
                        "natural_origin": vc.natural_verification.is_natural,
                        "natural_origin_status": vc.natural_verification.status.value,
                        "natural_origin_confidence": vc.natural_verification.confidence,
                        "natural_product_class": vc.natural_verification.natural_product_class,
                        "subclass": vc.natural_verification.subclass,
                        "determination_method": vc.natural_verification.determination_method,
                        "notes": vc.natural_verification.notes,
                        "retrieval_routes": vc.retrieval_routes,
                        "targets_targeted": vc.targets_targeted,
                        "evidence_sources": vc.evidence_sources,
                        "citation_count": vc.citation_count,
                        "best_bioactivity_nM": vc.best_bioactivity_nM,
                        "is_dual_route": vc.is_dual_route,
                        "target_relations": [
                            {
                                "target_symbol": getattr(tr, "target_symbol", ""),
                                "target_name": getattr(tr, "target_name", ""),
                                "relation_type": getattr(tr, "relation_type", "active_against"),
                                "best_potency_nM": getattr(tr, "best_potency_nM", None),
                                "pmids": getattr(tr, "pmids", []),
                                "evidence_snippets": getattr(tr, "evidence_snippets", [])[:3],
                                "source": getattr(tr, "source", "ChEMBL"),
                            }
                            for tr in vc.target_relations
                        ],
                        "provenance": {
                            "pmids": vc.provenance.get("pmids", [])[:10],
                            "snippets": vc.provenance.get("snippets", [])[:5],
                            "verification": vc.provenance.get("verification", {}),
                        },
                    }

                output = {
                    "status": "success",
                    "disease_name": result.disease_name,
                    "targets_queried": result.targets_queried,
                    "total_compounds": verified_batch.total_candidates,
                    "verified_natural_count": verified_batch.verified_natural_count,
                    "natural_derivative_count": verified_batch.natural_derivative_count,
                    "synthetic_count": verified_batch.synthetic_count,
                    "unverified_count": verified_batch.unverified_count,
                    "route_a_count": result.route_a_count,
                    "route_b_count": result.route_b_count,
                    "dual_route_count": result.dual_route_count,
                    "compounds": [verified_compound_to_dict(c) for c in verified_batch.compounds],
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

        if path == "/api/compounds/verify":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode("utf-8"))
                raw_compounds = payload.get("compounds", [])
                candidates = []
                for item in raw_compounds:
                    if isinstance(item, str):
                        candidates.append({"name": item})
                    elif isinstance(item, dict):
                        candidates.append(item)

                verifier = get_compound_verifier()
                verified_batch = verifier.verify_batch(candidates=candidates)

                compounds_data = []
                for vc in verified_batch.compounds:
                    compounds_data.append({
                        "compound_id": vc.compound_id,
                        "name": vc.name,
                        "pubchem_cid": vc.identity.pubchem_cid,
                        "inchikey": vc.identity.inchikey,
                        "canonical_smiles": vc.identity.canonical_smiles,
                        "iupac_name": vc.identity.iupac_name,
                        "molecular_formula": vc.identity.molecular_formula,
                        "molecular_weight": vc.identity.molecular_weight,
                        "synonyms": vc.identity.synonyms[:10],
                        "natural_origin_status": vc.natural_verification.status.value,
                        "is_natural": vc.natural_verification.is_natural,
                        "confidence": vc.natural_verification.confidence,
                        "natural_product_class": vc.natural_verification.natural_product_class,
                        "subclass": vc.natural_verification.subclass,
                        "determination_method": vc.natural_verification.determination_method,
                        "notes": vc.natural_verification.notes,
                        "provenance": vc.provenance,
                    })

                resp = {
                    "status": "success",
                    "total_candidates": verified_batch.total_candidates,
                    "verified_natural_count": verified_batch.verified_natural_count,
                    "natural_derivative_count": verified_batch.natural_derivative_count,
                    "synthetic_count": verified_batch.synthetic_count,
                    "unverified_count": verified_batch.unverified_count,
                    "compounds": compounds_data,
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(resp).encode("utf-8"))
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
