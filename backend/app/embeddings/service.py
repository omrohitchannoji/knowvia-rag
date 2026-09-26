from typing import List, Union
from sentence_transformers import SentenceTransformer
from backend.app.core.config import settings
from backend.app.core.logging import logger

class EmbeddingService:
    def __init__(self, model_name: str = None):
        raw_name = model_name or settings.EMBEDDING_MODEL
        self.model_name = raw_name.strip('\'"') if isinstance(raw_name, str) else raw_name
        logger.info(f"Initializing EmbeddingService with model: [{self.model_name}]")
        self.model = SentenceTransformer(self.model_name)
        if hasattr(self.model, "get_sentence_embedding_dimension"):
            self.dimension = self.model.get_sentence_embedding_dimension()
        elif hasattr(self.model, "get_embedding_dimension"):
            self.dimension = self.model.get_embedding_dimension()
        else:
            self.dimension = settings.EMBEDDING_DIMENSION
        
    def embed_text(self, text: str) -> List[float]:
        """
        Embeds a single string query or document chunk into a dense vector.
        """
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty string.")
        embedding = self.model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        return embedding.tolist()

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Embeds a list of string chunks in batches for high throughput.
        """
        if not texts:
            return []
        embeddings = self.model.encode(
            texts, 
            batch_size=batch_size, 
            convert_to_numpy=True, 
            show_progress_bar=False
        )
        return embeddings.tolist()

# Singleton instance for application reuse
_embedding_service_instance = None

def get_embedding_service() -> EmbeddingService:
    global _embedding_service_instance
    if _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingService()
    return _embedding_service_instance
