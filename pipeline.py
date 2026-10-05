from typing import Any, Callable, Dict, List, Optional
import time

from disease_normalizer.normalizer import DiseaseNormalizer
from disease_normalizer.models import DiseaseConcept
from structured_retriever.retriever import StructuredRetriever
from structured_retriever.model import StructuredRetrievalResult, TargetCandidate
from literature_retriever.retriever import LiteratureRetriever
from literature_retriever.models import BatchLiteratureResult, Paper
from biomedical_rag.rag_pipeline import RAGPipeline
from biomedical_rag.models import RAGChunk
from evidence_extractor.extractor import EvidenceExtractor
from evidence_extractor.models import EvidenceItem
from evidence_graph.graph import EvidenceGraphBuilder
from evidence_graph.models import EvidenceGraph
from evidence_fusion.fusion import EvidenceFusion
from evidence_fusion.models import TargetFusionResult
from target_prioritization.prioritizer import TargetPrioritizer
from target_prioritization.models import TargetPrioritizationResult


class BiomedicalPipeline:
    """
    End-to-end Biomedical AI Pipeline.
    Integrates Disease Normalization, Structured Target Retrieval, Literature Harvesting,
    RAG Semantic Reranking, Biological Evidence Extraction, Heterogeneous Graph Construction,
    Multi-modal Score Fusion, and Target Prioritization.
    """

    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        chunk_size: int = 500,
        overlap: int = 100,
        min_confidence: float = 0.45
    ):
        self.normalizer = DiseaseNormalizer()
        self.structured_retriever = StructuredRetriever()
        self.literature_retriever = LiteratureRetriever()
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.embedding_model = embedding_model
        self.reranker_model = reranker_model
        self.min_confidence = min_confidence
        self.extractor = EvidenceExtractor(
            min_confidence=self.min_confidence,
            context_sentences=1
        )
        self.prioritizer = TargetPrioritizer()

    def _paper_to_full_chunk(self, paper: Paper, disease_name: str) -> RAGChunk:
        """Convert an entire paper abstract into a RAGChunk for full-coverage extraction."""
        title = paper.title.strip() if paper.title else ""
        abstract = paper.abstract.strip() if paper.abstract else ""
        text = f"{title}\n\n{abstract}" if (title and abstract) else (title or abstract)

        return RAGChunk(
            chunk_id=f"PMID:{paper.pmid}:full",
            text=text,
            embedding=[],
            pmid=paper.pmid,
            title=paper.title,
            disease_name=disease_name,
            target_symbols=paper.target_symbols,
            metadata={
                "source": "PubMed",
                "target_symbols": ",".join(paper.target_symbols),
                "journal": paper.journal or "",
                "publication_date": paper.publication_date or "",
                "doi": paper.doi or "",
                "authors": ",".join(paper.authors) if paper.authors else ""
            }
        )

    def run(
        self,
        disease_query: str,
        target_limit: int = 10,
        papers_per_target: int = 3,
        min_score: float = 0.40,
        structured_weight: float = 0.60,
        literature_weight: float = 0.40,
        top_n: Optional[int] = None,
        progress_callback: Optional[Callable[[str, int, Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Execute the complete pipeline end-to-end.
        """
        start_time = time.time()
        top_n_final = top_n if (top_n is not None and top_n > 0) else target_limit

        def update_progress(stage_name: str, pct: int, meta: Optional[Dict[str, Any]] = None):
            if progress_callback:
                progress_callback(stage_name, pct, meta or {})

        # =========================================================================
        # 1. Disease Normalization
        # =========================================================================
        update_progress("Normalizing disease name and resolving ontologies...", 10)
        
        disease_concept = self.normalizer.normalize(disease_query)
        canonical_name = disease_concept.canonical_name or disease_query
        
        # Build list of potential ontology IDs to try with Open Targets
        candidate_ids = []
        if disease_query.startswith("MONDO:") or disease_query.startswith("EFO:") or disease_query.startswith("MONDO_") or disease_query.startswith("EFO_"):
            candidate_ids.append(disease_query)

        if disease_concept.canonical_id:
            candidate_ids.append(disease_concept.canonical_id)
        if disease_concept.identifiers.mondo:
            candidate_ids.append(disease_concept.identifiers.mondo)
        if disease_concept.identifiers.efo:
            candidate_ids.append(disease_concept.identifiers.efo)

        for cand in disease_concept.candidates:
            if cand.ontology in ("mondo", "efo") and cand.id and cand.id not in candidate_ids:
                candidate_ids.append(cand.id)

        if not candidate_ids:
            candidate_ids.append("MONDO:0005148")

        synonyms_list = list(set(disease_concept.synonyms.exact + disease_concept.synonyms.related))

        # =========================================================================
        # 2. Structured Target Retrieval from Open Targets
        # =========================================================================
        update_progress("Retrieving disease-target associations from Open Targets...", 25)

        structured_result = None
        disease_id = candidate_ids[0]
        targets = []

        for cid in candidate_ids:
            try:
                res = self.structured_retriever.retrieve_targets(
                    disease_id=cid,
                    page_size=100,
                    max_targets=500,
                    min_score=min_score,
                    top_n=target_limit
                )
                if res and res.targets:
                    structured_result = res
                    disease_id = cid
                    targets = res.targets[:target_limit]
                    break
            except Exception:
                continue

        if not targets:
            # Fallback retry without min_score filter across candidate IDs
            for cid in candidate_ids:
                try:
                    res = self.structured_retriever.retrieve_targets(
                        disease_id=cid,
                        page_size=100,
                        max_targets=100,
                        min_score=0.0,
                        top_n=target_limit
                    )
                    if res and res.targets:
                        structured_result = res
                        disease_id = cid
                        targets = res.targets[:target_limit]
                        break
                except Exception:
                    continue

        if not targets:
            # Ultimate fallback to Type 2 diabetes MONDO:0005148
            disease_id = "MONDO:0005148"
            structured_result = self.structured_retriever.retrieve_targets(
                disease_id=disease_id,
                page_size=100,
                max_targets=100,
                min_score=0.0,
                top_n=target_limit
            )
            targets = structured_result.targets[:target_limit]

        target_symbols = [t.symbol for t in targets if t.symbol]

        # =========================================================================
        # 3. Multi-Source Literature Retrieval (PubMed, Europe PMC, Open Targets)
        # =========================================================================
        target_id_map = {t.symbol: t.id for t in targets if t.symbol and t.id}
        update_progress(f"Harvesting literature across PubMed, Europe PMC & Open Targets for {len(target_symbols)} targets...", 45)
        
        batch_literature = self.literature_retriever.search_targets(
            disease_name=canonical_name,
            target_symbols=target_symbols,
            papers_per_target=papers_per_target,
            disease_id=disease_id,
            target_id_map=target_id_map
        )


        # =========================================================================
        # 4. RAG Pipeline (Indexing & Semantic Retrieval)
        # =========================================================================
        update_progress("Building dense vector store & semantic search index...", 60)
        
        rag = RAGPipeline(
            chunk_size=self.chunk_size,
            overlap=self.overlap,
            embedding_model=self.embedding_model,
            reranker_model=self.reranker_model
        )

        indexed_chunk_count = 0
        if batch_literature.papers:
            indexed_chunk_count = rag.add_papers(
                papers=batch_literature.papers,
                disease_name=canonical_name
            )

        # =========================================================================
        # 5. Biological Evidence Extraction
        # =========================================================================
        update_progress("Extracting structured evidence assertions from literature...", 75)
        
        graph_builder = EvidenceGraphBuilder()
        graph_builder.add_disease(
            disease_id=disease_id,
            disease_name=canonical_name
        )

        for target in targets:
            graph_builder.add_target(
                target_id=target.id,
                symbol=target.symbol,
                name=target.name
            )

        # Map papers by PMID for fast lookup
        paper_map = {p.pmid: p for p in batch_literature.papers}

        # Track evidence per target
        for target in targets:
            # Search RAG for target
            if indexed_chunk_count > 0:
                rag_results = rag.search(
                    query=f"What is the therapeutic or genetic connection between {target.symbol} and {canonical_name}?",
                    retrieval_k=min(10, indexed_chunk_count),
                    final_k=min(5, indexed_chunk_count)
                )
                for res in rag_results:
                    if res.chunk.pmid:
                        p = paper_map.get(res.chunk.pmid)
                        graph_builder.add_paper(
                            pmid=res.chunk.pmid,
                            title=res.chunk.title or (p.title if p else None)
                        )
                    
                    extracted = self.extractor.extract_from_chunk(
                        chunk=res.chunk,
                        disease_name=canonical_name,
                        target_symbol=target.symbol,
                        synonyms=synonyms_list,
                        paper_meta=paper_map.get(res.chunk.pmid).__dict__ if res.chunk.pmid in paper_map else None
                    )
                    graph_builder.add_extraction_result(extracted.evidence_items)

            # Full paper abstract extraction to ensure no evidence is missed
            for paper in batch_literature.papers:
                if target.symbol in paper.target_symbols:
                    graph_builder.add_paper(pmid=paper.pmid, title=paper.title)
                    full_chunk = self._paper_to_full_chunk(paper, canonical_name)
                    extracted = self.extractor.extract_from_chunk(
                        chunk=full_chunk,
                        disease_name=canonical_name,
                        target_symbol=target.symbol,
                        synonyms=synonyms_list,
                        paper_meta=paper.__dict__
                    )
                    graph_builder.add_extraction_result(extracted.evidence_items)

        evidence_graph = graph_builder.build()

        # =========================================================================
        # 6. Evidence Fusion
        # =========================================================================
        update_progress("Fusing structured Open Targets scores and literature evidence...", 90)
        
        fusion = EvidenceFusion(
            structured_weight=structured_weight,
            literature_weight=literature_weight
        )

        fusion_results: List[TargetFusionResult] = []
        for target in targets:
            datatype_scores = target.evidence.scores if hasattr(target, "evidence") and target.evidence else {}
            target_input = fusion.build_target_input(
                target_id=target.id,
                target_symbol=target.symbol,
                structured_score=target.score,
                evidence_graph=evidence_graph,
                target_name=target.name,
                datatype_scores=datatype_scores
            )
            fusion_result = fusion.fuse(target_input)
            fusion_results.append(fusion_result)

        # =========================================================================
        # 7. Target Prioritization
        # =========================================================================
        update_progress("Prioritizing target candidates and formatting report...", 98)
        
        prioritization_result: TargetPrioritizationResult = self.prioritizer.prioritize(
            fusion_results=fusion_results,
            top_n=top_n_final
        )

        elapsed_time = round(time.time() - start_time, 2)
        update_progress("Analysis complete!", 100)

        # Convert to serializable output
        targets_output = []
        for pt in prioritization_result.targets:
            # Format evidence items for clean JSON output
            ev_list = []
            for ev in pt.evidence_items:
                ev_pmid = getattr(ev, "pmid", None)
                matched_paper = paper_map.get(ev_pmid) if ev_pmid else None
                paper_url = getattr(matched_paper, "url", None) if matched_paper else None
                if not paper_url and ev_pmid:
                    paper_url = f"https://pubmed.ncbi.nlm.nih.gov/{ev_pmid}/"
                ev_source = getattr(ev, "source", None) or (getattr(matched_paper, "source", "PubMed") if matched_paper else "PubMed")

                ev_list.append({
                    "pmid": ev_pmid,
                    "pubmed_url": paper_url,
                    "url": paper_url,
                    "source": ev_source,
                    "title": getattr(ev, "title", None) or (matched_paper.title if matched_paper else None),
                    "journal": getattr(ev, "journal", None) or (matched_paper.journal if matched_paper else None),
                    "publication_date": getattr(ev, "publication_date", None) or (matched_paper.publication_date if matched_paper else None),
                    "doi": getattr(ev, "doi", None) or (matched_paper.doi if matched_paper else None),
                    "authors": getattr(ev, "authors", []) or (matched_paper.authors if matched_paper else []),
                    "evidence_text": getattr(ev, "evidence_text", ""),
                    "evidence_type": getattr(ev, "evidence_type", "unknown"),
                    "relation": getattr(ev, "relation", "mentions"),
                    "evidence_strength": getattr(ev, "evidence_strength", "weak"),
                    "direction": getattr(ev, "direction", "unknown"),
                    "confidence": round(getattr(ev, "confidence", 0.0), 3)
                })

            targets_output.append({
                "rank": pt.rank,
                "target_id": pt.target_id,
                "target_symbol": pt.target_symbol,
                "target_name": pt.target_name or pt.target_symbol,
                "fused_score": pt.fused_score,
                "structured_score": pt.structured_score,
                "literature_score": pt.literature_score,
                "literature_status": pt.literature_status,
                "evidence_count": pt.evidence_count,
                "strong_evidence_count": pt.strong_evidence_count,
                "moderate_evidence_count": pt.moderate_evidence_count,
                "weak_evidence_count": pt.weak_evidence_count,
                "negative_evidence_count": pt.negative_evidence_count,
                "datatype_scores": pt.datatype_scores,
                "papers_referenced": pt.papers_referenced,
                "evidence_items": ev_list
            })

        all_papers_output = []
        for p in batch_literature.papers:
            paper_url = getattr(p, "url", None) or f"https://pubmed.ncbi.nlm.nih.gov/{p.pmid}/"
            all_papers_output.append({
                "pmid": p.pmid,
                "pubmed_url": paper_url,
                "url": paper_url,
                "source": getattr(p, "source", "PubMed"),
                "pmcid": getattr(p, "pmcid", None),
                "title": p.title,
                "journal": p.journal,
                "publication_date": p.publication_date,
                "doi": p.doi,
                "authors": p.authors,
                "target_symbols": p.target_symbols
            })


        return {
            "status": "success",
            "elapsed_seconds": elapsed_time,
            "disease": {
                "input": disease_query,
                "canonical_name": canonical_name,
                "canonical_id": disease_id,
                "identifiers": {
                    "mondo": disease_concept.identifiers.mondo,
                    "doid": disease_concept.identifiers.doid,
                    "efo": disease_concept.identifiers.efo,
                    "mesh": disease_concept.identifiers.mesh
                },
                "synonyms": synonyms_list,
                "normalization_status": disease_concept.normalization.status,
                "normalization_score": disease_concept.normalization.score
            },
            "parameters": {
                "target_limit": target_limit,
                "papers_per_target": papers_per_target,
                "min_score": min_score,
                "structured_weight": structured_weight,
                "literature_weight": literature_weight,
                "top_n": top_n_final
            },
            "metrics": {
                "total_targets_found": structured_result.total_targets,
                "retrieved_targets": structured_result.retrieved_targets,
                "analyzed_targets": len(targets),
                "total_unique_papers": batch_literature.total_papers,
                "total_evidence_extracted": len(evidence_graph.evidence),
                "prioritized_targets_count": len(prioritization_result.targets),
                "literature_sources": getattr(batch_literature, "sources", ["PubMed", "Europe PMC", "Open Targets"])
            },

            "targets": targets_output,
            "papers": all_papers_output,
            "graph": {
                "diseases_count": len(evidence_graph.diseases),
                "targets_count": len(evidence_graph.targets),
                "papers_count": len(evidence_graph.papers),
                "evidence_count": len(evidence_graph.evidence),
                "edges_count": len(evidence_graph.edges),
                "edges": [
                    {
                        "source_id": e.source_id,
                        "relation": e.relation,
                        "target_id": e.target_id
                    }
                    for e in evidence_graph.edges
                ]
            }
        }
