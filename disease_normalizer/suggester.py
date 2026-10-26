from typing import Any, Dict, List
import requests
import difflib

# Curated reference catalog of disease concepts with IDs & synonyms for instant spell correction & autocomplete
CURATED_DISEASES: List[Dict[str, Any]] = [
    {"name": "Type 2 diabetes mellitus", "id": "MONDO:0005148", "synonyms": ["Type 2 diabetes", "T2D", "NIDDM", "diabtes", "diabetes type 2", "diabetis"]},
    {"name": "Type 1 diabetes mellitus", "id": "MONDO:0005147", "synonyms": ["Type 1 diabetes", "T1D", "juvenile diabetes", "diabetes type 1"]},
    {"name": "Diabetes mellitus", "id": "MONDO:0005015", "synonyms": ["Diabetes", "diabtes", "diabetic"]},
    {"name": "Diabetes insipidus", "id": "MONDO:0007450", "synonyms": ["Diabetes insipidus"]},
    {"name": "Alzheimer disease", "id": "MONDO:0004975", "synonyms": ["Alzheimer's disease", "Alzheimers", "alzhemier", "alzheimer"]},
    {"name": "Parkinson disease", "id": "MONDO:0005180", "synonyms": ["Parkinson's disease", "Parkinsons", "parkins", "parkinson"]},
    {"name": "Rheumatoid arthritis", "id": "MONDO:0008383", "synonyms": ["RA", "arthritis", "rheumatoid"]},
    {"name": "Multiple sclerosis", "id": "MONDO:0005301", "synonyms": ["MS", "sclerosis"]},
    {"name": "Crohn disease", "id": "MONDO:0004980", "synonyms": ["Crohn's disease", "Crohns", "IBD"]},
    {"name": "Ulcerative colitis", "id": "MONDO:0005101", "synonyms": ["UC", "Colitis"]},
    {"name": "Systemic lupus erythematosus", "id": "MONDO:0007915", "synonyms": ["Lupus", "SLE", "lups"]},
    {"name": "Asthma", "id": "MONDO:0004979", "synonyms": ["Bronchial asthma", "astma", "athsma"]},
    {"name": "Hypertension", "id": "MONDO:0005044", "synonyms": ["High blood pressure", "HTN"]},
    {"name": "Atherosclerosis", "id": "MONDO:0005311", "synonyms": ["Arteriosclerosis"]},
    {"name": "Heart failure", "id": "MONDO:0005009", "synonyms": ["Congestive heart failure", "CHF"]},
    {"name": "Myocardial infarction", "id": "MONDO:0005060", "synonyms": ["Heart attack", "MI"]},
    {"name": "Stroke", "id": "MONDO:0005093", "synonyms": ["Cerebrovascular accident", "Ischemic stroke"]},
    {"name": "Colorectal cancer", "id": "MONDO:0005575", "synonyms": ["Bowel cancer", "Colon cancer", "Rectal cancer"]},
    {"name": "Breast cancer", "id": "MONDO:0003582", "synonyms": ["Breast carcinoma", "BRCA"]},
    {"name": "Lung cancer", "id": "MONDO:0008903", "synonyms": ["Lung carcinoma", "NSCLC"]},
    {"name": "Prostate cancer", "id": "MONDO:0005072", "synonyms": ["Prostate carcinoma"]},
    {"name": "Pancreatic cancer", "id": "MONDO:0002633", "synonyms": ["Pancreatic adenocarcinoma"]},
    {"name": "Melanoma", "id": "MONDO:0005012", "synonyms": ["Skin melanoma"]},
    {"name": "Glioblastoma", "id": "MONDO:0018177", "synonyms": ["Glioblastoma multiforme", "GBM"]},
    {"name": "Psoriasis", "id": "MONDO:0005041", "synonyms": ["Psoriatic arthritis"]},
    {"name": "Atopic dermatitis", "id": "MONDO:0004981", "synonyms": ["Eczema"]},
    {"name": "Idiopathic pulmonary fibrosis", "id": "MONDO:0005251", "synonyms": ["IPF"]},
    {"name": "Non-alcoholic fatty liver disease", "id": "MONDO:0005172", "synonyms": ["NAFLD", "NASH", "MASLD", "Fatty liver"]},
    {"name": "Obesity", "id": "MONDO:0011122", "synonyms": ["Adiposity"]},
    {"name": "Chronic kidney disease", "id": "MONDO:0005300", "synonyms": ["CKD", "Renal failure"]},
    {"name": "Amyotrophic lateral sclerosis", "id": "MONDO:0004976", "synonyms": ["ALS", "Lou Gehrig's disease"]},
    {"name": "Huntington disease", "id": "MONDO:0007739", "synonyms": ["Huntington's chorea"]},
    {"name": "Major depressive disorder", "id": "MONDO:0002050", "synonyms": ["Depression", "MDD"]},
    {"name": "Schizophrenia", "id": "MONDO:0005090", "synonyms": ["SCZ"]},
    {"name": "Bipolar disorder", "id": "MONDO:0004985", "synonyms": ["Manic depression"]}
]


def get_disease_suggestions(query: str, limit: int = 8) -> List[Dict[str, Any]]:
    """
    Returns disease suggestions based on prefix/substring matching, fuzzy spelling correction,
    and Open Targets / OLS API lookup.
    """
    if not query or not query.strip():
        return []

    q_raw = query.strip()
    q_clean = q_raw.lower()
    results: List[Dict[str, Any]] = []
    seen = set()

    # 1. Exact & Substring Matches in Curated Catalog
    for item in CURATED_DISEASES:
        name = item["name"]
        item_id = item["id"]
        syns = item["synonyms"]

        is_match = False
        if q_clean in name.lower():
            is_match = True
        else:
            for s in syns:
                if q_clean in s.lower():
                    is_match = True
                    break

        if is_match and name.lower() not in seen:
            seen.add(name.lower())
            results.append({
                "name": name,
                "id": item_id,
                "source": "MONDO Ontology",
                "score": 1.0 if name.lower() == q_clean else 0.8
            })

    # 2. Remote API Query (Open Targets GraphQL) for real-time coverage
    if len(q_clean) >= 2:
        try:
            url = "https://api.platform.opentargets.org/api/v4/graphql"
            gql = f"""
            query {{
              search(queryString: "{q_clean}", entityNames: ["disease"], page: {{ size: 8, index: 0 }}) {{
                hits {{
                  id
                  name
                }}
              }}
            }}
            """
            resp = requests.post(url, json={"query": gql}, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                hits = data.get("data", {}).get("search", {}).get("hits", [])
                for h in hits:
                    h_name = h.get("name")
                    h_id = (h.get("id") or "").replace("_", ":")
                    if h_name and h_name.lower() not in seen:
                        seen.add(h_name.lower())
                        results.append({
                            "name": h_name,
                            "id": h_id or "EFO/MONDO",
                            "source": "Open Targets",
                            "score": 0.7
                        })
        except Exception:
            pass

    # 3. Fuzzy Spelling Correction (difflib) for typos like 'diabtes', 'alzhemier', 'lups'
    if len(results) < 5:
        term_map = {}
        for item in CURATED_DISEASES:
            term_map[item["name"].lower()] = item
            for s in item["synonyms"]:
                term_map[s.lower()] = item

        matches = difflib.get_close_matches(q_clean, list(term_map.keys()), n=6, cutoff=0.35)
        for match in matches:
            item = term_map[match]
            if item["name"].lower() not in seen:
                seen.add(item["name"].lower())
                results.append({
                    "name": item["name"],
                    "id": item["id"],
                    "source": "Spelling Correction",
                    "score": 0.6
                })

    # Sort results by score
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
