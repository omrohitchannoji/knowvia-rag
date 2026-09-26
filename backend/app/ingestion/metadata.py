from typing import Dict, Any, Optional
from backend.app.schemas.documents import DocumentMetadata
from backend.app.ingestion.chunker import Chunk

def build_chunk_metadata(
    chunk: Chunk,
    doc_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Combines document-level metadata (from YAML frontmatter or file defaults)
    with chunk-level structural metadata (chunk_id, section, page, lineage).
    
    Ensures output is a JSON-serializable dictionary matching DocumentMetadata schema.
    """
    # Extract base metadata fields with default fallbacks
    document_id = doc_metadata.get("document_id", f"doc_{chunk.chunk_id.split('_chk_')[0]}")
    document_name = doc_metadata.get("document_name", "Unknown Document")
    document_type = doc_metadata.get("document_type", "technical_documentation")
    source = doc_metadata.get("source", "System Ingestion")
    source_url = doc_metadata.get("source_url", "")
    organization = doc_metadata.get("organization", "Technical Documentation Intelligence")
    data_category = doc_metadata.get("data_category", "true")
    source_path = doc_metadata.get("source_path", "")
    file_type = doc_metadata.get("file_type", "")
    version = str(doc_metadata.get("version", "1.0"))
    effective_date = doc_metadata.get("effective_date", None)
    expiration_date = doc_metadata.get("expiration_date", None)
    status = doc_metadata.get("status", "active")
    access_level = doc_metadata.get("access_level", "public")
    authority = doc_metadata.get("authority", None)
    source_type = doc_metadata.get("source_type", "official")
    supersedes_document = doc_metadata.get("supersedes_document", None)

    section = chunk.section_title
    subsection = chunk.breadcrumbs[-1] if len(chunk.breadcrumbs) > 1 else None

    meta = DocumentMetadata(
        document_id=document_id,
        chunk_id=chunk.chunk_id,
        document_name=document_name,
        document_type=document_type,
        source=source,
        source_url=source_url,
        organization=organization,
        data_category=data_category,
        source_path=source_path,
        file_type=file_type,
        section=section,
        subsection=subsection,
        page=chunk.page_number,
        slide=chunk.slide_number,
        version=version,
        effective_date=effective_date,
        expiration_date=expiration_date,
        status=status,
        access_level=access_level,
        authority=authority,
        source_type=source_type,
        supersedes_document=supersedes_document
    )

    return meta.model_dump()
