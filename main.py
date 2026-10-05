import argparse
import json
import sys
from pipeline import BiomedicalPipeline

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def print_cli_summary(result: dict):
    print("\n" + "=" * 80)
    print("BIOMEDICAL AI — TARGET PRIORITIZATION REPORT")
    print("=" * 80)
    
    disease = result.get("disease", {})
    metrics = result.get("metrics", {})
    targets = result.get("targets", [])

    print(f"\nDisease Input:        {disease.get('input')}")
    print(f"Canonical Concept:    {disease.get('canonical_name')} (ID: {disease.get('canonical_id')})")
    print(f"Ontology Mapping:     MONDO: {disease.get('identifiers', {}).get('mondo')} | EFO: {disease.get('identifiers', {}).get('efo')} | DOID: {disease.get('identifiers', {}).get('doid')}")
    print(f"Total Proteins Found: {metrics.get('total_targets_found')} (Analyzed: {metrics.get('analyzed_targets')})")
    print(f"Literature Reviewed:  {metrics.get('total_unique_papers')} papers | {metrics.get('total_evidence_extracted')} evidence claims extracted")
    print(f"Execution Time:       {result.get('elapsed_seconds')} seconds")

    print("\n" + "-" * 80)
    print(f"{'RANK':<5} {'SYMBOL':<10} {'FUSED':<8} {'STRUCT':<8} {'LIT':<8} {'EVID':<6} {'STATUS':<15} {'NAME'}")
    print("-" * 80)

    for t in targets:
        print(f"#{t['rank']:<4} {t['target_symbol']:<10} {t['fused_score']:<8.4f} {t['structured_score']:<8.4f} {t['literature_score']:<8.4f} {t['evidence_count']:<6} {t['literature_status']:<15} {t['target_name'][:30]}")

    print("\n" + "=" * 80)
    print("WHERE LITERATURE EVIDENCE IS FOUND (DETAILED CITATIONS)")
    print("=" * 80)

    for t in targets:
        print(f"\nTarget #{t['rank']}: {t['target_symbol']} ({t['target_name']}) — Fused Score: {t['fused_score']:.4f}")
        if not t.get("evidence_items"):
            print("   (No direct literature evidence extracted for this target)")
            continue

        for i, ev in enumerate(t["evidence_items"], 1):
            print(f"   [{i}] PMID: {ev['pmid']} — {ev.get('title') or 'PubMed Article'}")
            print(f"       Source Link:  {ev['pubmed_url']}")
            print(f"       Journal/Date: {ev.get('journal') or 'N/A'} ({ev.get('publication_date') or 'N/A'})")
            print(f"       Type/Relation:{ev['evidence_type']} | {ev['relation']} | Strength: {ev['evidence_strength']} | Direction: {ev['direction']}")
            print(f"       Confidence:   {ev['confidence']:.2f}")
            print(f"       Evidence:     \"{ev['evidence_text']}\"")
            print()


def main():
    parser = argparse.ArgumentParser(description="Biomedical AI - Disease Target Prioritization & Evidence Fusion Pipeline")
    parser.add_argument("--disease", type=str, default=None, help="Disease query name or ontology ID (e.g., 'Type 2 diabetes')")
    parser.add_argument("--targets", type=int, default=10, help="Number of candidate protein targets to retrieve (default: 10)")
    parser.add_argument("--papers", type=int, default=3, help="Number of literature papers per target to review (default: 3)")
    parser.add_argument("--min-score", type=float, default=0.40, help="Minimum Open Targets association score (default: 0.40)")
    parser.add_argument("--struct-weight", type=float, default=0.60, help="Structured evidence weight (default: 0.60)")
    parser.add_argument("--lit-weight", type=float, default=0.40, help="Literature evidence weight (default: 0.40)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format")
    parser.add_argument("--server", action="store_true", help="Launch the Web UI Frontend and HTTP server")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")

    args = parser.parse_args()

    if args.server or (args.disease is None and len(sys.argv) == 1):
        from server import start_server
        print(f"Starting Biomedical AI Web Application on http://localhost:{args.port} ...")
        start_server(port=args.port)
        return

    if not args.disease:
        print("Error: Please provide a disease using --disease \"Disease Name\" or launch the Web UI with --server")
        sys.exit(1)

    print(f"Running Biomedical AI Pipeline for '{args.disease}'...")
    pipeline = BiomedicalPipeline()
    result = pipeline.run(
        disease_query=args.disease,
        target_limit=args.targets,
        papers_per_target=args.papers,
        min_score=args.min_score,
        structured_weight=args.struct_weight,
        literature_weight=args.lit_weight,
        progress_callback=lambda stage, pct, _: print(f"[{pct:3d}%] {stage}")
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_cli_summary(result)


if __name__ == "__main__":
    main()
