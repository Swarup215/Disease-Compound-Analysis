"""
chembl_client.py
----------------
ChEMBL REST API client for Route B compound retrieval.

Given a list of target ChEMBL IDs (or UniProt accessions), queries the
ChEMBL Activities endpoint to retrieve bioactive compounds tested against
those targets.  Results are filtered to meaningful assay types (B = binding,
F = functional) and structured into dicts aligned with CompoundCandidate /
BioactivityRecord models.

ChEMBL REST API docs: https://www.ebi.ac.uk/chembl/api/data/
"""

import time
from typing import Dict, List, Optional

import requests

CHEMBL_API_BASE = "https://www.ebi.ac.uk/chembl/api/data"

# Assay types to include
INCLUDED_ASSAY_TYPES = {"B", "F"}  # Binding, Functional

# Standard types we care about (potency + activity)
POTENCY_TYPES = {"IC50", "Ki", "Kd", "EC50", "Inhibition", "Activity", "Potency"}


class ChEMBLClient:
    """Client for ChEMBL REST API v1 (JSON format)."""

    _RATE_LIMIT_DELAY = 0.25  # seconds between requests

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self._last_request_time: float = 0.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self._RATE_LIMIT_DELAY:
            time.sleep(self._RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()

    def _get(self, url: str, params: Dict) -> Optional[Dict]:
        self._throttle()
        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Target resolution: UniProt -> ChEMBL target ID
    # ------------------------------------------------------------------

    def resolve_target_by_uniprot(self, uniprot_id: str) -> Optional[str]:
        """Return the ChEMBL target ID for a UniProt accession, or None."""
        url = f"{CHEMBL_API_BASE}/target.json"
        params = {
            "target_components__accession": uniprot_id,
            "target_type": "SINGLE PROTEIN",
            "limit": 1,
        }
        data = self._get(url, params)
        if not data:
            return None
        targets = data.get("targets", [])
        if targets:
            return targets[0].get("target_chembl_id")
        return None

    def resolve_target_by_gene_name(self, gene_symbol: str) -> Optional[str]:
        """Return the ChEMBL target ID for a gene symbol, or None."""
        url = f"{CHEMBL_API_BASE}/target.json"
        params = {
            "pref_name__icontains": gene_symbol,
            "target_type": "SINGLE PROTEIN",
            "organism": "Homo sapiens",
            "limit": 3,
        }
        data = self._get(url, params)
        if not data:
            return None
        targets = data.get("targets", [])
        if not targets:
            return None
        # Prefer exact match on pref_name
        for t in targets:
            pref = (t.get("pref_name") or "").upper()
            if pref == gene_symbol.upper():
                return t.get("target_chembl_id")
        return targets[0].get("target_chembl_id")

    # ------------------------------------------------------------------
    # Activity retrieval
    # ------------------------------------------------------------------

    def get_activities_for_target(
        self,
        target_chembl_id: str,
        max_results: int = 200,
        standard_types: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Retrieve bioactivity records for *target_chembl_id*.

        Returns a list of activity dicts aligned with BioactivityRecord fields.
        """
        if standard_types is None:
            standard_types = list(POTENCY_TYPES)

        url = f"{CHEMBL_API_BASE}/activity.json"
        collected: List[Dict] = []
        offset = 0
        page_size = min(100, max_results)

        while len(collected) < max_results:
            params = {
                "target_chembl_id": target_chembl_id,
                "assay_type__in": ",".join(INCLUDED_ASSAY_TYPES),
                "standard_type__in": ",".join(standard_types),
                "standard_value__isnull": "false",
                "limit": page_size,
                "offset": offset,
            }
            data = self._get(url, params)
            if not data:
                break
            activities = data.get("activities", [])
            if not activities:
                break

            for act in activities:
                std_type = act.get("standard_type") or ""
                if std_type not in set(standard_types):
                    continue
                try:
                    std_value = float(act["standard_value"]) if act.get("standard_value") else None
                except (TypeError, ValueError):
                    std_value = None

                collected.append({
                    "activity_id": str(act.get("activity_id") or ""),
                    "standard_type": std_type,
                    "standard_value": std_value,
                    "standard_units": act.get("standard_units"),
                    "standard_relation": act.get("standard_relation", "="),
                    "assay_type": act.get("assay_type"),
                    "assay_description": act.get("assay_description"),
                    "target_chembl_id": target_chembl_id,
                    "molecule_chembl_id": act.get("molecule_chembl_id"),
                    "document_chembl_id": act.get("document_chembl_id"),
                    "pmid": str(act.get("src_id") or "") if act.get("src_id") else None,
                    "doi": act.get("document_journal"),  # best effort
                })

            offset += page_size
            total = data.get("page_meta", {}).get("total_count", 0)
            if offset >= total:
                break

        return collected[:max_results]

    # ------------------------------------------------------------------
    # Molecule details
    # ------------------------------------------------------------------

    def get_molecule(self, chembl_id: str) -> Optional[Dict]:
        """Fetch basic molecule metadata for a ChEMBL molecule ID."""
        url = f"{CHEMBL_API_BASE}/molecule/{chembl_id}.json"
        self._throttle()
        try:
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None

    def get_molecules_batch(self, chembl_ids: List[str]) -> List[Dict]:
        """Fetch molecule metadata for a batch of ChEMBL IDs."""
        if not chembl_ids:
            return []
        url = f"{CHEMBL_API_BASE}/molecule.json"
        params = {
            "molecule_chembl_id__in": ",".join(chembl_ids[:100]),
            "limit": 100,
        }
        data = self._get(url, params)
        if not data:
            return []
        return data.get("molecules", [])

    # ------------------------------------------------------------------
    # Natural-origin check
    # ------------------------------------------------------------------

    @staticmethod
    def is_natural_origin(molecule_dict: Dict) -> bool:
        """
        Heuristic: a molecule is likely of natural origin when its
        ChEMBL 'natural_product' flag is set, or its molecule type is
        'Natural Product'.
        """
        props = molecule_dict.get("molecule_properties") or {}
        mol_type = (molecule_dict.get("molecule_type") or "").lower()
        np_flag = molecule_dict.get("natural_product", 0)
        # np_flag can be 0/1 integer or True/False
        return bool(np_flag) or "natural" in mol_type
