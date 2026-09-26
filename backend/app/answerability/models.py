from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class EvidenceStatus(str, Enum):
    STRONG = "STRONG"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"

class EvidenceAssessmentResult(BaseModel):
    status: EvidenceStatus = Field(description="Evidence assessment status: STRONG, PARTIAL, or INSUFFICIENT")
    confidence_signal: float = Field(description="Top reranker sigmoid probability signal")
    raw_score: float = Field(description="Top reranker raw logit score")
    evidence_score: float = Field(description="Combined multi-signal evidence confidence score")
    supported_aspects: List[str] = Field(default_factory=list, description="Aspects/topics supported by retrieved evidence")
    unsupported_aspects: List[str] = Field(default_factory=list, description="Requested aspects not covered by retrieved evidence")
    supporting_documents: List[Dict[str, Any]] = Field(default_factory=list, description="Metadata of valid supporting chunks")
    reason: str = Field(description="Rationale for the evidence status decision")
