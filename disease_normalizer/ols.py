from typing import Any, Dict, List
import requests


OLS_BASE_URL = "https://www.ebi.ac.uk/ols4/api"


class OLSClient:

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def search(
        self,
        query: str,
        ontology: str,
        rows: int = 20
    ) -> List[Dict[str, Any]]:

        url = f"{OLS_BASE_URL}/select"

        params = {
        "q": query,
        "ontology": ontology,
        "rows": rows,
        "start": 0,
        "type": "class",
        "obsoletes": "false",
        "local": "true",
        "fieldList": (
            "iri,"
            "label,"
            "short_form,"
            "obo_id,"
            "ontology_name,"
            "ontology_prefix,"
            "description,"
            "synonym"
        )
    }

        try:

            response = requests.get(
                url,
                params=params,
                timeout=self.timeout
            )

            response.raise_for_status()

            data = response.json()

            return data.get(
                "response",
                {}
            ).get(
                "docs",
                []
            )

        except requests.RequestException as exc:

            raise RuntimeError(
                f"OLS request failed: {exc}"
            ) from exc