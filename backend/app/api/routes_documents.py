import os
import shutil
import tempfile
from typing import List, Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status
from backend.app.schemas.documents import DocumentUploadResponse, DocumentInfo
from backend.app.services.document_service import get_document_service
from backend.app.core.logging import logger

router = APIRouter(prefix="/documents", tags=["Document Management"])

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and Ingest Document",
    description="Uploads a Markdown (.md) or PDF (.pdf) document, parses structure, creates embeddings, and indexes into Qdrant & BM25."
)
def upload_document(
    file: UploadFile = File(...),
    access_level: Optional[str] = Form("PUBLIC_USER"),
    version: Optional[str] = Form("1.0"),
    document_type: Optional[str] = Form("technical_documentation")
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".md", ".pdf"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Only .md and .pdf files are supported."
        )

    doc_service = get_document_service()
    
    # Save UploadFile to temporary directory
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        temp_path = temp_file.name

    try:
        override_meta = {
            "document_name": file.filename,
            "access_level": access_level,
            "version": version,
            "document_type": document_type,
            "source": f"HTTP Upload ({file.filename})"
        }
        res = doc_service.ingest_file(temp_path, override_metadata=override_meta)
        return DocumentUploadResponse(**res)
    except Exception as e:
        logger.error(f"Error during file upload ingestion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}"
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@router.get(
    "/list",
    response_model=List[DocumentInfo],
    summary="List Indexed Documents",
    description="Returns a list of all unique documents currently indexed in the vector store with chunk statistics."
)
def list_documents():
    doc_service = get_document_service()
    docs = doc_service.list_documents()
    formatted_docs = []
    for d in docs:
        formatted_docs.append(DocumentInfo(
            document_id=d.get("document_id", "unknown"),
            document_name=d.get("document_name", "Unknown"),
            document_type=d.get("document_type", "technical_documentation"),
            version=d.get("version", "1.0"),
            status=d.get("status", "active"),
            access_level=d.get("access_level", "PUBLIC_USER"),
            chunk_count=d.get("chunk_count", 0)
        ))
    return formatted_docs

@router.delete(
    "/{document_id}",
    summary="Delete Document",
    description="Deletes all indexed vector points and sparse tokens associated with document_id."
)
def delete_document(document_id: str):
    doc_service = get_document_service()
    success = doc_service.delete_document(document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found or deletion failed."
        )
    return {"message": f"Successfully deleted document '{document_id}'.", "document_id": document_id}
