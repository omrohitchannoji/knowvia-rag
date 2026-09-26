import re
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ingestion.chunker import Chunk

ROLE_ACCESS_MAPPING = {
    "PUBLIC_USER": ["public", "PUBLIC_USER"],
    "INTERNAL_USER": ["public", "PUBLIC_USER", "internal", "INTERNAL_USER"],
    "ADMIN": ["public", "PUBLIC_USER", "internal", "INTERNAL_USER", "restricted", "ADMIN"]
}



def tokenize_text(text: str) -> List[str]:
    """
    Tokenizes text for BM25 keyword matching while preserving exact error codes,
    hyphenated identifiers (e.g. ERR-4012), code syntax, and function names.
    """
    if not text:
        return []
    # Match alphanumeric terms, preserving internal hyphens, underscores, and dots
    tokens = re.findall(r"[a-zA-Z0-9]+(?:[\-\._][a-zA-Z0-9]+)*", text.lower())
    return tokens

class BM25Retriever:
    def __init__(self):
        self.bm25_index: Optional[BM25Okapi] = None
        self.indexed_chunks: List[Chunk] = []
        self.indexed_metadata: List[Dict[str, Any]] = []

    def index_chunks(self, chunks: List[Chunk], metadata_list: List[Dict[str, Any]]):
        """
        Builds or refreshes the BM25 sparse keyword index over chunk text.
        """
        if len(chunks) != len(metadata_list):
            raise ValueError("Mismatched counts between chunks and metadata.")

        self.indexed_chunks = chunks
        self.indexed_metadata = metadata_list

        corpus_tokens = [tokenize_text(c.text) for c in chunks]
        if corpus_tokens:
            self.bm25_index = BM25Okapi(corpus_tokens)
            logger.info(f"Built BM25 Sparse Index over {len(chunks)} chunks.")
        else:
            self.bm25_index = None

    def retrieve(
        self,
        query: str,
        user_role: str = "PUBLIC_USER",
        top_k: Optional[int] = None,
        filter_status: Optional[str] = "active",
        filter_document_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes BM25 Lexical Keyword Search with Pre-Retrieval Authorization.
        """
        if not query or not query.strip():
            raise ValueError("Query string cannot be empty.")

        if self.bm25_index is None or not self.indexed_chunks:
            logger.warning("BM25 index is empty. Returning 0 candidates.")
            return []

        k = top_k or settings.TOP_K_BM25
        allowed_access_levels = ROLE_ACCESS_MAPPING.get(user_role.upper(), ["public"])

        query_tokens = tokenize_text(query)
        if not query_tokens:
            return []

        # Compute raw BM25 scores for all chunks
        raw_scores = self.bm25_index.get_scores(query_tokens)

        scored_candidates = []
        for idx, score in enumerate(raw_scores):
            if score <= 0:
                continue

            meta = self.indexed_metadata[idx]
            chunk = self.indexed_chunks[idx]

            # 1. Pre-Retrieval Authorization Filter
            if meta.get("access_level") not in allowed_access_levels:
                continue

            # 2. Document Status Filter
            if filter_status and filter_status != "all":
                if meta.get("status") != filter_status:
                    continue

            # 3. Document Type Filter
            if filter_document_type:
                if meta.get("document_type") != filter_document_type:
                    continue

            scored_candidates.append({
                "score": round(float(score), 4),
                "payload": meta,
                "text": chunk.text,
                "chunk_id": chunk.chunk_id,
                "document_id": meta.get("document_id"),
                "document_name": meta.get("document_name"),
                "access_level": meta.get("access_level"),
                "version": meta.get("version"),
                "status": meta.get("status")
            })

        # Sort candidates by BM25 score descending
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        return scored_candidates[:k]

# Singleton helper
_bm25_retriever_instance = None

def get_bm25_retriever() -> BM25Retriever:
    global _bm25_retriever_instance
    if _bm25_retriever_instance is None:
        _bm25_retriever_instance = BM25Retriever()
    return _bm25_retriever_instance

