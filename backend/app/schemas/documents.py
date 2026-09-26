from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class DocumentMetadata(BaseModel):
    document_id: str
    chunk_id: Optional[str] = None
    document_name: str
    document_type: str = Field(description="policy, technical_documentation, api_reference, troubleshooting, standard, faq")
    source: str
    source_url: Optional[str] = None
    organization: Optional[str] = None
    data_category: str = Field(default="true", description="true, noisy")
    source_path: Optional[str] = None
    file_type: Optional[str] = None
    slide: Optional[int] = None
    section: Optional[str] = None
    subsection: Optional[str] = None
    page: Optional[int] = None
    version: Optional[str] = "1.0"
    effective_date: Optional[str] = None
    expiration_date: Optional[str] = None
    status: str = Field(default="active", description="draft, active, expired, archived")
    access_level: str = Field(default="public", description="public, internal, restricted")
    authority: Optional[str] = None
    source_type: str = Field(default="official", description="official, synthetic_policy")
    supersedes_document: Optional[str] = None

class DocumentUploadResponse(BaseModel):
    document_id: str
    document_name: str
    total_chunks: int
    status: str
    message: str

class DocumentInfo(BaseModel):
    document_id: str
    document_name: str
    document_type: str
    version: Optional[str]
    status: str
    access_level: str
    chunk_count: int
