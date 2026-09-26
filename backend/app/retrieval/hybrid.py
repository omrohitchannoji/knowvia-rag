from typing import List, Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.retrieval.dense import DenseRetriever, get_dense_retriever
from backend.app.retrieval.bm25 import BM25Retriever, get_bm25_retriever

class HybridRetriever:
    def __init__(
        self,
        dense_retriever: Optional[DenseRetriever] = None,
        bm25_retriever: Optional[BM25Retriever] = None,
        dense_weight: float = None,
        bm25_weight: float = None,
        fusion_method: str = "rrf" # "rrf" or "weighted"
    ):
        self.dense_retriever = dense_retriever or get_dense_retriever()
        self.bm25_retriever = bm25_retriever or get_bm25_retriever()
        self.dense_weight = dense_weight if dense_weight is not None else settings.DENSE_WEIGHT
        self.bm25_weight = bm25_weight if bm25_weight is not None else settings.BM25_WEIGHT
        self.fusion_method = fusion_method

    def retrieve(
        self,
        query: str,
        user_role: str = "PUBLIC_USER",
        top_k: Optional[int] = None,
        filter_status: Optional[str] = "active",
        filter_document_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes Hybrid Retrieval combining Dense Vector Search and Sparse BM25 Search.
        Applies Reciprocal Rank Fusion (RRF) to produce unified, deduplicated candidates.
        """
        k_candidate = (top_k or settings.TOP_K_DENSE) * 2

        # 1. Retrieve Candidate Lists from Dense and BM25 Retrievers
        dense_results = self.dense_retriever.retrieve(
            query=query,
            user_role=user_role,
            top_k=k_candidate,
            filter_status=filter_status,
            filter_document_type=filter_document_type
        )

        bm25_results = self.bm25_retriever.retrieve(
            query=query,
            user_role=user_role,
            top_k=k_candidate,
            filter_status=filter_status,
            filter_document_type=filter_document_type
        )

        logger.info(f"Hybrid Retrieval for query '{query}': Dense candidates={len(dense_results)}, BM25 candidates={len(bm25_results)}")

        # 2. Fuse Scores
        if self.fusion_method == "rrf":
            fused_candidates = self._reciprocal_rank_fusion(dense_results, bm25_results)
        else:
            fused_candidates = self._weighted_score_fusion(dense_results, bm25_results)

        final_k = top_k or settings.TOP_K_DENSE
        return fused_candidates[:final_k]

    def _reciprocal_rank_fusion(
        self,
        dense_results: List[Dict[str, Any]],
        bm25_results: List[Dict[str, Any]],
        rrf_k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion (RRF):
        RRF_Score(chunk) = (w_dense / (rrf_k + rank_dense)) + (w_bm25 / (rrf_k + rank_bm25))
        """
        chunk_map: Dict[str, Dict[str, Any]] = {}
        rrf_scores: Dict[str, float] = {}

        # Process Dense Ranks (1-indexed)
        for rank, item in enumerate(dense_results, start=1):
            chunk_id = item["chunk_id"]
            chunk_map[chunk_id] = item
            score = self.dense_weight / (rrf_k + rank)
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + score

        # Process BM25 Ranks (1-indexed)
        for rank, item in enumerate(bm25_results, start=1):
            chunk_id = item["chunk_id"]
            if chunk_id not in chunk_map:
                chunk_map[chunk_id] = item
            score = self.bm25_weight / (rrf_k + rank)
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + score

        # Build fused result list
        fused_list = []
        for chunk_id, item in chunk_map.items():
            fused_item = item.copy()
            fused_item["hybrid_score"] = round(rrf_scores[chunk_id], 6)
            fused_item["fusion_method"] = "RRF"
            fused_list.append(fused_item)

        fused_list.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return fused_list

    def _weighted_score_fusion(
        self,
        dense_results: List[Dict[str, Any]],
        bm25_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Min-Max Normalized Weighted Score Fusion.
        """
        chunk_map: Dict[str, Dict[str, Any]] = {}
        dense_norm: Dict[str, float] = {}
        bm25_norm: Dict[str, float] = {}

        # Normalize Dense Scores
        if dense_results:
            scores = [d["score"] for d in dense_results]
            min_s, max_s = min(scores), max(scores)
            denom = (max_s - min_s) if max_s != min_s else 1.0
            for item in dense_results:
                cid = item["chunk_id"]
                chunk_map[cid] = item
                dense_norm[cid] = (item["score"] - min_s) / denom

        # Normalize BM25 Scores
        if bm25_results:
            scores = [b["score"] for b in bm25_results]
            min_s, max_s = min(scores), max(scores)
            denom = (max_s - min_s) if max_s != min_s else 1.0
            for item in bm25_results:
                cid = item["chunk_id"]
                if cid not in chunk_map:
                    chunk_map[cid] = item
                bm25_norm[cid] = (item["score"] - min_s) / denom

        fused_list = []
        for cid, item in chunk_map.items():
            ds = dense_norm.get(cid, 0.0)
            bs = bm25_norm.get(cid, 0.0)
            fused_score = (self.dense_weight * ds) + (self.bm25_weight * bs)
            fused_item = item.copy()
            fused_item["hybrid_score"] = round(fused_score, 6)
            fused_item["fusion_method"] = "Weighted"
            fused_list.append(fused_item)

        fused_list.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return fused_list

# Singleton helper
_hybrid_retriever_instance = None

def get_hybrid_retriever() -> HybridRetriever:
    global _hybrid_retriever_instance
    if _hybrid_retriever_instance is None:
        _hybrid_retriever_instance = HybridRetriever()
    return _hybrid_retriever_instance

