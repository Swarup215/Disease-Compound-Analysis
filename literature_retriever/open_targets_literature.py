import logging
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)

OPEN_TARGETS_URL = "https://api.platform.opentargets.org/api/v4/graphql"


class OpenTargetsLiteratureClient:
    """
    Client for extracting literature-mined evidence records from Open Targets Platform GraphQL API.
    Retrieves peer-reviewed publications associated with a specific disease and target gene.
    """

    def __init__(self, timeout: int = 15):
        self.session = requests.Session()
        self.timeout = timeout

    def get_evidence_pmids(
        self,
        disease_id: str,
        target_ensembl_id: str,
        size: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieves literature evidence records (PMIDs and text-mining confidence scores)
        for a specific disease and target from Open Targets.
        """
        if not disease_id or not target_ensembl_id:
            return []

        clean_disease_id = disease_id.replace(":", "_")

        query = """
        query targetLiteratureEvidence($diseaseId: String!, $targetId: String!, $size: Int!) {
            disease(efoId: $diseaseId) {
                name
                evidences(
                    ensemblIds: [$targetId],
                    datasourceIds: ["europepmc"],
                    size: $size
                ) {
                    count
                    rows {
                        score
                        literature
                    }
                }
            }
        }
        """

        variables = {
            "diseaseId": clean_disease_id,
            "targetId": target_ensembl_id,
            "size": size
        }

        try:
            response = self.session.post(
                OPEN_TARGETS_URL,
                json={"query": query, "variables": variables},
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            disease_data = data.get("data", {}).get("disease")
            if not disease_data:
                return []

            evidences = disease_data.get("evidences", {})
            rows = evidences.get("rows", [])
            results = []
            seen_pmids = set()

            for row in rows:
                score = row.get("score", 0.0)
                pmids = row.get("literature") or []
                for pmid in pmids:
                    pmid_str = str(pmid).strip()
                    if pmid_str and pmid_str not in seen_pmids:
                        seen_pmids.add(pmid_str)
                        results.append({
                            "pmid": pmid_str,
                            "open_targets_score": score,
                            "source": "Open Targets (Text-Mined)"
                        })

            return results
        except Exception as exc:
            logger.warning(
                f"Open Targets literature query failed for disease {disease_id} and target {target_ensembl_id}: {exc}"
            )
            return []
