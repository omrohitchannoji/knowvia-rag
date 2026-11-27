"""
Automated RAG Retrieval & Abstention Ablation Benchmark Runner (K-1).
Evaluates development and held-out test sets across 5 pipeline modes WITHOUT
calling the LLM generator or Tier 2 LLM router:
  1. Dense Only
  2. BM25 Only
  3. Hybrid (RRF)
  4. Hybrid + Reranker
  5. Hybrid + Reranker + Abstention

Uses an isolated local/in-memory Qdrant collection built from the repository
corpus using Knowvia's standard ingestion/chunking pipeline. Never alters Qdrant Cloud.
"""

import argparse
import datetime
import json
import os
import sys
import time
from typing import List, Dict, Any, Optional

# Ensure repository root is on Python sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.config import settings
from backend.app.embeddings.service import get_embedding_service
from backend.app.retrieval.vector_store import QdrantVectorStore
from backend.app.retrieval.dense import DenseRetriever
from backend.app.retrieval.bm25 import BM25Retriever
from backend.app.retrieval.hybrid import HybridRetriever
from backend.app.retrieval.reranker import get_reranker
from backend.app.services.document_service import DocumentService
from backend.app.generation.intent_router import IntentRouter, QueryIntent
from backend.app.generation.llm import BaseLLMClient
from backend.app.answerability.evaluator import EvidenceEvaluator
from backend.app.answerability.models import EvidenceStatus
from backend.app.evaluation.retrieval_eval import (
    calculate_recall_at_k,
    calculate_mrr,
    calculate_ndcg_at_k,
    calculate_percentile_latencies,
    calculate_abstention_metrics,
)

DATASET_PATH = os.path.join(os.path.dirname(__file__), "dataset.json")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


class _NoOpDeterministicRouterClient(BaseLLMClient):
    """Forces IntentRouter to use Tier 1 deterministic patterns and fallback rules without any LLM API call."""
    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        return ""


def load_dataset(split_filter: Optional[str] = "development") -> List[Dict[str, Any]]:
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if split_filter and split_filter != "all":
        data = [item for item in data if item.get("split") == split_filter]
    return data


def build_local_corpus_index() -> Dict[str, Any]:
    """
    Builds an isolated in-memory Qdrant + BM25 index from the repository corpus
    using Knowvia's standard DocumentService ingestion and chunking settings.
    Does NOT connect to, write to, delete from, or alter Qdrant Cloud.
    """
    embedder = get_embedding_service()
    local_vstore = QdrantVectorStore(collection_name="eval_local_k1", location=":memory:")
    local_bm25 = BM25Retriever()
    doc_service = DocumentService(
        vector_store=local_vstore,
        embedding_service=embedder,
        bm25_retriever=local_bm25
    )

    corpus_dirs = [
        ("data/TrueData", "true"),
        ("data/NoisyData", "noisy"),
        ("data/synthetic_policies", "true"),
        ("data/technical", "true"),
    ]
    ingested_dirs = []
    for dir_path, data_cat in corpus_dirs:
        if os.path.exists(dir_path):
            doc_service.ingest_directory(dir_path, data_category=data_cat)
            ingested_dirs.append(dir_path)

    indexed_doc_ids = sorted({
        m.get("document_id") for m in doc_service.all_metadata if m.get("document_id")
    })
    indexed_doc_names = sorted({
        m.get("document_name") for m in doc_service.all_metadata if m.get("document_name")
    })
    qdrant_points = local_vstore.client.count(collection_name="eval_local_k1").count

    return {
        "embedder": embedder,
        "vector_store": local_vstore,
        "bm25_retriever": local_bm25,
        "dense_retriever": DenseRetriever(vector_store=local_vstore, embedding_service=embedder),
        "hybrid_retriever": HybridRetriever(
            dense_retriever=DenseRetriever(vector_store=local_vstore, embedding_service=embedder),
            bm25_retriever=local_bm25
        ),
        "ingested_dirs": ingested_dirs,
        "total_chunks": len(doc_service.all_chunks),
        "qdrant_points": qdrant_points,
        "indexed_doc_ids": indexed_doc_ids,
        "indexed_doc_names": indexed_doc_names,
    }


def run_evaluation(
    split: str = "development",
    modes_to_run: Optional[List[str]] = None,
    top_k: int = 5,
    save_results: bool = True,
) -> Dict[str, Any]:
    dataset = load_dataset(split)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("=" * 92)
    print(f"   KNOWVIA AI K-1 RETRIEVAL & ABSTENTION BENCHMARK (NO LLM) — SPLIT: {split.upper()}   ")
    print("=" * 92)
    print(f"Loaded {len(dataset)} cases from [{DATASET_PATH}] for split: '{split}'.")

    # Build isolated in-memory Qdrant + BM25 index
    idx_info = build_local_corpus_index()
    dense_retriever = idx_info["dense_retriever"]
    bm25_retriever = idx_info["bm25_retriever"]
    hybrid_retriever = idx_info["hybrid_retriever"]
    reranker = get_reranker()
    router = IntentRouter(llm_client=_NoOpDeterministicRouterClient())
    evidence_evaluator = EvidenceEvaluator()

    # Map dataset logical IDs to actual sanitized document_ids produced by DocumentService
    EXPECTED_DOC_ID_ALIASES = {
        "doc_5_level_paging_and_5_level_ept": "doc_5-Level_Paging_and_5-Level_EPT_-_Intel_-_Revision_",
    }

    # Verify expected documents exist in local index
    expected_docs_in_split = sorted({
        item["expected_document"] for item in dataset if item.get("expected_document")
    })
    indexed_id_set = set(idx_info["indexed_doc_ids"])
    missing_expected_docs = [
        d for d in expected_docs_in_split
        if EXPECTED_DOC_ID_ALIASES.get(d, d) not in indexed_id_set
    ]

    print(f"Local In-Memory Index Built: {idx_info['total_chunks']} chunks | {idx_info['qdrant_points']} Qdrant points")
    print(f"Ingested Directories: {idx_info['ingested_dirs']}")
    print(f"Actual Indexed Document IDs ({len(idx_info['indexed_doc_ids'])}): {idx_info['indexed_doc_ids']}")
    print(f"Expected Corpus Documents ({len(expected_docs_in_split)}): {expected_docs_in_split}")
    print(f"Document ID Aliases Applied: {EXPECTED_DOC_ID_ALIASES}")
    print(f"Missing Expected Documents in Local Index: {missing_expected_docs}\n")

    all_pipeline_modes = [
        "Dense Only",
        "BM25 Only",
        "Hybrid (RRF)",
        "Hybrid + Reranker",
        "Hybrid + Reranker + Abstention"
    ]
    if modes_to_run:
        selected_modes = [
            m for m in all_pipeline_modes
            if m.lower().replace(" ", "_").replace("+", "_").replace("(", "").replace(")", "") in modes_to_run
            or m in modes_to_run
        ]
        if not selected_modes:
            selected_modes = all_pipeline_modes
    else:
        selected_modes = all_pipeline_modes

    mode_results = {
        mode: {
            "doc_recall_k": [],
            "doc_mrr": [],
            "doc_ndcg_k": [],
            "latencies_ms": [],
            "predicted_abstain": [],
            "ground_truth_abstain": [],
        }
        for mode in selected_modes
    }

    excluded_from_doc_metrics = []
    per_query_records = []
    correct_intents = 0

    for item in dataset:
        qid = item["id"]
        query = item["query"]
        expected_doc = item.get("expected_document")
        expected_intent = item.get("expected_intent")
        should_abstain = bool(item.get("should_abstain", False))
        eval_role = item.get("evaluation_role", "PUBLIC_USER").upper()

        # 1. Deterministic Router (no Tier 2 LLM call)
        t_route0 = time.perf_counter()
        route_res = router.route(query)
        route_lat = (time.perf_counter() - t_route0) * 1000
        is_intent_correct = (route_res.intent.value == expected_intent)
        if is_intent_correct:
            correct_intents += 1

        if not expected_doc:
            excluded_from_doc_metrics.append({
                "id": qid,
                "category": item.get("category"),
                "reason": "expected_document is null (conversational, out_of_scope, unanswerable, or RBAC-blocked)"
            })

        query_record = {
            "id": qid,
            "query": query,
            "category": item.get("category"),
            "expected_document": expected_doc,
            "expected_chunk_ids": None,
            "expected_intent": expected_intent,
            "routed_intent": route_res.intent.value,
            "intent_correct": is_intent_correct,
            "should_abstain": should_abstain,
            "evaluation_role": eval_role,
            "mode_evaluations": {}
        }

        # Deterministic non-retrieval routes
        if route_res.intent in [QueryIntent.CONVERSATIONAL, QueryIntent.OUT_OF_SCOPE]:
            is_abs = (route_res.intent == QueryIntent.OUT_OF_SCOPE)
            for mode in selected_modes:
                mode_results[mode]["latencies_ms"].append(route_lat)
                mode_results[mode]["predicted_abstain"].append(is_abs)
                mode_results[mode]["ground_truth_abstain"].append(should_abstain)
                # Note: if an answerable query with expected_doc was misrouted to bypass, count 0.0 on doc metrics
                if expected_doc:
                    mode_results[mode]["doc_recall_k"].append(0.0)
                    mode_results[mode]["doc_mrr"].append(0.0)
                    mode_results[mode]["doc_ndcg_k"].append(0.0)

            query_record["mode_evaluations"]["deterministic_bypass"] = {
                "routed_intent": route_res.intent.value,
                "latency_ms": round(route_lat, 2),
                "is_abstained": is_abs,
                "doc_metrics_applicable": bool(expected_doc),
            }
            per_query_records.append(query_record)
            continue

        # --- Retrieval Stages ---
        t_d0 = time.perf_counter()
        dense_results = dense_retriever.retrieve(query=query, user_role=eval_role, top_k=top_k)
        dense_lat = route_lat + (time.perf_counter() - t_d0) * 1000
        dense_docs = [f"{r.get('document_id', '')} {r.get('document_name', '')}" for r in dense_results]

        t_b0 = time.perf_counter()
        bm25_results = bm25_retriever.retrieve(query=query, user_role=eval_role, top_k=top_k)
        bm25_lat = route_lat + (time.perf_counter() - t_b0) * 1000
        bm25_docs = [f"{r.get('document_id', '')} {r.get('document_name', '')}" for r in bm25_results]

        t_h0 = time.perf_counter()
        hybrid_candidates = hybrid_retriever.retrieve(query=query, user_role=eval_role, top_k=top_k)
        hybrid_lat = route_lat + (time.perf_counter() - t_h0) * 1000
        hybrid_docs = [f"{r.get('document_id', '')} {r.get('document_name', '')}" for r in hybrid_candidates]

        t_r0 = time.perf_counter()
        reranked_candidates = reranker.rerank(query=query, candidates=hybrid_candidates, top_n=top_k)
        rerank_lat = hybrid_lat + (time.perf_counter() - t_r0) * 1000
        reranked_docs = [f"{r.get('document_id', '')} {r.get('document_name', '')}" for r in reranked_candidates]

        # EvidenceEvaluator Abstention Check (no LLM generation call)
        t_e0 = time.perf_counter()
        assessment = evidence_evaluator.assess(
            query=query,
            search_query=query,
            intent=route_res.intent.value,
            candidates=reranked_candidates
        )
        abstain_lat = rerank_lat + (time.perf_counter() - t_e0) * 1000
        eval_abstained = (assessment.status == EvidenceStatus.INSUFFICIENT)

        runs = [
            ("Dense Only", dense_docs, dense_results, dense_lat, len(dense_results) == 0),
            ("BM25 Only", bm25_docs, bm25_results, bm25_lat, len(bm25_results) == 0),
            ("Hybrid (RRF)", hybrid_docs, hybrid_candidates, hybrid_lat, len(hybrid_candidates) == 0),
            ("Hybrid + Reranker", reranked_docs, reranked_candidates, rerank_lat, len(reranked_candidates) == 0),
            ("Hybrid + Reranker + Abstention", reranked_docs, reranked_candidates, abstain_lat, eval_abstained),
        ]

        for mode_name, retrieved_doc_list, cand_objs, lat_ms, is_abstained in runs:
            if mode_name not in selected_modes:
                continue

            mode_results[mode_name]["latencies_ms"].append(lat_ms)
            mode_results[mode_name]["predicted_abstain"].append(is_abstained)
            mode_results[mode_name]["ground_truth_abstain"].append(should_abstain)

            if expected_doc:
                target_doc_id = EXPECTED_DOC_ID_ALIASES.get(expected_doc, expected_doc)
                r_k = calculate_recall_at_k(retrieved_doc_list, target_doc_id, k=top_k)
                mrr_val = calculate_mrr(retrieved_doc_list, target_doc_id)
                ndcg_val = calculate_ndcg_at_k(retrieved_doc_list, target_doc_id, k=top_k)
                mode_results[mode_name]["doc_recall_k"].append(r_k)
                mode_results[mode_name]["doc_mrr"].append(mrr_val)
                mode_results[mode_name]["doc_ndcg_k"].append(ndcg_val)
            else:
                r_k, mrr_val, ndcg_val = None, None, None

            query_record["mode_evaluations"][mode_name] = {
                "doc_recall_k": r_k,
                "doc_mrr": mrr_val,
                "doc_ndcg_k": ndcg_val,
                "chunk_metrics": "unavailable (no ground-truth chunk IDs)",
                "latency_ms": round(lat_ms, 2),
                "is_abstained": is_abstained,
                "evidence_status": assessment.status.value if mode_name == "Hybrid + Reranker + Abstention" else None,
                "evidence_reason": assessment.reason if mode_name == "Hybrid + Reranker + Abstention" else None,
                "retrieved_doc_ids": [c.get("document_id") for c in cand_objs],
            }

        per_query_records.append(query_record)

    summary_report = {
        "benchmark_type": "K-1 Retrieval & Abstention Ablation (No LLM Generator / No Tier 2 LLM Router)",
        "dataset_version": "2.0-sixty-cases",
        "split": split,
        "total_cases": len(dataset),
        "doc_metric_cases": len(dataset) - len(excluded_from_doc_metrics),
        "excluded_from_doc_metrics": excluded_from_doc_metrics,
        "chunk_level_metrics": "unavailable (0 cases have ground-truth chunk IDs)",
        "abstention_metric_cases": len(dataset),
        "local_index_verification": {
            "qdrant_mode": "in-memory (:memory:)",
            "total_chunks": idx_info["total_chunks"],
            "qdrant_points": idx_info["qdrant_points"],
            "ingested_dirs": idx_info["ingested_dirs"],
            "actual_indexed_doc_ids": idx_info["indexed_doc_ids"],
            "document_id_aliases": EXPECTED_DOC_ID_ALIASES,
            "expected_docs_present": expected_docs_in_split,
            "missing_expected_docs": missing_expected_docs,
        },
        "router_accuracy_deterministic": round(correct_intents / len(dataset), 4),
        "evaluation_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": " ".join(sys.argv),
        "modes": {}
    }

    print("-" * 92)
    print(f"{'Pipeline Mode':<30} | {'DocR@5':<8} | {'DocMRR':<8} | {'DocNDCG@5':<9} | {'Abs-P':<8} | {'Abs-R':<8} | {'p50(ms)':<8} | {'p95(ms)':<8}")
    print("-" * 92)

    for mode in selected_modes:
        doc_cnt = len(mode_results[mode]["doc_recall_k"]) or 1
        avg_rec = round(sum(mode_results[mode]["doc_recall_k"]) / doc_cnt, 4)
        avg_mrr = round(sum(mode_results[mode]["doc_mrr"]) / doc_cnt, 4)
        avg_ndcg = round(sum(mode_results[mode]["doc_ndcg_k"]) / doc_cnt, 4)

        abs_metrics = calculate_abstention_metrics(
            mode_results[mode]["predicted_abstain"],
            mode_results[mode]["ground_truth_abstain"]
        )
        lat_stats = calculate_percentile_latencies(mode_results[mode]["latencies_ms"])

        summary_report["modes"][mode] = {
            "doc_recall_5": avg_rec,
            "doc_mrr": avg_mrr,
            "doc_ndcg_5": avg_ndcg,
            "chunk_recall_5": "unavailable",
            "chunk_mrr": "unavailable",
            "chunk_ndcg_5": "unavailable",
            "abstention_metrics": abs_metrics,
            "latency_percentiles": lat_stats
        }

        print(
            f"{mode:<30} | {avg_rec:<8.4f} | {avg_mrr:<8.4f} | {avg_ndcg:<9.4f} | "
            f"{abs_metrics['abstention_precision']:<8.4f} | {abs_metrics['abstention_recall']:<8.4f} | "
            f"{lat_stats['p50_ms']:<8.1f} | {lat_stats['p95_ms']:<8.1f}"
        )

    print("-" * 92)
    print(f"Document-level metrics evaluated on {summary_report['doc_metric_cases']}/{len(dataset)} cases "
          f"({len(excluded_from_doc_metrics)} excluded: expected_document is null).")
    print("Chunk-level metrics: unavailable (no ground-truth chunk IDs in dataset).")
    print(f"Deterministic Router Intent Classification Accuracy: {summary_report['router_accuracy_deterministic'] * 100:.1f}%\n")

    if save_results:
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = os.path.join(RESULTS_DIR, f"eval_run_{timestamp_str}_{split}_k1_no_llm.json")
        full_payload = {
            "summary": summary_report,
            "per_query_evaluations": per_query_records
        }
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(full_payload, f, indent=2)
        print(f"Artifact Saved: Full per-query judgments and aggregate metrics stored at [{out_file}].\n")

    return summary_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run K-1 Retrieval & Abstention Ablation Benchmark (No LLM)")
    parser.add_argument("--split", choices=["development", "held_out_test", "all"], default="development", help="Dataset split to evaluate")
    parser.add_argument("--mode", choices=["all", "dense_only", "bm25_only", "hybrid", "hybrid_reranker", "hybrid_reranker_abstain"], default="all", help="Pipeline ablation mode to evaluate")
    parser.add_argument("--top-k", type=int, default=5, help="Top-K candidate count")
    parser.add_argument("--no-save", action="store_true", help="Disable saving results to file")
    args = parser.parse_args()

    modes = None if args.mode == "all" else [args.mode]
    run_evaluation(
        split=args.split,
        modes_to_run=modes,
        top_k=args.top_k,
        save_results=not args.no_save
    )
