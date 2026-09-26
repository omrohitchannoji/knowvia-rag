"""
Automated RAG Evaluation Runner.
Evaluates benchmark test queries across 4 retrieval strategies and pipeline routing modes.
"""

import json
import os
import sys
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.document_service import get_document_service
from backend.app.retrieval.dense import get_dense_retriever
from backend.app.retrieval.bm25 import get_bm25_retriever
from backend.app.retrieval.hybrid import get_hybrid_retriever
from backend.app.retrieval.reranker import get_reranker
from backend.app.generation.service import get_generation_service
from backend.app.generation.intent_router import get_intent_router
from backend.app.security.access_control import get_allowed_access_levels
from backend.app.evaluation.retrieval_eval import (
    calculate_recall_at_k,
    calculate_mrr,
    calculate_ndcg_at_k,
    evaluate_generation_faithfulness
)

DATASET_PATH = os.path.join(os.path.dirname(__file__), "dataset.json")

def load_dataset() -> List[Dict[str, Any]]:
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def run_evaluation():
    print("=" * 80)
    print("      TECHNICAL DOCUMENTATION INTELLIGENCE RAG EVALUATION BENCHMARK      ")
    print("=" * 80)

    dataset = load_dataset()
    print(f"Loaded {len(dataset)} benchmark queries from [{DATASET_PATH}].\n")

    doc_service = get_document_service()
    doc_service.sync_bm25_from_vector_store()

    dense_retriever = get_dense_retriever()
    bm25_retriever = get_bm25_retriever()
    hybrid_retriever = get_hybrid_retriever()
    reranker = get_reranker()
    gen_service = get_generation_service()
    router = get_intent_router()

    pipeline_modes = ["Dense Only", "BM25 Only", "Hybrid (RRF)", "Hybrid + Reranker"]
    metrics = {mode: {"recall_5": [], "mrr": [], "ndcg_5": [], "groundedness": []} for mode in pipeline_modes}

    correct_intents = 0
    total_eval_items = len(dataset)

    for item in dataset:
        qid = item["id"]
        query = item["query"]
        expected_doc = item.get("expected_document")
        expected_intent = item.get("expected_intent")
        role = item.get("access_required", "PUBLIC_USER").upper()

        # Evaluate Router
        route_res = router.route(query)
        if route_res.intent.value == expected_intent:
            correct_intents += 1

        if route_res.intent.value in ["conversational", "out_of_scope"]:
            continue

        # 1. Dense Search
        dense_results = dense_retriever.retrieve(query=query, user_role=role, top_k=5)
        dense_docs = [f"{r.get('document_id', '')} {r.get('document_name', '')} {r.get('payload', {}).get('document_id', '')} {r.get('payload', {}).get('document_name', '')}" for r in dense_results]

        # 2. BM25 Search
        bm25_results = bm25_retriever.retrieve(query=query, user_role=role, top_k=5)
        bm25_docs = [f"{r.get('document_id', '')} {r.get('document_name', '')} {r.get('payload', {}).get('document_id', '')} {r.get('payload', {}).get('document_name', '')}" for r in bm25_results]

        # 3. Hybrid Search
        hybrid_results = hybrid_retriever.retrieve(query=query, user_role=role, top_k=5)
        hybrid_docs = [f"{r.get('document_id', '')} {r.get('document_name', '')} {r.get('payload', {}).get('document_id', '')} {r.get('payload', {}).get('document_name', '')}" for r in hybrid_results]

        # 4. Reranked Search
        reranked_results = reranker.rerank(query=query, candidates=hybrid_results, top_n=5)
        reranked_docs = [f"{r.get('document_id', '')} {r.get('document_name', '')} {r.get('payload', {}).get('document_id', '')} {r.get('payload', {}).get('document_name', '')}" for r in reranked_results]

        # Evaluate Generation on top reranked candidate
        gen_response = gen_service.generate(query=query, candidates=reranked_results)
        kw_score, is_safe = evaluate_generation_faithfulness(
            answer=gen_response.answer,
            expected_keywords=item.get("expected_answer_keywords", []),
            must_not_contain=item.get("must_not_contain", [])
        )

        runs = [
            ("Dense Only", dense_docs),
            ("BM25 Only", bm25_docs),
            ("Hybrid (RRF)", hybrid_docs),
            ("Hybrid + Reranker", reranked_docs)
        ]

        for mode_name, retrieved_doc_list in runs:
            r5 = calculate_recall_at_k(retrieved_doc_list, expected_doc, k=5)
            mrr = calculate_mrr(retrieved_doc_list, expected_doc)
            ndcg5 = calculate_ndcg_at_k(retrieved_doc_list, expected_doc, k=5)

            metrics[mode_name]["recall_5"].append(r5)
            metrics[mode_name]["mrr"].append(mrr)
            metrics[mode_name]["ndcg_5"].append(ndcg5)
            metrics[mode_name]["groundedness"].append(kw_score)

    intent_accuracy = round(correct_intents / total_eval_items, 4)
    print(f"Intent Classification Accuracy: {intent_accuracy * 100:.1f}%\n")

    print("-" * 80)
    print(f"{'Pipeline Mode':<22} | {'Recall@5':<10} | {'MRR':<10} | {'NDCG@5':<10} | {'Groundedness':<12}")
    print("-" * 80)

    for mode in pipeline_modes:
        count = len(metrics[mode]["recall_5"]) or 1
        avg_r5 = round(sum(metrics[mode]["recall_5"]) / count, 4)
        avg_mrr = round(sum(metrics[mode]["mrr"]) / count, 4)
        avg_ndcg5 = round(sum(metrics[mode]["ndcg_5"]) / count, 4)
        avg_grd = round(sum(metrics[mode]["groundedness"]) / count, 4)
        print(f"{mode:<22} | {avg_r5:<10.4f} | {avg_mrr:<10.4f} | {avg_ndcg5:<10.4f} | {avg_grd:<12.4f}")

    print("-" * 80)
    print("Evaluation benchmark completed successfully!\n")

if __name__ == "__main__":
    run_evaluation()
