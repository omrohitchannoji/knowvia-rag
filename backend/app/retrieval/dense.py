from typing import List, Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.embeddings.service import get_embedding_service, EmbeddingService
from backend.app.retrieval.vector_store import QdrantVectorStore, get_vector_store

ROLE_ACCESS_MAPPING = {
    "PUBLIC_USER": ["public", "PUBLIC_USER"],
    "INTERNAL_USER": ["public", "PUBLIC_USER", "internal", "INTERNAL_USER"],
    "ADMIN": ["public", "PUBLIC_USER", "internal", "INTERNAL_USER", "restricted", "ADMIN"]
}



class DenseRetriever:
    def __init__(
        self,
        vector_store: Optional[QdrantVectorStore] = None,
        embedding_service: Optional[EmbeddingService] = None
    ):
        self.vector_store = vector_store or get_vector_store()
        self.embedding_service = embedding_service or get_embedding_service()


    def retrieve(
        self,
        query: str,
        user_role: str = "PUBLIC_USER",
        top_k: Optional[int] = None,
        filter_status: Optional[str] = "active",
        filter_document_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes Dense Semantic Vector Search with Pre-Retrieval Authorization.
        
        Steps:
        1. Validate query string.
        2. Map user_role to allowed access_level list.
        3. Generate query vector using EmbeddingService.
        4. Execute Qdrant vector search with metadata filters.
        """
        if not query or not query.strip():
            raise ValueError("Query string cannot be empty.")

        k = top_k or settings.TOP_K_DENSE
        allowed_access_levels = ROLE_ACCESS_MAPPING.get(user_role.upper(), ["public"])

        logger.info(f"Dense Search for Query: '{query}' | Role: {user_role} -> Access: {allowed_access_levels} | Top-K: {k}")

        # Generate Dense Vector for User Query
        query_vector = self.embedding_service.embed_text(query)

        # Execute Pre-Retrieval Authorized Similarity Search in Qdrant
        results = self.vector_store.similarity_search(
            query_vector=query_vector,
            top_k=k,
            allowed_access_levels=allowed_access_levels,
            filter_status=filter_status,
            filter_document_type=filter_document_type
        )

        return results

# Singleton helper
_dense_retriever_instance = None

def get_dense_retriever() -> DenseRetriever:
    global _dense_retriever_instance
    if _dense_retriever_instance is None:
        _dense_retriever_instance = DenseRetriever()
    return _dense_retriever_instance

