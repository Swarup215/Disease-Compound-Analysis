"""
Step 7: Compound Identity & Natural-Origin Verification.

Exports:
  - CompoundVerifier: Master orchestrator for chemical resolution and origin verification.
  - PubChemClient: NCBI PubChem PUG REST API client.
  - NaturalOriginClassifier: Rule and registry-based natural vs. synthetic classifier.
  - Models: VerifiedCompound, CompoundIdentity, NaturalOriginVerification,
            NaturalOriginStatus, CompoundVerificationBatchResult.
"""

from .models import (
    CompoundIdentity,
    CompoundVerificationBatchResult,
    NaturalOriginStatus,
    NaturalOriginVerification,
    VerifiedCompound,
)
from .natural_classifier import NaturalOriginClassifier
from .pubchem_client import PubChemClient
from .verifier import CompoundVerifier

__all__ = [
    "CompoundVerifier",
    "PubChemClient",
    "NaturalOriginClassifier",
    "VerifiedCompound",
    "CompoundIdentity",
    "NaturalOriginVerification",
    "NaturalOriginStatus",
    "CompoundVerificationBatchResult",
]

