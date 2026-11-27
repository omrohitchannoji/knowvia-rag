"""
Stage-Level Latency, Token Usage, and Cost Report Script (K-4).
Runs the evaluation set through the full RAG pipeline with PipelineTracer
and reports per-stage p50/p95 latency, tokens per query, and cost availability.
"""

import sys
import os
import json
import time
import argparse
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.config import settings
from backend.app.security.input_guardrails import InputGuardrail
from backend.app.security.output_guardrails import OutputGuardrail
from backend.app.generation.intent_router import get_intent_router, QueryIntent
from backend.app.retrieval.hybrid import get_hybrid_retriever
from backend.app.retrieval.reranker import get_reranker
from backend.app.generation.service import get_generation_service
from backend.app.services.document_service import get_document_service
from backend.app.tracing.tracer import PipelineTracer
from backend.app.evaluation.retrieval_eval import calculate_percentile_latencies


def run_latency_report(split: str = "development", output_path: Optional[str] = None):
    dataset_path = os.path.join("evaluation", "dataset.json")
    with open(dataset_path, "r", encoding="utf-8") as f:
        all_cases = json.load(f)

    cases = [c for c in all_cases if c.get("split") == split] if split != "all" else all_cases
    if not cases:
        print(f"No cases found for split '{split}'.")
        return

    # Ensure corpus is initialized for BM25
    doc_service = get_document_service()
    if not doc_service.bm25_retriever.bm25_index:
        if os.path.exists("data/TrueData"):
            doc_service.ingest_directory("data/TrueData", data_category="true")
        if os.path.exists("data/NoisyData"):
            doc_service.ingest_directory("data/NoisyData", data_category="noisy")

    router = get_intent_router()
    hybrid_retriever = get_hybrid_retriever()
    reranker = get_reranker()
    gen_service = get_generation_service()

    stages = [
        "guardrail",
        "router",
        "dense_retrieval",
        "bm25_retrieval",
        "fusion",
        "reranking",
        "generation",
        "total"
    ]
    stage_latencies: Dict[str, List[float]] = {s: [] for s in stages}
    token_totals: List[int] = []
    usage_unavailable_count = 0
    cost_totals: List[float] = []
    cost_unavailable_count = 0
    live_trace_count = 0

    for idx, case in enumerate(cases):
        query = case["query"]
        role = case.get("evaluation_role", "PUBLIC_USER")
        tracer = PipelineTracer(trace_id=f"lat_eval_{split}_{idx}")

        t0 = time.perf_counter()
        # 1. Guardrail
        t_g = time.perf_counter()
        is_safe, violation_reason = InputGuardrail.inspect_query(query)
        clean_q = InputGuardrail.sanitize_query(query)
        tracer.record_span("guardrail", (time.perf_counter() - t_g) * 1000, details={"is_safe": is_safe})

        if not is_safe:
            trace = tracer.finalize()
            for sp in trace.spans:
                if sp.stage in stage_latencies:
                    stage_latencies[sp.stage].append(sp.duration_ms)
            stage_latencies["total"].append(trace.total_latency_ms)
            usage_unavailable_count += 1
            cost_unavailable_count += 1
            continue

        # 2. Router
        t_r = time.perf_counter()
        router_usage: Dict[str, Any] = {}

        def capture_router_usage(usage: Dict[str, Any]) -> None:
            router_usage.update(usage)
            usage_available = bool(usage.get("usage_available", False))
            tracer.record_llm_usage(
                str(usage.get("model", settings.LLM_MODEL) or settings.LLM_MODEL),
                usage.get("prompt_tokens") if usage_available else None,
                usage.get("completion_tokens") if usage_available else None,
                total_tokens=usage.get("total_tokens") if usage_available else None,
                usage_available=usage_available,
                stage="router",
            )

        route_res = router.route(clean_q, usage_callback=capture_router_usage)
        router_details: Dict[str, Any] = {"intent": route_res.intent.value}
        if router_usage:
            router_details["token_usage_available"] = bool(router_usage.get("usage_available", False))
            if router_usage.get("usage_available"):
                router_details.update({
                    "input_tokens": router_usage.get("prompt_tokens"),
                    "output_tokens": router_usage.get("completion_tokens"),
                    "total_tokens": router_usage.get("total_tokens"),
                })
        tracer.record_span("router", (time.perf_counter() - t_r) * 1000, details=router_details)

        if route_res.intent == QueryIntent.CONVERSATIONAL:
            t_gn = time.perf_counter()
            gen_service.generate_conversational(clean_q)
            usage = getattr(gen_service, "last_call_usage", None) or {}
            usage = usage if isinstance(usage, dict) else {}
            u_avail = bool(usage.get("usage_available", False))
            tracer.record_llm_usage(
                str(usage.get("model", settings.LLM_MODEL) or settings.LLM_MODEL),
                usage.get("prompt_tokens") if u_avail else None,
                usage.get("completion_tokens") if u_avail else None,
                total_tokens=usage.get("total_tokens") if u_avail else None,
                usage_available=u_avail,
                stage="generation",
            )
            tracer.record_span("generation", (time.perf_counter() - t_gn) * 1000, details={"intent": "conversational"})

        elif route_res.intent in [QueryIntent.KNOWLEDGE, QueryIntent.HYBRID]:
            search_q = route_res.search_query or clean_q
            fused = hybrid_retriever.retrieve(
                query=search_q,
                user_role=role,
                top_k=settings.TOP_K_DENSE * 2,
                tracer=tracer
            )
            t_rk = time.perf_counter()
            reranked = reranker.rerank(query=search_q, candidates=fused, top_n=settings.RERANK_TOP_N)
            tracer.record_span("reranking", (time.perf_counter() - t_rk) * 1000, details={"reranked": len(reranked)})

            t_gn = time.perf_counter()
            gen_resp = gen_service.generate(query=clean_q, candidates=reranked, search_query=search_q, intent=route_res.intent.value)
            usage = getattr(gen_service, "last_call_usage", None) or {}
            usage = usage if isinstance(usage, dict) else {}
            u_avail = bool(usage.get("usage_available", False))
            tracer.record_llm_usage(
                str(usage.get("model", settings.LLM_MODEL) or settings.LLM_MODEL),
                usage.get("prompt_tokens") if u_avail else None,
                usage.get("completion_tokens") if u_avail else None,
                total_tokens=usage.get("total_tokens") if u_avail else None,
                usage_available=u_avail,
                stage="generation",
            )
            tracer.record_span("generation", (time.perf_counter() - t_gn) * 1000, details={"is_abstained": gen_resp.is_abstained})

        trace = tracer.finalize()
        if trace.langfuse_mode == "live":
            live_trace_count += 1
        for sp in trace.spans:
            if sp.stage in stage_latencies:
                stage_latencies[sp.stage].append(sp.duration_ms)
        stage_latencies["total"].append((time.perf_counter() - t0) * 1000)

        if trace.token_usage.usage_available and trace.token_usage.total_tokens is not None:
            token_totals.append(trace.token_usage.total_tokens)
        else:
            usage_unavailable_count += 1

        if trace.estimated_cost_usd is not None:
            cost_totals.append(trace.estimated_cost_usd)
        else:
            cost_unavailable_count += 1

    print("\n" + "=" * 75)
    print(f"KNOWVIA RAG PER-STAGE LATENCY & TOKEN REPORT (split={split}, n={len(cases)})")
    print("=" * 75)
    print(f"{'Stage':<20} | {'Samples':<8} | {'p50 (ms)':<12} | {'p95 (ms)':<12}")
    print("-" * 75)

    summary_stages = {}
    for stage in stages:
        vals = stage_latencies[stage]
        if vals:
            pct = calculate_percentile_latencies(vals)
            print(f"{stage:<20} | {len(vals):<8} | {pct['p50_ms']:<12.2f} | {pct['p95_ms']:<12.2f}")
            summary_stages[stage] = {"samples": len(vals), **pct}
        else:
            print(f"{stage:<20} | {0:<8} | {'N/A':<12} | {'N/A':<12}")
            summary_stages[stage] = {"samples": 0, "p50_ms": None, "p95_ms": None}

    print("-" * 75)
    if token_totals:
        avg_tokens = round(sum(token_totals) / len(token_totals), 2)
        print(f"Tokens/Query (available for {len(token_totals)}/{len(cases)}): {avg_tokens} avg tokens")
    else:
        print(f"Tokens/Query: unavailable (0/{len(cases)} queries had provider token usage; offline/mock mode)")

    if cost_totals:
        avg_cost = round(sum(cost_totals) / len(cost_totals), 6)
        print(f"Estimated Cost/Query: ${avg_cost:.6f} USD")
    else:
        print(f"Estimated Cost/Query: unavailable (pricing rates unset or provider token usage unavailable)")
    print("=" * 75)

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "split": split,
                "total_queries": len(cases),
                "langfuse_mode": "live" if live_trace_count == len(cases) else (
                    "mixed" if live_trace_count else "offline_mock"
                ),
                "live_trace_count": live_trace_count,
                "stages": summary_stages,
                "tokens_available_count": len(token_totals),
                "tokens_unavailable_count": usage_unavailable_count,
                "avg_tokens_per_query": round(sum(token_totals) / len(token_totals), 2) if token_totals else None,
                "cost_available_count": len(cost_totals),
                "cost_unavailable_count": cost_unavailable_count
            }, f, indent=2)
        print(f"Report saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Per-stage latency and token usage report.")
    parser.add_argument("--split", type=str, default="development", choices=["development", "held_out_test", "all"])
    parser.add_argument("--output", type=str, default="evaluation/results/latency_report_development.json")
    args = parser.parse_args()
    run_latency_report(split=args.split, output_path=args.output)
