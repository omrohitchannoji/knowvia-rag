from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    role: str = Field(description="user or assistant")
    content: str = Field(description="Message content")

class QueryRequest(BaseModel):
    query: str = Field(min_length=1, description="User question or query")
    user_role: str = Field(default="PUBLIC_USER", description="PUBLIC_USER, INTERNAL_USER, ADMIN")
    chat_history: Optional[List[ChatMessage]] = Field(default=[], description="Previous conversation turns")
    filter_document_type: Optional[str] = None
    filter_status: Optional[str] = Field(default="active", description="active, expired, archived, all")
    top_k: Optional[int] = 5

class Citation(BaseModel):
    source_index: int
    document_name: str
    section: Optional[str] = None
    page: Optional[int] = None
    version: Optional[str] = None
    access_level: str
    source_url: Optional[str] = None

class QueryResponse(BaseModel):
    query: str
    answer: str
    citations: List[Citation]
    retrieved_chunks_count: int
    is_abstained: bool = False
    latency_ms: float
    evidence_status: Optional[str] = None
    supported_aspects: Optional[List[str]] = Field(default_factory=list)
    unsupported_aspects: Optional[List[str]] = Field(default_factory=list)
