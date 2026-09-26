from typing import List, Dict, Any, Optional
from sentence_transformers import CrossEncoder
from backend.app.core.config import settings
from backend.app.core.logging import logger

class Reranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        raw_name = model_name or "cross-encoder/ms-marco-MiniLM-L-6-v2"
        self.model_name = raw_name.strip('\'"') if isinstance(raw_name, str) else raw_name
        logger.info(f"Initializing Cross-Encoder Reranker model: [{self.model_name}]")
        self.model = CrossEncoder(self.model_name)

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_n: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Reranks candidate chunks using a Cross-Encoder joint-attention model.
        
        Input:
            query (str): Natural language user question.
            candidates (List[Dict[str, Any]]): Retrieved candidate chunks from Hybrid Search.
            top_n (int): Final count of top reranked chunks to return.
            
        Output:
            List[Dict[str, Any]]: Re-ordered chunks with added 'rerank_score'.
        """
        if not candidates:
            return []

        if not query or not query.strip():
            raise ValueError("Query string cannot be empty for reranking.")

        n = top_n or settings.RERANK_TOP_N

        # Prepare pairs for Cross-Encoder: (Query, Chunk Text)
        pairs = [[query, candidate.get("text", "")] for candidate in candidates]

        # Calculate joint relevance scores using Cross-Encoder
        logger.info(f"Reranking {len(candidates)} candidates down to Top-{n} for query: '{query}'")
        raw_scores = self.model.predict(pairs)

        import math
        reranked_candidates = []
        for idx, candidate in enumerate(candidates):
            item = candidate.copy()
            # Convert raw cross-encoder logit to probability in [0, 1] using Sigmoid
            logit = float(raw_scores[idx])
            prob = 1.0 / (1.0 + math.exp(-logit))
            item["rerank_score"] = round(prob, 4)
            item["raw_rerank_score"] = round(logit, 4)
            reranked_candidates.append(item)

        # Sort descending by rerank_score
        reranked_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        return reranked_candidates[:n]


# Singleton instance
_reranker_instance = None

def get_reranker() -> Reranker:
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = Reranker()
    return _reranker_instance
