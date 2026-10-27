"""
compound_retriever
------------------
Step 6: Natural Compound Candidate Retrieval module.

Public API
----------
NaturalCompoundRetriever   - main orchestrator (Route A + B)
CompoundCandidate          - data model for a single compound
CompoundRetrievalResult    - aggregate output of Step 6
BioactivityRecord          - ChEMBL bioactivity measurement
TargetRelation             - compound <-> target link with evidence
"""

from .models import (
    BioactivityRecord,
    CompoundCandidate,
    CompoundRetrievalResult,
    TargetRelation,
)
from .retriever import NaturalCompoundRetriever

__all__ = [
    "NaturalCompoundRetriever",
    "CompoundCandidate",
    "CompoundRetrievalResult",
    "BioactivityRecord",
    "TargetRelation",
]
