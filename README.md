# Biomedical AI

A modular biomedical evidence pipeline for disease normalization, structured target retrieval, literature retrieval, evidence extraction, evidence graphs, evidence fusion, and target prioritization.

## Components

- `disease_normalizer/` - Normalizes disease names and resolves ontology identifiers.
- `structured_retriever/` - Retrieves disease-target associations from structured sources such as Open Targets.
- `literature_retriever/` - Builds literature queries and harvests scientific literature across PubMed, EMBL-EBI Europe PMC, and Open Targets.
- `biomedical_rag/` - Processes, chunks, embeds, stores, retrieves, and reranks literature evidence.
- `evidence_extractor/` - Extracts structured evidence from retrieved text.
- `evidence_graph/` - Represents diseases, targets, papers, and evidence relationships.
- `evidence_fusion/` - Combines structured and literature evidence into a fused score.
- `target_prioritization/` - Sorts fused target results and selects the top candidates without creating a new biological score.

## Setup

Create and activate a virtual environment, then install the dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Running Tests

The repository includes standalone component and integration scripts. Run an individual test with:

```powershell
python test_target_prioritization.py
```

The target prioritization test should rank the sample targets by fused score:

1. KCNJ11
2. ABCC8
3. GCK

Other available checks include:

```powershell
python test_disease_normalizer.py
python test_evidence_extractor.py
python test_evidence_fusion.py
python test_evidence_fusion_graph.py
python test_evidence_graph.py
python test_literature_retriever_unit.py
python test_query_builder_unit.py
python test_rag_pipeline.py
python test_structured_retriever_unit.py
```

The integration test may call external services and can require network access:

```powershell
python test_evidence_fusion_integration.py
```

## Target Prioritization

Evidence Fusion calculates the combined score for each target. Target Prioritization then sorts those existing fusion results and returns the requested number of highest-scoring candidates.

```python
from target_prioritization import TargetPrioritizer

result = TargetPrioritizer().prioritize(
    fusion_results=fusion_results,
    top_n=10
)
```

The prioritizer rejects empty fusion results and non-positive `top_n` values. It is currently available as an isolated component and is not integrated into the full pipeline.
