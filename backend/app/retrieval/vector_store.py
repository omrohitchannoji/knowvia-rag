import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ingestion.chunker import Chunk

class QdrantVectorStore:
    def __init__(
        self,
        collection_name: Optional[str] = None,
        path: Optional[str] = None,
        location: Optional[str] = None,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        vector_size: int = 384
    ):
        self.collection_name = collection_name or settings.COLLECTION_NAME
        self.vector_size = vector_size or settings.EMBEDDING_DIMENSION

        # Client Connection Setup
        if url or settings.QDRANT_URL:
            logger.info(f"Connecting to Cloud Qdrant Vector DB at [{url or settings.QDRANT_URL}]")
            self.client = QdrantClient(
                url=url or settings.QDRANT_URL,
                api_key=api_key or settings.QDRANT_API_KEY
            )
        elif location == ":memory:":
            logger.info("Initializing in-memory Qdrant Vector DB for testing")
            self.client = QdrantClient(location=":memory:")
        else:
            storage_path = path or settings.QDRANT_STORAGE_PATH
            logger.info(f"Initializing local persistent Qdrant Vector DB at [{storage_path}]")
            self.client = QdrantClient(path=storage_path)

        self._ensure_collection_exists()

    def _ensure_payload_indexes(self):
        """Creates required payload indexes for metadata filtering on Qdrant Cloud."""
        for field in ["access_level", "status", "document_type", "document_id"]:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD
                )
            except Exception as e:
                logger.debug(f"Payload index for field [{field}] notice: {e}")

    def _ensure_collection_exists(self):
        """Creates the Qdrant vector collection if it does not already exist."""
        collections = self.client.get_collections().collections
        existing_names = [c.name for c in collections]
        
        if self.collection_name not in existing_names:
            logger.info(f"Creating Qdrant Collection [{self.collection_name}] with Cosine distance...")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
        self._ensure_payload_indexes()

    def recreate_collection(self):
        """Deletes existing collection if present and creates a fresh collection."""
        collections = self.client.get_collections().collections
        existing_names = [c.name for c in collections]

        if self.collection_name in existing_names:
            logger.info(f"Deleting existing Qdrant Collection [{self.collection_name}] for fresh re-indexation...")
            self.client.delete_collection(collection_name=self.collection_name)

        logger.info(f"Creating fresh Qdrant Collection [{self.collection_name}]...")
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE
            )
        )
        self._ensure_payload_indexes()

    def add_chunks(
        self,
        chunks: List[Chunk],
        vectors: List[List[float]],
        metadata_list: List[Dict[str, Any]]
    ) -> int:
        """
        Inserts vector embeddings, chunk text, and metadata payloads into Qdrant.
        """
        if len(chunks) != len(vectors) or len(chunks) != len(metadata_list):
            raise ValueError("Mismatched counts between chunks, vectors, and metadata.")

        points = []
        for chunk, vector, meta in zip(chunks, vectors, metadata_list):
            payload = meta.copy()
            payload["text"] = chunk.text
            payload["section_title"] = chunk.section_title
            payload["chunk_id"] = chunk.chunk_id
            
            # Use deterministic UUID string based on chunk_id
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk.chunk_id))
            
            points.append(models.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            ))

        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        logger.info(f"Successfully indexed {len(points)} points into Qdrant collection [{self.collection_name}]")
        return len(points)

    def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        allowed_access_levels: Optional[List[str]] = None,
        filter_status: Optional[str] = "active",
        filter_document_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Performs dense vector similarity search with pre-retrieval metadata filtering.
        """
        must_filters = []

        # 1. Pre-Retrieval Authorization Filter (access_level)
        if allowed_access_levels:
            must_filters.append(
                models.FieldCondition(
                    key="access_level",
                    match=models.MatchAny(any=allowed_access_levels)
                )
            )

        # 2. Document Status Filter (active vs expired vs all)
        if filter_status and filter_status != "all":
            must_filters.append(
                models.FieldCondition(
                    key="status",
                    match=models.MatchValue(value=filter_status)
                )
            )

        # 3. Document Type Filter
        if filter_document_type:
            must_filters.append(
                models.FieldCondition(
                    key="document_type",
                    match=models.MatchValue(value=filter_document_type)
                )
            )

        query_filter = models.Filter(must=must_filters) if must_filters else None

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k
        )

        formatted_results = []
        for point in results.points:
            formatted_results.append({
                "score": round(float(point.score), 4),
                "payload": point.payload,
                "text": point.payload.get("text", ""),
                "chunk_id": point.payload.get("chunk_id"),
                "document_id": point.payload.get("document_id"),
                "document_name": point.payload.get("document_name"),
                "access_level": point.payload.get("access_level"),
                "version": point.payload.get("version"),
                "status": point.payload.get("status")
            })

        return formatted_results

    def delete_document(self, document_id: str) -> bool:
        """
        Deletes all vector points associated with a specific document_id.
        """
        delete_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchValue(value=document_id)
                )
            ]
        )
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(filter=delete_filter)
        )
        logger.info(f"Deleted vector points for document_id [{document_id}]")
        return True

    def list_documents(self) -> List[Dict[str, Any]]:
        """
        Scans collection payloads to return unique indexed documents and chunk counts.
        """
        scroll_res = self.client.scroll(
            collection_name=self.collection_name,
            limit=1000,
            with_payload=True,
            with_vectors=False
        )

        docs_summary: Dict[str, Dict[str, Any]] = {}
        for point in scroll_res[0]:
            payload = point.payload
            doc_id = payload.get("document_id")
            if doc_id:
                if doc_id not in docs_summary:
                    docs_summary[doc_id] = {
                        "document_id": doc_id,
                        "document_name": payload.get("document_name"),
                        "document_type": payload.get("document_type"),
                        "version": payload.get("version"),
                        "status": payload.get("status"),
                        "access_level": payload.get("access_level"),
                        "chunk_count": 0
                    }
                docs_summary[doc_id]["chunk_count"] += 1

        return list(docs_summary.values())

    def get_document_count(self) -> int:
        """Returns total count of points/chunks indexed in the collection."""
        try:
            info = self.client.get_collection(collection_name=self.collection_name)
            return info.points_count or 0
        except Exception:
            return 0

# Singleton helper
_vector_store_instance = None

def get_vector_store() -> QdrantVectorStore:
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = QdrantVectorStore()
    return _vector_store_instance


