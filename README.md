# Biomedical AI — Disease Target Discovery & Evidence Analysis

A modular biomedical evidence pipeline for disease normalization, structured target retrieval, literature retrieval, evidence extraction, evidence graphs, evidence fusion, and target prioritization. Includes a local web server and browser-based UI for interactive disease analysis.

---

## Components

| Module | Description |
|---|---|
| `disease_normalizer/` | Normalizes disease names and resolves ontology identifiers (MONDO, DOID, EFO, MeSH) |
| `structured_retriever/` | Retrieves disease-target associations from structured sources such as Open Targets |
| `literature_retriever/` | Builds literature queries and harvests scientific literature across PubMed, EMBL-EBI Europe PMC, and Open Targets |
| `biomedical_rag/` | Processes, chunks, embeds, stores, retrieves, and reranks literature evidence |
| `evidence_extractor/` | Extracts structured evidence from retrieved text |
| `evidence_graph/` | Represents diseases, targets, papers, and evidence relationships |
| `evidence_fusion/` | Combines structured and literature evidence into a fused score |
| `target_prioritization/` | Sorts fused target results and selects the top candidates |
| `frontend/` | Browser-based UI served by the local HTTP server |
| `server.py` | Local HTTP server exposing REST API + frontend |
| `pipeline.py` | End-to-end pipeline orchestrator |

---

## Prerequisites

- **Python 3.10 or higher** — [Download Python](https://www.python.org/downloads/)
- **Git** — [Download Git](https://git-scm.com/downloads)
- An active internet connection (for literature retrieval from PubMed / Europe PMC)

---

## Step-by-Step Setup (Windows CMD)

### 1. Clone the Repository

Open **Command Prompt (CMD)** and run:

```cmd
git clone https://github.com/Swarup215/Disease-Compound-Analysis.git
cd Disease-Compound-Analysis
```

### 2. Checkout the Feature Branch

```cmd
git checkout feature/multi-source-literature-retrieval
```

### 3. Create a Virtual Environment

```cmd
python -m venv venv
```

### 4. Activate the Virtual Environment

```cmd
venv\Scripts\activate.bat
```

> You should now see `(venv)` at the start of your command prompt, confirming the environment is active.

### 5. Install Dependencies

```cmd
pip install -r requirements.txt
```

> This installs all required packages including PyTorch, FAISS, sentence-transformers, scikit-learn, and more.  
> **Note:** First-time installation may take several minutes depending on your internet speed.

### 6. Run the Local Web Server

```cmd
python server.py
```

You should see:

```
Biomedical AI Server running on http://localhost:8000
```

### 7. Open the Application in Your Browser

Open your browser and navigate to:

```
http://127.0.0.1:8000
```

> If `localhost` does not resolve, use `127.0.0.1` directly.

---

## REST API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Frontend UI |
| `/api/health` | GET | Health check — returns `{"status": "healthy"}` |
| `/api/suggest?q=<query>` | GET | Disease name autocomplete suggestions |
| `/api/suggest` | POST | Disease suggestions via JSON body `{"query": "diabetes"}` |
| `/api/analyze` | POST | Run the full biomedical pipeline for a disease |

### Example: Analyze a Disease via CMD (curl)

```cmd
curl -X POST http://127.0.0.1:8000/api/analyze ^
  -H "Content-Type: application/json" ^
  -d "{\"disease\": \"Type 2 diabetes\"}"
```

### Example: Health Check

```cmd
curl http://127.0.0.1:8000/api/health
```

---

## Running Tests (CMD)

Make sure the virtual environment is active (`venv\Scripts\activate.bat`) before running any test.

### Disease Normalizer Test

```cmd
python test_disease_normalizer.py
```

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
```

> `test_evidence_fusion_integration.py` calls external services and requires an active internet connection.

---

## Target Prioritization

Evidence Fusion calculates the combined score for each target. Target Prioritization then sorts those existing fusion results and returns the requested number of highest-scoring candidates.

```python
from target_prioritization import TargetPrioritizer

result = TargetPrioritizer().prioritize(
    fusion_results=fusion_results,
    top_n=10
)
```

The prioritizer rejects empty fusion results and non-positive `top_n` values.

---

## Stopping the Server

In the CMD window where the server is running, press:

```
Ctrl + C
```

---

## Deactivating the Virtual Environment

When you are done, deactivate the virtual environment with:

```cmd
deactivate
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `python` not recognized | Ensure Python is added to PATH during installation |
| `venv\Scripts\activate.bat` fails | Run CMD as Administrator or check Python installation |
| `pip install` errors | Upgrade pip first: `python -m pip install --upgrade pip` |
| Site cannot be reached at `localhost:8000` | Use `http://127.0.0.1:8000` instead |
| Port 8000 already in use | Run `netstat -ano \| findstr :8000` to find the PID, then `taskkill /PID <PID> /F` |
