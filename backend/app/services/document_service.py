import os
import re
from typing import List, Dict, Any
from backend.app.core.logging import logger
from backend.app.ingestion.loaders import (
    load_markdown_file,
    load_pdf_file,
    load_docx_file,
    load_pptx_file,
    load_html_file,
    load_txt_file
)
from backend.app.ingestion.parser import parse_markdown_structure, ParsedSection
from backend.app.ingestion.chunker import create_structure_aware_chunks, Chunk
from backend.app.ingestion.metadata import build_chunk_metadata
from backend.app.embeddings.service import get_embedding_service, EmbeddingService
from backend.app.retrieval.vector_store import QdrantVectorStore, get_vector_store
from backend.app.retrieval.bm25 import get_bm25_retriever, BM25Retriever

def sanitize_doc_id(raw_name: str) -> str:
    """Creates a clean, safe document ID string."""
    clean = re.sub(r"[^a-zA-Z0-9_\-]", "_", raw_name)
    return f"doc_{clean.strip('_')[:50]}"

class DocumentService:
    def __init__(
        self,
        vector_store: QdrantVectorStore = None,
        embedding_service: EmbeddingService = None,
        bm25_retriever: BM25Retriever = None
    ):
        self.vector_store = vector_store or get_vector_store()
        self.embedding_service = embedding_service or get_embedding_service()
        self.bm25_retriever = bm25_retriever or get_bm25_retriever()

        self.all_chunks = []
        self.all_metadata = []
        self.sync_bm25_from_vector_store()

    def sync_bm25_from_vector_store(self):
        """
        Synchronizes the in-memory BM25 index from existing Qdrant vector store points on startup.
        """
        try:
            scroll_res = self.vector_store.client.scroll(
                collection_name=self.vector_store.collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=False
            )
            points = scroll_res[0]
            if not points:
                logger.info(f"Qdrant collection [{self.vector_store.collection_name}] is empty. BM25 count: 0.")
                return

            chunks = []
            metadata_list = []

            for point in points:
                payload = point.payload or {}
                chunk_id = payload.get("chunk_id", str(point.id))
                text = payload.get("text", "")
                if not text:
                    continue
                title = payload.get("section_title", payload.get("section", "General"))
                
                chunk = Chunk(
                    chunk_id=chunk_id,
                    text=text,
                    section_title=title,
                    breadcrumbs=[payload.get("document_name", "doc"), title],
                    page_number=payload.get("page"),
                    slide_number=payload.get("slide")
                )
                chunks.append(chunk)
                metadata_list.append(payload)

            if chunks:
                self.all_chunks = chunks
                self.all_metadata = metadata_list
                self.bm25_retriever.index_chunks(chunks, metadata_list)
                logger.info(f"Diagnostic: BM25 Index successfully synchronized with {len(chunks)} Qdrant vector store chunks.")
        except Exception as e:
            logger.warning(f"Could not auto-sync BM25 from Qdrant: {e}")

    def ingest_file(self, file_path: str, override_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Orchestrates full ingestion lifecycle for a file:
        File -> Load -> Parse -> Chunk -> Metadata -> Embed -> Vector Store Index & BM25 Index.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        override_metadata = override_metadata or {}
        ext = os.path.splitext(file_path)[1].lower()

        base_filename = os.path.basename(file_path)
        doc_name = override_metadata.get("document_name", base_filename)
        doc_id = override_metadata.get("document_id", sanitize_doc_id(os.path.splitext(base_filename)[0]))
        data_category = override_metadata.get("data_category", "true")

        merged_meta = {
            **override_metadata,
            "document_id": doc_id,
            "document_name": doc_name,
            "source_path": file_path,
            "file_type": ext.lstrip("."),
            "data_category": data_category
        }

        sections: List[ParsedSection] = []

        if ext in [".md", ".markdown"]:
            content, frontmatter = load_markdown_file(file_path)
            merged_meta.update(frontmatter)
            sections = parse_markdown_structure(content, doc_name)
            chunks = create_structure_aware_chunks(sections, doc_id, doc_name)

        elif ext == ".pdf":
            pdf_pages = load_pdf_file(file_path)
            sections = [
                ParsedSection(
                    title=f"Page {p['page_number']}",
                    level=1,
                    content=p["text"],
                    breadcrumbs=[doc_name, f"Page {p['page_number']}"]
                ) for p in pdf_pages
            ]
            chunks = create_structure_aware_chunks(sections, doc_id, doc_name)

        elif ext == ".docx":
            docx_sections = load_docx_file(file_path)
            sections = [
                ParsedSection(
                    title=s["heading"],
                    level=1,
                    content=s["text"],
                    breadcrumbs=[doc_name, s["heading"]]
                ) for s in docx_sections
            ]
            chunks = create_structure_aware_chunks(sections, doc_id, doc_name)

        elif ext == ".pptx":
            pptx_slides = load_pptx_file(file_path)
            sections = [
                ParsedSection(
                    title=s["title"],
                    level=1,
                    content=s["text"],
                    breadcrumbs=[doc_name, s["title"]]
                ) for s in pptx_slides
            ]
            chunks = create_structure_aware_chunks(sections, doc_id, doc_name)

        elif ext in [".html", ".htm"]:
            html_doc = load_html_file(file_path)
            sections = [
                ParsedSection(
                    title=html_doc["title"],
                    level=1,
                    content=html_doc["text"],
                    breadcrumbs=[doc_name, html_doc["title"]]
                )
            ]
            chunks = create_structure_aware_chunks(sections, doc_id, doc_name)

        elif ext == ".txt":
            raw_text = load_txt_file(file_path)
            sections = [
                ParsedSection(
                    title="Main Content",
                    level=1,
                    content=raw_text,
                    breadcrumbs=[doc_name, "Main Content"]
                )
            ]
            chunks = create_structure_aware_chunks(sections, doc_id, doc_name)
        else:
            logger.warning(f"Skipping unsupported file extension [{ext}] for path [{file_path}]")
            return {
                "document_id": doc_id,
                "document_name": doc_name,
                "total_chunks": 0,
                "status": "skipped",
                "message": f"Unsupported format: {ext}"
            }

        if not chunks:
            logger.warning(f"No chunks created for file [{file_path}]")
            return {
                "document_id": doc_id,
                "document_name": doc_name,
                "total_chunks": 0,
                "status": "empty",
                "message": "File contained no indexable text."
            }

        # Build Metadata List
        metadata_list = [build_chunk_metadata(chunk, merged_meta) for chunk in chunks]

        # Generate Dense Vector Embeddings
        chunk_texts = [c.text for c in chunks]
        vectors = self.embedding_service.embed_batch(chunk_texts)

        # Index into Qdrant Vector Store
        indexed_count = self.vector_store.add_chunks(chunks, vectors, metadata_list)

        # Index into BM25 Sparse Index
        self.all_chunks.extend(chunks)
        self.all_metadata.extend(metadata_list)
        self.bm25_retriever.index_chunks(self.all_chunks, self.all_metadata)

        return {
            "document_id": doc_id,
            "document_name": doc_name,
            "total_chunks": indexed_count,
            "status": "indexed",
            "message": f"Successfully indexed {indexed_count} chunks into Qdrant & BM25."
        }

    def delete_document(self, document_id: str) -> bool:
        return self.vector_store.delete_document(document_id)

    def list_documents(self) -> List[Dict[str, Any]]:
        return self.vector_store.list_documents()

    def ingest_directory(self, dir_path: str, data_category: str = "true") -> List[Dict[str, Any]]:
        """
        Recursively ingests all supported files (.md, .pdf, .docx, .pptx, .html, .txt) found in a directory.
        """
        if not os.path.exists(dir_path):
            raise FileNotFoundError(f"Directory not found: {dir_path}")

        results = []
        supported_exts = (".md", ".markdown", ".pdf", ".docx", ".pptx", ".html", ".htm", ".txt")

        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.lower().endswith(supported_exts):
                    full_path = os.path.join(root, file)
                    res = self.ingest_file(full_path, override_metadata={"data_category": data_category})
                    results.append(res)
        return results

# Singleton helper
_document_service_instance = None

def get_document_service() -> DocumentService:
    global _document_service_instance
    if _document_service_instance is None:
        _document_service_instance = DocumentService()
    return _document_service_instance
