# Biomedical AI Disease–Target–Literature Pipeline

An evidence-driven biomedical AI pipeline that takes a disease as input, normalizes it to a standard biomedical concept, retrieves candidate protein targets, retrieves targeted literature, uses RAG to find relevant evidence, builds an evidence graph, fuses structured and literature evidence, and prioritizes candidate targets.

> **Current status:** Disease Normalization → Structured Target Retrieval → Literature Retrieval → Biomedical RAG → Evidence Extraction → Evidence Graph → Evidence Fusion → Target Prioritization are implemented and tested. Compound retrieval and downstream protein/compound AI pipelines are planned future stages.

---

## 1. Why This Architecture Was Changed

The initial approach relied heavily on broad disease literature retrieval using sources such as PubMed and Europe PMC.

For broad diseases such as diabetes, this can return extremely large numbers of papers.

The problem is therefore not simply:

> "How can we make the PubMed query better?"

The revised approach is:

```text
Disease
   ↓
Disease Normalization
   ↓
Structured Candidate Generation
   ↓
Target-specific Literature Retrieval
   ↓
RAG
   ↓
Evidence Extraction
   ↓
Evidence Graph
   ↓
Evidence Fusion
   ↓
Target Prioritization
```

The main idea is:

**Use structured biomedical sources to generate candidates first. Use literature to provide focused evidence about those candidates.**

---

# 2. Overall Architecture

```text
USER
  ↓
Disease Input
  ↓
Disease Normalization
  ↓
Canonical Disease ID
  ↓
Disease Knowledge / Association Layer
  ├── Open Targets
  ├── UniProt
  ├── ChEMBL / DrugBank
  └── Literature
  ↓
Entity Candidate Generation
  ↓
Literature Retrieval
  ↓
Biomedical RAG
  ├── Document Processing
  ├── Chunking
  ├── Embeddings
  ├── Vector Search
  └── Reranking
  ↓
Evidence Extraction
  ↓
Evidence Graph
  ↓
Evidence Fusion
  ↓
Target / Compound Prioritization
  ↓
Existing Protein / Compound AI Pipelines
  ↓
Docking
  ↓
Validation
  ↓
PPI
  ↓
Functional Analysis
  ↓
Results / Dashboard
```

The currently implemented pipeline reaches **Target Prioritization**.

---

# 3. Current Project Structure

```text
biomedical_ai/
│
├── test_disease_normalizer.py
├── test_structured_retriever.py
├── test_structured_retriever_unit.py
├── test_literature_retriever_unit.py
├── test_query_builder_unit.py
├── test_evidence_graph.py
├── test_evidence_fusion.py
├── test_evidence_fusion_graph.py
├── test_evidence_fusion_integration.py
└── test_target_prioritization.py
│
├── disease_normalizer/
│   ├── __init__.py
│   ├── models.py
│   ├── preprocess.py
│   ├── ols.py
│   ├── resolver.py
│   └── normalizer.py
│
├── structured_retriever/
│   ├── __init__.py
│   ├── models.py
│   ├── open_targets.py
│   └── retriever.py
│
├── literature_retriever/
│   ├── __init__.py
│   ├── models.py
│   ├── pubmed.py
│   ├── retriever.py
│   └── query_builder.py
│
├── biomedical_rag/
│   ├── __init__.py
│   ├── models.py
│   ├── document_processor.py
│   ├── chunker.py
│   ├── embedder.py
│   ├── vector_store.py
│   ├── retriever.py
│   ├── reranker.py
│   └── rag_pipeline.py
│
├── evidence_extractor/
│   ├── __init__.py
│   ├── models.py
│   ├── rules.py
│   └── extractor.py
│
├── evidence_graph/
│   ├── __init__.py
│   ├── models.py
│   └── graph.py
│
├── evidence_fusion/
│   ├── __init__.py
│   ├── models.py
│   └── fusion.py
│
└── target_prioritization/
    ├── __init__.py
    ├── models.py
    └── prioritizer.py
```

---

# 4. Stage 1 — Disease Normalization

## Goal

Convert the user's disease input into a standard biomedical disease concept.

For example:

```text
User input:
type 2 diabetes

        ↓

Canonical disease:
type 2 diabetes mellitus

        ↓

MONDO:
MONDO:0005148
```

The normalizer currently uses the Ontology Lookup Service (OLS) and supports:

- MONDO
- DOID
- EFO
- MeSH

## Example

```text
Input:
type 2 diabetes

Canonical name:
type 2 diabetes mellitus

Canonical ID:
MONDO:0005148

Status:
resolved

Match:
exact_synonym

Score:
0.95
```

Identifiers:

```text
MONDO:0005148
DOID:9352
EFO:0004997
MeSH:mesh:D003924
```

## Other tested diseases

```text
Alzheimer disease → MONDO:0004975
Parkinson disease → MONDO:0005180
asthma           → MONDO:0004979
breast cancer    → MONDO:0007254
diabetes         → ambiguous
IVDD              → currently no_match
```

### Current limitation

Abbreviations such as `IVDD` may be ambiguous.

The current system should eventually handle ambiguous abbreviations by presenting possible meanings or asking the user for clarification instead of silently selecting one.

---

# 5. Stage 2 — Structured Target Retrieval

## Goal

Generate candidate protein targets using structured disease–target associations before performing large literature searches.

The current implementation uses:

**Open Targets Platform**

API:

```text
https://api.platform.opentargets.org/api/v4/graphql
```

The Open Targets disease ID is converted from:

```text
MONDO:0005148
```

to:

```text
MONDO_0005148
```

when required by the API.

## Retrieval configuration

```python
page_size = 100
max_targets = 500
min_score = 0.60
top_n = 50
```

These values are configurable engineering parameters.

They are **not scientifically validated cutoffs**.

## Type 2 diabetes example

```text
Disease ID:
MONDO:0005148

Total associated targets:
10206

Retrieved:
500

Filtered / selected:
50
```

Leading targets included:

```text
KCNJ11
ABCC8
GCK
PPARG
HNF1A
HNF4A
HNF1B
INSR
GLP1R
WFS1
```

The Open Targets score is treated as one signal, not as the final biological truth.

---

# 6. Stage 3 — Literature Retrieval

## Goal

Retrieve literature specifically related to:

```text
Disease + Target
```

instead of retrieving all literature related to the disease.

Example:

```text
"type 2 diabetes mellitus" AND KCNJ11
```

## Query Builder

The query builder validates the disease and target and creates:

```text
"type 2 diabetes mellitus" AND KCNJ11
```

Empty disease or target values raise validation errors.

## PubMed

The implementation uses NCBI PubMed E-utilities.

The PubMed client can:

1. Search PubMed
2. Fetch article records
3. Parse PubMed XML
4. Extract:
   - PMID
   - title
   - abstract
   - journal
   - publication date
   - DOI
   - authors

Example observed search:

```text
Query:
"type 2 diabetes mellitus" AND KCNJ11

Total found:
128

Retrieved:
3
```

PubMed is a live database, so counts can change over time.

## Batch retrieval

Multiple targets can be searched together:

```text
Disease:
type 2 diabetes mellitus

Targets:
KCNJ11
ABCC8
GCK
```

Duplicate papers are removed across targets.

---

# 7. Stage 4 — Biomedical RAG

## Goal

Use semantic retrieval to find relevant parts of retrieved literature.

The RAG pipeline contains:

```text
Paper
 ↓
Document Processing
 ↓
Chunking
 ↓
Embedding
 ↓
Vector Store
 ↓
Semantic Retrieval
 ↓
Reranking
 ↓
Relevant Chunks
```

## Current models

### Embedding

```text
all-MiniLM-L6-v2
```

Embedding dimension:

```text
384
```

### Vector store

```text
FAISS IndexFlatL2
```

### Reranker

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

### Chunking

Default:

```text
chunk_size = 500
overlap = 100
```

The RAG pipeline was successfully tested.

---

# 8. Stage 5 — Evidence Extraction

## Goal

Convert relevant literature text into structured evidence.

Each extracted evidence item contains information such as:

```text
PMID
Disease
Target
Evidence text
Evidence type
Relation
Evidence strength
Direction
Confidence
Source
```

## Evidence types

Current rule categories include:

```text
genetic_association
gene_expression
protein_interaction
drug_target
animal_model
experimental
unknown
```

## Relations

Current relation categories include:

```text
associated_with
drug_target_of
experimental_association
no_association
mentions
```

## Evidence strength

Current engineering categories:

```text
strong
moderate
weak
```

Examples:

```text
genetic_association → strong
drug_target        → moderate
animal_model       → moderate
experimental       → moderate
gene_expression    → moderate
protein_interaction→ moderate
```

These are **engineering categories**, not scientifically validated evidence levels.

## Confidence

The current confidence calculation considers:

```text
Target present        +0.25
Disease present       +0.25
Evidence type         +0.20
Non-mentions relation +0.20
Direction             +0.10
```

Maximum:

```text
1.0
```

Evidence is also deduplicated using:

```text
PMID + target + evidence text
```

---

# 9. Stage 6 — Evidence Graph

## Goal

Create a structured graph connecting:

- Disease
- Target
- Paper
- Evidence

## Node types

```text
DiseaseNode
TargetNode
PaperNode
EvidenceNode
```

## Edge

```text
EvidenceEdge
```

Example:

```text
Disease
   |
   | associated_with
   ↓
KCNJ11
   |
   | supported_by
   ↓
Evidence
   |
   | reported_in
   ↓
PMID
```

## Example graph test

```text
Diseases: 1
Targets: 3
Papers: 5
Evidence: 3
Edges: 9
```

This graph becomes the structured source used by Evidence Fusion.

---

# 10. Stage 7 — Evidence Fusion

## Goal

Combine:

1. Structured Open Targets score
2. Literature evidence

into a single engineering score.

## Inputs

```text
structured_score
evidence_count
strong_evidence_count
moderate_evidence_count
weak_evidence_count
```

## Literature score

Current calculation:

```text
weighted_evidence =
    strong × 1.0
  + moderate × 0.6
  + weak × 0.3

literature_score =
    weighted_evidence / evidence_count
```

The result is capped at:

```text
1.0
```

## Fusion formula

Current weights:

```text
structured_weight = 0.6
literature_weight = 0.4
```

Therefore:

```text
fused_score =
    structured_score × 0.6
    +
    literature_score × 0.4
```

These weights are engineering choices and are **not scientifically validated**.

## Example

For KCNJ11:

```text
Structured score:
0.8772

Evidence:
2

Strong:
1

Moderate:
1

Literature score:
0.8

Fused score:
0.84632
```

---

# 11. Important Fusion Improvement

A major issue was identified:

```text
No evidence found
```

does **not** mean:

```text
Negative evidence
```

For example, if only two papers are searched for GCK and neither contains qualifying evidence, we cannot conclude that GCK has no biological evidence.

Therefore the fusion result now contains:

```text
literature_status
```

Possible values currently include:

```text
evidence_found
no_evidence
```

This lets the pipeline distinguish between:

```text
Evidence exists
```

and:

```text
No qualifying evidence was found in the current search
```

The scoring formula has not yet been changed based on this status.

---

# 12. Stage 8 — Real Evidence Fusion Integration

The complete real integration now works:

```text
Disease
 ↓
Open Targets
 ↓
Real target candidates
 ↓
PubMed
 ↓
RAG
 ↓
Evidence Extraction
 ↓
Evidence Graph
 ↓
Evidence Fusion
 ↓
Real fused scores
```

## Real test

```text
Total Open Targets associations:
10206

Targets used:
3

Unique papers:
5
```

Evidence graph:

```text
Diseases: 1
Targets: 3
Papers: 4
Evidence: 1
Edges: 3
```

Fusion:

```text
1. KCNJ11
   Open Targets: 0.8772
   Evidence count: 1
   Strong evidence: 1
   Literature score: 1.0000
   Fused score: 0.9263

2. ABCC8
   Open Targets: 0.8764
   Evidence count: 0
   Literature score: 0.0000
   Fused score: 0.5258

3. GCK
   Open Targets: 0.8680
   Evidence count: 0
   Literature score: 0.0000
   Fused score: 0.5208
```

### Interpretation

KCNJ11 receives the highest engineering score in this test because it has both:

```text
High structured association score
+
Qualifying literature evidence
```

This does **not** mean:

> KCNJ11 is scientifically proven to be the best target.

It means:

> KCNJ11 ranked highest under the current pipeline configuration and small literature sample.

---

# 13. Stage 9 — Target Prioritization

## Goal

Target Prioritization takes the fused results and sorts them.

It does not create another biological score.

The separation is:

```text
Evidence Fusion
       ↓
Calculate fused score
       ↓
Target Prioritization
       ↓
Sort / select Top-N
```

## Output

Each prioritized target contains:

```text
rank
target_id
target_symbol
fused_score
structured_score
literature_score
evidence_count
literature_status
```

## Test

```text
Total targets: 3
Selected targets: 3

1. KCNJ11
   Fused score: 0.9263
   Literature status: evidence_found
   Evidence count: 1

2. ABCC8
   Fused score: 0.5258
   Literature status: no_evidence
   Evidence count: 0

3. GCK
   Fused score: 0.5208
   Literature status: no_evidence
   Evidence count: 0
```

---

# 14. Errors Encountered During Integration

Several interface mismatches were found while connecting the modules.

## Error 1 — Open Targets

The integration test initially called:

```python
retrieve_targets(
    disease_id=DISEASE_ID,
    disease_name=DISEASE_NAME
)
```

But the existing method supported:

```python
retrieve_targets(
    disease_id,
    page_size=100,
    max_targets=500,
    min_score=None,
    top_n=None
)
```

The integration test was corrected to use the existing API.

## Error 2 — Evidence Extractor

The integration test initially passed:

```python
text=...
pmid=...
```

But the existing extractor expects:

```python
extract_from_chunk(
    chunk=RAGChunk,
    disease_name=...,
    target_symbol=...
)
```

The integration test was corrected to pass the actual RAG chunk.

## Error 3 — Evidence Graph

A graph fusion test initially inserted dictionaries into the graph.

The fusion code expected:

```python
EvidenceNode
```

objects.

The test was corrected to use real Pydantic `EvidenceNode` objects.

---

# 15. Current Status

| Stage | Status |
|---|---|
| Disease Normalization | ✅ Implemented and tested |
| Structured Target Retrieval | ✅ Implemented and tested |
| PubMed Literature Retrieval | ✅ Implemented and tested |
| Biomedical RAG | ✅ Implemented and tested |
| Evidence Extraction | ✅ Implemented and tested |
| Evidence Graph | ✅ Implemented and tested |
| Evidence Fusion | ✅ Implemented and integrated |
| Target Prioritization | ✅ Implemented and unit-tested |
| Real Fusion → Prioritizer wiring | 🔄 Next |
| Compound Retrieval | ⏳ Future |
| Compound Evidence | ⏳ Future |
| Protein/Compound Prioritization | ⏳ Future |
| Docking | ⏳ Future |
| Validation | ⏳ Future |
| PPI | ⏳ Future |
| Functional Analysis | ⏳ Future |
| Results Dashboard | ⏳ Future |

---

# 16. Current Limitations

The current system should not yet be treated as a scientifically validated target-ranking system.

Important limitations:

1. Open Targets scores are association scores, not final biological truth.

2. `no_evidence` does not mean the target has no biological evidence.

3. Rule-based evidence extraction can miss evidence.

4. Rule-based evidence extraction can sometimes classify text incorrectly.

5. Evidence strength categories are engineering categories.

6. Fusion weights of `0.6 / 0.4` are engineering choices.

7. Evidence items from the same paper could potentially inflate evidence counts in future versions.

8. Negative evidence needs explicit treatment.

9. The current literature sample is intentionally small for pipeline testing.

10. The current target ranking is an engineering prioritization and not a scientifically validated final target list.

---

# 17. Recommended Next Steps

The immediate next step is:

```text
Real Evidence Fusion Results
          ↓
Real Target Prioritization
          ↓
Top-N Candidate Targets
```

After that:

```text
Top Candidate Targets
        ↓
Compound Retrieval
        ↓
Compound Literature / Evidence
        ↓
Protein + Compound Evidence Graph
        ↓
Evidence Fusion
        ↓
Protein / Compound Prioritization
        ↓
Existing AI Pipelines
        ↓
Docking
        ↓
Validation
        ↓
PPI
        ↓
Functional Analysis
        ↓
Results / Dashboard
```

---

# 18. Simple Explanation of the Whole Project

The project starts with a disease such as:

```text
type 2 diabetes
```

First, the system identifies the standard disease:

```text
type 2 diabetes mellitus
MONDO:0005148
```

Then Open Targets gives candidate proteins:

```text
KCNJ11
ABCC8
GCK
...
```

Instead of searching every diabetes paper, the system asks focused questions:

```text
type 2 diabetes + KCNJ11
type 2 diabetes + ABCC8
type 2 diabetes + GCK
```

The retrieved papers are processed by RAG.

RAG finds the most relevant text.

The Evidence Extractor turns that text into structured evidence.

The Evidence Graph connects:

```text
Disease
 ↕
Target
 ↕
Evidence
 ↕
Paper
```

Evidence Fusion combines:

```text
Open Targets score
+
Literature evidence
```

Finally, Target Prioritization sorts the candidates.

The current engineering result is:

```text
KCNJ11
   ↓
highest fused score in the current test
```

The important achievement is that the complete pipeline now works from:

```text
Disease Input
        ↓
Target Candidates
        ↓
Literature
        ↓
Evidence
        ↓
Graph
        ↓
Fusion
        ↓
Prioritized Targets
```

---

# 19. Key Design Principle

The central design principle of this project is:

> **Do not use literature search alone to discover everything. Use structured biomedical data to generate candidates, then use targeted literature retrieval and RAG to collect evidence about those candidates.**

This keeps the pipeline more manageable and creates a clear path toward evidence-aware protein and compound prioritization.
