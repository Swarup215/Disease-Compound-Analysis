"""
pubchem_client.py
-----------------
PubChem PUG REST API client for Step 7: Compound Identity & Natural-Origin Verification.

Retrieves authoritative chemical identity information:
  - PubChem CID (Compound Identifier)
  - Canonical SMILES and Isomeric SMILES
  - Standard InChIKey (14-10-1 format)
  - IUPAC Name
  - Molecular Formula & Molecular Weight
  - Chemical synonyms and trade names

Complies with NCBI PubChem usage policies (rate throttling and error recovery).
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional
import urllib.parse
import requests

logger = logging.getLogger(__name__)

PUBCHEM_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


class PubChemClient:
    """Client for the NCBI PubChem PUG REST API with built-in caching and throttling."""

    _RATE_LIMIT_DELAY = 0.20  # Minimum 200ms between calls (~5 req/sec limit)

    def __init__(self, timeout: int = 15):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Biomedical-AI-Compound-Verifier/1.0 (academic/research)",
            "Accept": "application/json",
        })
        self.timeout = timeout
        self._last_request_time: float = 0.0
        # In-memory LRU/dict cache: key -> dict
        self._cache: Dict[str, Any] = {}

    def _throttle(self) -> None:
        """Enforce rate limiting between successive PubChem API requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._RATE_LIMIT_DELAY:
            time.sleep(self._RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()

    def _get(self, url: str) -> Optional[Dict[str, Any]]:
        """Execute a throttled GET request and return the parsed JSON response."""
        if url in self._cache:
            return self._cache[url]

        self._throttle()
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                self._cache[url] = data
                return data
            elif resp.status_code == 404:
                # Normal 404: compound not found in PubChem
                self._cache[url] = None
                return None
            else:
                logger.warning(f"PubChem request returned HTTP {resp.status_code} for {url}")
                return None
        except Exception as exc:
            logger.warning(f"PubChem network error for {url}: {exc}")
            return None

    # -------------------------------------------------------------------------
    # Property retrieval
    # -------------------------------------------------------------------------

    def get_properties_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Query PubChem by common or chemical name to retrieve primary physical properties.
        Returns dict with keys: CID, InChIKey, CanonicalSMILES, IsomericSMILES,
        IUPACName, MolecularFormula, MolecularWeight.
        """
        clean_name = name.strip()
        if not clean_name:
            return None

        # URL encode name safely
        encoded = urllib.parse.quote(clean_name, safe="")
        props = "InChIKey,CanonicalSMILES,IsomericSMILES,IUPACName,MolecularFormula,MolecularWeight"
        url = f"{PUBCHEM_BASE_URL}/compound/name/{encoded}/property/{props}/JSON"

        data = self._get(url)
        if not data:
            return None

        try:
            properties_list = data.get("PropertyTable", {}).get("Properties", [])
            if properties_list:
                return properties_list[0]
        except (KeyError, IndexError, TypeError):
            pass
        return None

    def get_properties_by_cid(self, cid: int) -> Optional[Dict[str, Any]]:
        """Query PubChem properties for a specific integer CID."""
        if not cid or cid <= 0:
            return None

        props = "InChIKey,CanonicalSMILES,IsomericSMILES,IUPACName,MolecularFormula,MolecularWeight"
        url = f"{PUBCHEM_BASE_URL}/compound/cid/{cid}/property/{props}/JSON"

        data = self._get(url)
        if not data:
            return None

        try:
            properties_list = data.get("PropertyTable", {}).get("Properties", [])
            if properties_list:
                return properties_list[0]
        except (KeyError, IndexError, TypeError):
            pass
        return None

    def get_properties_by_inchikey(self, inchikey: str) -> Optional[Dict[str, Any]]:
        """Query PubChem properties using a Standard InChIKey."""
        clean_key = inchikey.strip().upper()
        if not self.is_valid_inchikey(clean_key):
            return None

        props = "InChIKey,CanonicalSMILES,IsomericSMILES,IUPACName,MolecularFormula,MolecularWeight"
        url = f"{PUBCHEM_BASE_URL}/compound/inchikey/{clean_key}/property/{props}/JSON"

        data = self._get(url)
        if not data:
            return None

        try:
            properties_list = data.get("PropertyTable", {}).get("Properties", [])
            if properties_list:
                return properties_list[0]
        except (KeyError, IndexError, TypeError):
            pass
        return None

    def get_properties_by_smiles(self, smiles: str) -> Optional[Dict[str, Any]]:
        """Query PubChem properties using a SMILES string."""
        clean_smiles = smiles.strip()
        if not clean_smiles:
            return None

        encoded = urllib.parse.quote(clean_smiles, safe="")
        props = "InChIKey,CanonicalSMILES,IsomericSMILES,IUPACName,MolecularFormula,MolecularWeight"
        url = f"{PUBCHEM_BASE_URL}/compound/smiles/{encoded}/property/{props}/JSON"

        data = self._get(url)
        if not data:
            return None

        try:
            properties_list = data.get("PropertyTable", {}).get("Properties", [])
            if properties_list:
                return properties_list[0]
        except (KeyError, IndexError, TypeError):
            pass
        return None

    # -------------------------------------------------------------------------
    # Synonyms resolution
    # -------------------------------------------------------------------------

    def get_synonyms_by_cid(self, cid: int, max_synonyms: int = 15) -> List[str]:
        """Retrieve authoritative chemical synonyms and trade names for a given PubChem CID."""
        if not cid or cid <= 0:
            return []

        url = f"{PUBCHEM_BASE_URL}/compound/cid/{cid}/synonyms/JSON"
        data = self._get(url)
        if not data:
            return []

        try:
            info_list = data.get("InformationList", {}).get("Information", [])
            if info_list:
                synonyms = info_list[0].get("Synonym", [])
                # Return distinct non-empty strings up to max_synonyms
                seen = set()
                result = []
                for s in synonyms:
                    s_clean = s.strip()
                    if s_clean and s_clean.lower() not in seen:
                        seen.add(s_clean.lower())
                        result.append(s_clean)
                        if len(result) >= max_synonyms:
                            break
                return result
        except (KeyError, IndexError, TypeError):
            pass
        return []

    # -------------------------------------------------------------------------
    # High-level compound identity resolver
    # -------------------------------------------------------------------------

    def resolve_identity(
        self,
        name: Optional[str] = None,
        inchikey: Optional[str] = None,
        smiles: Optional[str] = None,
        pubchem_cid: Optional[int] = None,
        fetch_synonyms: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Unified multi-strategy chemical resolver.
        Tries:
          1. Directly by PubChem CID (if known)
          2. By InChIKey (highest structural fidelity)
          3. By Name (standard biomedical literature query)
          4. By SMILES (if available)

        Returns standardized identity dictionary, or None if completely unresolvable.
        """
        props = None

        # Strategy 1: CID
        if pubchem_cid and pubchem_cid > 0:
            props = self.get_properties_by_cid(pubchem_cid)

        # Strategy 2: InChIKey
        if not props and inchikey and self.is_valid_inchikey(inchikey):
            props = self.get_properties_by_inchikey(inchikey)

        # Strategy 3: Name
        if not props and name:
            props = self.get_properties_by_name(name)
            # Try cleaning compound name if not found (e.g., removing trailing salt/specifiers)
            if not props and ("(" in name or "," in name or "-" in name):
                simplified = re.sub(r"\(.*?\)", "", name).strip()
                if simplified and simplified.lower() != name.lower():
                    props = self.get_properties_by_name(simplified)

        # Strategy 4: SMILES
        if not props and smiles:
            props = self.get_properties_by_smiles(smiles)

        if not props:
            return None

        # Parse properties safely
        cid = props.get("CID")
        synonyms = self.get_synonyms_by_cid(cid, max_synonyms=15) if (cid and fetch_synonyms) else []

        mw_val = props.get("MolecularWeight")
        try:
            mw = float(mw_val) if mw_val is not None else None
        except (ValueError, TypeError):
            mw = None

        return {
            "pubchem_cid": cid,
            "inchikey": props.get("InChIKey"),
            "canonical_smiles": props.get("CanonicalSMILES") or props.get("ConnectivitySMILES"),
            "isomeric_smiles": props.get("IsomericSMILES"),
            "iupac_name": props.get("IUPACName"),
            "molecular_formula": props.get("MolecularFormula"),
            "molecular_weight": mw,
            "synonyms": synonyms,
        }

    @staticmethod
    def is_valid_inchikey(key: Optional[str]) -> bool:
        """Validate whether a string conforms to Standard InChIKey syntax (14-10-1 format)."""
        if not key or not isinstance(key, str):
            return False
        # Standard InChIKey: 14 uppercase letters, hyphen, 10 uppercase letters/digits, hyphen, 1 letter
        pattern = r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$"
        return bool(re.match(pattern, key.strip()))

