import requests


OPEN_TARGETS_URL = (
    "https://api.platform.opentargets.org/api/v4/graphql"
)


class OpenTargetsClient:

    def __init__(self, timeout: int = 30):

        self.timeout = timeout

    def get_associated_targets(
        self,
        disease_id: str,
        page_index: int = 0,
        page_size: int = 25
    ):

        if not disease_id:
            raise ValueError(
                "Disease ID cannot be empty."
            )

        if page_index < 0:
            raise ValueError(
                "page_index cannot be negative."
            )

        if page_size <= 0:
            raise ValueError(
                "page_size must be greater than 0."
            )

        open_targets_id = disease_id.replace(
            ":",
            "_"
        )

        query = """
        query associatedTargets(
            $diseaseId: String!,
            $pageIndex: Int!,
            $pageSize: Int!
        ) {

            disease(efoId: $diseaseId) {

                id

                name

                associatedTargets(
                    page: {
                        index: $pageIndex,
                        size: $pageSize
                    }
                ) {

                    count

                    rows {

                        target {
                            id
                            approvedSymbol
                            approvedName
                        }

                        score

                        datatypeScores {
                            id
                            score
                        }
                    }
                }
            }
        }
        """

        variables = {
            "diseaseId": open_targets_id,
            "pageIndex": page_index,
            "pageSize": page_size
        }

        try:

            response = requests.post(
                OPEN_TARGETS_URL,
                json={
                    "query": query,
                    "variables": variables
                },
                timeout=self.timeout
            )

            response.raise_for_status()

        except requests.RequestException as exc:

            raise RuntimeError(
                f"Open Targets request failed: {exc}"
            ) from exc

        data = response.json()

        if "errors" in data:

            raise RuntimeError(
                f"Open Targets API error: "
                f"{data['errors']}"
            )

        if "data" not in data:

            raise RuntimeError(
                "Open Targets returned no data."
            )

        return data["data"]