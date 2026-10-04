from typing import Dict, List, Optional

from .model import (
    TargetCandidate,
    TargetEvidence,
    StructuredRetrievalResult
)

from .open_targets import OpenTargetsClient


class StructuredRetriever:

    def __init__(self):

        self.open_targets = OpenTargetsClient()

    @staticmethod
    @staticmethod
    def _parse_evidence(
    datatype_scores
) -> TargetEvidence:

        scores = {}

        if not datatype_scores:

            return TargetEvidence(
            scores=scores
        )

        for item in datatype_scores:

            if not isinstance(item, dict):
                continue

            datatype = item.get("id")

            score = item.get("score")

            if datatype is None:
                continue

            if score is None:
                continue

            scores[datatype] = score

        return TargetEvidence(
            scores=scores
    )

    @staticmethod
    def _deduplicate_targets(
        targets: List[TargetCandidate]
    ) -> List[TargetCandidate]:

        unique_targets: Dict[
            str,
            TargetCandidate
        ] = {}

        for target in targets:

            if target.id not in unique_targets:

                unique_targets[target.id] = target

            else:

                existing = unique_targets[
                    target.id
                ]

                # Keep the higher score if
                # the same target appears twice.

                if target.score > existing.score:

                    unique_targets[
                        target.id
                    ] = target

        return list(
            unique_targets.values()
        )

    def retrieve_targets(
        self,
        disease_id: str,
        page_size: int = 100,
        max_targets: int = 500,
        min_score: Optional[float] = None,
        top_n: Optional[int] = None
    ) -> StructuredRetrievalResult:

        if not disease_id:
            raise ValueError(
                "Disease ID cannot be empty."
            )

        if page_size <= 0:
            raise ValueError(
                "page_size must be greater than 0."
            )

        if max_targets <= 0:
            raise ValueError(
                "max_targets must be greater than 0."
            )

        if min_score is not None:

            if not 0.0 <= min_score <= 1.0:

                raise ValueError(
                    "min_score must be between "
                    "0.0 and 1.0."
                )

        if top_n is not None:

            if top_n <= 0:

                raise ValueError(
                    "top_n must be greater than 0."
                )

        all_targets: List[
            TargetCandidate
        ] = []

        page_index = 0

        total_targets = 0

        disease_name = None

        while True:

            data = (
                self.open_targets
                .get_associated_targets(
                    disease_id=disease_id,
                    page_index=page_index,
                    page_size=page_size
                )
            )

            disease = data.get(
                "disease"
            )

            if not disease:

                raise RuntimeError(
                    f"Disease not found: "
                    f"{disease_id}"
                )

            disease_name = disease.get(
                "name"
            )

            associated_targets = (
                disease.get(
                    "associatedTargets"
                )
                or {}
            )

            total_targets = (
                associated_targets.get(
                    "count"
                )
                or 0
            )

            rows = (
                associated_targets.get(
                    "rows"
                )
                or []
            )

            if not rows:
                break

            for row in rows:

                target = row.get(
                    "target"
                )

                if not target:
                    continue

                target_id = target.get(
                    "id"
                )

                if not target_id:
                    continue

                score = row.get(
                    "score",
                    0.0
                )

                if score is None:
                    score = 0.0

                evidence = (
                    self._parse_evidence(
                        row.get(
                            "datatypeScores"
                        )
                    )
                )

                all_targets.append(
                    TargetCandidate(

                        id=target_id,

                        symbol=target.get(
                            "approvedSymbol"
                        ),

                        name=target.get(
                            "approvedName"
                        ),

                        score=score,

                        evidence=evidence,

                        source="Open Targets"
                    )
                )

            # Stop retrieving once our
            # safety limit is reached.

            if len(all_targets) >= max_targets:

                break

            # Stop if we have reached
            # the total available targets.

            if len(all_targets) >= total_targets:

                break

            page_index += 1

        # --------------------------------
        # Deduplicate
        # --------------------------------

        all_targets = (
            self._deduplicate_targets(
                all_targets
            )
        )

        # --------------------------------
        # Sort by Open Targets score
        # --------------------------------

        all_targets.sort(
            key=lambda target: target.score,
            reverse=True
        )

        retrieved_targets = len(
            all_targets
        )

        # --------------------------------
        # Minimum score filtering
        # --------------------------------

        filtered_targets = all_targets

        if min_score is not None:

            filtered_targets = [

                target

                for target in filtered_targets

                if target.score >= min_score
            ]

        # --------------------------------
        # Top-N filtering
        # --------------------------------

        if top_n is not None:

            filtered_targets = (
                filtered_targets[:top_n]
            )

        return StructuredRetrievalResult(

            disease_id=disease_id,

            disease_name=disease_name,

            total_targets=total_targets,

            retrieved_targets=retrieved_targets,

            filtered_targets=len(
                filtered_targets
            ),

            targets=filtered_targets
        )