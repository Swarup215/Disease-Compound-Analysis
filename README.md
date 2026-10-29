# Biomedical AI — Disease Target Discovery & Evidence Analysis

A modular biomedical evidence pipeline for disease normalization, structured target retrieval, literature retrieval, evidence extraction, evidence graphs, evidence fusion, target prioritization, natural compound candidate retrieval, and compound identity verification. Includes a local web server and browser-based UI for interactive disease analysis.

---

## Components

| Module | Step | Description |
|---|---|---|
| `disease_normalizer/` | Step 1 | Normalizes disease names and resolves ontology identifiers (MONDO, DOID, EFO, MeSH) |
| `structured_retriever/` | Step 2 | Retrieves disease-target associations from structured sources such as Open Targets |
| `literature_retriever/` | Step 3 | Builds literature queries and harvests scientific literature across PubMed, EMBL-EBI Europe PMC, and Open Targets |
| `biomedical_rag/` | Step 3-4 | Processes, chunks, embeds, stores, retrieves, and reranks literature evidence |
| `evidence_extractor/` | Step 4 | Extracts structured biological assertions from retrieved text |
| `evidence_graph/` | Step 4-5 | Represents diseases, targets, papers, and evidence relationships |
| `evidence_fusion/` | Step 5 | Combines structured and literature evidence into a fused score |
| `target_prioritization/` | Step 5 | Sorts fused target results and selects the top candidates |
| `compound_retriever/` | Step 6 | Discovers candidate bioactive and natural compounds via dual routes (Disease lit + Protein ChEMBL) |
| `compound_verifier/` | Step 7 | Standardizes chemical identity (PubChem CID, SMILES, InChIKey), classifies natural vs. synthetic origin, and retains provenance |
| `frontend/` | UI | Browser-based interactive UI served by the local HTTP server |
| `server.py` | API | Local HTTP server exposing REST APIs (`/api/analyze`, `/api/compounds`, `/api/compounds/verify`) + frontend |
| `pipeline.py` | Orchestration | End-to-end target discovery pipeline orchestrator |

---

## Prerequisites

- **Python 3.10 or higher** — [Download Python](https://www.python.org/downloads/)
- **Git** — [Download Git](https://git-scm.com/downloads)
- An active internet connection (for literature retrieval and PubChem / ChEMBL APIs)

---

## Step-by-Step Setup (Windows CMD)

### 1. Clone the Repository

Open **Command Prompt (CMD)** and run:

```cmd
git clone https://github.com/Swarup215/Disease-Compound-Analysis.git
cd Disease-Compound-Analysis
```

### 2. Create a Virtual Environment

```cmd
python -m venv venv
```

### 3. Activate the Virtual Environment

```cmd
venv\Scripts\activate.bat
```
*(or in PowerShell: `.\venv\Scripts\Activate.ps1`)*

> You should now see `(venv)` at the start of your command prompt.

### 4. Install Dependencies

```cmd
pip install -r requirements.txt
```

### 5. Run the Local Web Server

```cmd
python server.py
```

You should see:

```
Biomedical AI Server running on http://localhost:8000
```

### 6. Open the Application in Your Browser

Open your browser and navigate to:

```
http://127.0.0.1:8000
```

---

## REST API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Frontend UI |
| `/api/health` | GET | Health check — returns `{"status": "healthy"}` |
| `/api/suggest?q=<query>` | GET | Disease name autocomplete suggestions |
| `/api/suggest` | POST | Disease suggestions via JSON body `{"query": "diabetes"}` |
| `/api/analyze` | POST | Run Steps 1–5 of the biomedical pipeline for a disease |
| `/api/compounds` | POST | Run Step 6 & 7: Retrieve and verify natural compounds for prioritized targets |
| `/api/compounds/verify` | POST | Step 7: Verify identity and natural/synthetic status for arbitrary compound lists |

---

## Running Tests (CMD)

Make sure the virtual environment is active (`venv\Scripts\activate.bat`) before running tests.

### All Available Tests

```cmd
python test_disease_normalizer.py
python test_evidence_extractor.py
python test_evidence_fusion.py
python test_evidence_fusion_graph.py
python test_evidence_fusion_integration.py
python test_evidence_graph.py
python test_literature_retriever_unit.py
python test_query_builder_unit.py
python test_rag_pipeline.py
python test_target_prioritization.py
python test_compound_retriever.py
python test_compound_verifier.py
```

---

## Step 7: Compound Identity & Natural-Origin Verification

```python
from compound_verifier import CompoundVerifier

verifier = CompoundVerifier()

# Verify single compound
result = verifier.verify_compound({"name": "quercetin"})
print(result.identity.pubchem_cid)            # 5280343
print(result.identity.inchikey)              # REFJWTPEDVJJIY-UHFFFAOYSA-N
print(result.natural_verification.status)    # NaturalOriginStatus.NATURAL
print(result.natural_verification.natural_product_class) # Flavonoid

# Verify batch of compounds from Step 6
batch = verifier.verify_batch(candidates, disease_name="Type 2 diabetes")
```

---

## Stopping the Server

Press `Ctrl + C` in the CMD window.

## Deactivating the Virtual Environment

```cmd
deactivate
```
