"""
Generation Quality Evaluation Script (K-2).
Measures Answer Faithfulness and Answer Relevancy using an LLM judge DIFFERENT
from the generator model (e.g., generator=openai/gpt-oss-20b, judge=qwen/qwen3.8-27b).
Saves one row per question to CSV. Never fabricates scores when the judge LLM is unavailable.
"""

import sys
import os
import csv
import json
import re
import argparse
from typing import Dict, Any, Optional, Tuple, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.retrieval.hybrid import get_hybrid_retriever
from backend.app.retrieval.reranker import get_reranker
from backend.app.generation.service import get_generation_service
from backend.app.generation.intent_router import get_intent_router, QueryIntent
from backend.app.services.document_service import get_document_service


JUDGE_SYSTEM_PROMPT = """You are an impartial RAG evaluation judge.
Given a USER QUESTION, RETRIEVED EVIDENCE, and a GENERATED ANSWER, evaluate:
1. faithfulness (float 0.0 to 1.0): Are all factual claims in the generated answer strictly supported by the retrieved evidence (or appropriately abstaining when evidence is insufficient)?
2. answer_relevancy (float 0.0 to 1.0): Does the generated answer directly and coherently address the user question?

Respond ONLY with a valid JSON object:
{
  "faithfulness": <float 0.0-1.0>,
  "answer_relevancy": <float 0.0-1.0>,
  "rationale": "<brief explanation>"
}
"""


class SeparateLLMJudge:
    """
    Independent LLM Judge using a model strictly different from the generator.
    """
    def __init__(self, judge_provider: str = "groq", judge_model: str = "qwen/qwen3.8-27b"):
        self.judge_provider = judge_provider
        self.judge_model = judge_model
        if self.judge_model == settings.LLM_MODEL:
            raise ValueError(
                f"Judge model ({self.judge_model}) must be different from generator model ({settings.LLM_MODEL})."
            )

    def evaluate(
        self,
        question: str,
        answer: str,
        evidence_text: str
    ) -> Tuple[Optional[float], Optional[float], str]:
        """
        Returns (faithfulness_score, answer_relevancy_score, error_message).
        If the judge API is unavailable or fails, returns (None, None, error_str) without fabricating scores.
        """
        api_key = os.getenv("GROQ_API_KEY") or settings.GROQ_API_KEY
        if not api_key or api_key == "your_groq_api_key_here":
            return None, None, "Judge LLM unavailable: GROQ_API_KEY not configured."

        user_prompt = (
            f"USER QUESTION:\n{question}\n\n"
            f"RETRIEVED EVIDENCE:\n{evidence_text[:4000]}\n\n"
            f"GENERATED ANSWER:\n{answer}"
        )

        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            response = client.chat.completions.create(
                model=self.judge_model,
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0
            )
            raw = response.choices[0].message.content or ""
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                return None, None, f"Judge returned non-JSON output: {raw[:120]}"
            parsed = json.loads(match.group(0))
            faith = float(parsed["faithfulness"])
            rel = float(parsed["answer_relevancy"])
            return round(min(max(faith, 0.0), 1.0), 4), round(min(max(rel, 0.0), 1.0), 4), ""
        except Exception as e:
            return None, None, f"Judge API error: {str(e)}"


def run_generation_eval(
    split: str = "development",
    output_csv: str = "evaluation/results/generation_eval_results.csv",
    judge_provider: str = "groq",
    judge_model: str = "qwen/qwen3.8-27b"
):
    dataset_path = os.path.join("evaluation", "dataset.json")
    with open(dataset_path, "r", encoding="utf-8") as f:
        all_cases = json.load(f)

    cases = [c for c in all_cases if c.get("split") == split] if split != "all" else all_cases
    if not cases:
        print(f"No cases found for split '{split}'.")
        return

    # Ensure BM25 corpus is loaded
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
    judge = SeparateLLMJudge(judge_provider=judge_provider, judge_model=judge_model)

    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    rows: List[Dict[str, Any]] = []

    for case in cases:
        qid = case["id"]
        query = case["query"]
        role = case.get("evaluation_role", "PUBLIC_USER")

        route_res = router.route(query)
        if route_res.intent == QueryIntent.CONVERSATIONAL:
            answer = gen_service.generate_conversational(query)
            citations_str = "none (conversational)"
            evidence_text = ""
        elif route_res.intent == QueryIntent.OUT_OF_SCOPE:
            answer = "I am unable to answer based on the provided context."
            citations_str = "none (out_of_scope)"
            evidence_text = ""
        else:
            search_q = route_res.search_query or query
            fused = hybrid_retriever.retrieve(query=search_q, user_role=role, top_k=settings.TOP_K_DENSE * 2)
            reranked = reranker.rerank(query=search_q, candidates=fused, top_n=settings.RERANK_TOP_N)
            gen_resp = gen_service.generate(query=query, candidates=reranked, search_query=search_q, intent=route_res.intent.value)
            answer = gen_resp.answer
            citations_str = "; ".join(
                f"[Source {c.source_index}] {c.document_name} (sec: {c.section}, access: {c.access_level})"
                for c in (gen_resp.citations or [])
            ) or "none"
            evidence_text = "\n---\n".join(c.get("text", "")[:500] for c in reranked[:3])

        faith, rel, err = judge.evaluate(question=query, answer=answer, evidence_text=evidence_text)

        rows.append({
            "question_id": qid,
            "split": case.get("split", split),
            "question": query,
            "answer": answer,
            "retrieved_evidence_citations": citations_str,
            "faithfulness_score": faith if faith is not None else "unavailable",
            "answer_relevancy_score": rel if rel is not None else "unavailable",
            "judge_model": judge.judge_model,
            "judge_provider": judge.judge_provider,
            "error": err
        })

    fieldnames = [
        "question_id",
        "split",
        "question",
        "answer",
        "retrieved_evidence_citations",
        "faithfulness_score",
        "answer_relevancy_score",
        "judge_model",
        "judge_provider",
        "error"
    ]
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    valid_faith = [r["faithfulness_score"] for r in rows if isinstance(r["faithfulness_score"], float)]
    valid_rel = [r["answer_relevancy_score"] for r in rows if isinstance(r["answer_relevancy_score"], float)]

    print(f"Generation Evaluation Complete (split={split}, n={len(rows)})")
    print(f"Generator Model: {settings.LLM_MODEL} | Judge Model: {judge.judge_model} ({judge.judge_provider})")
    if valid_faith:
        print(f"Mean Faithfulness: {sum(valid_faith)/len(valid_faith):.4f} ({len(valid_faith)}/{len(rows)} scored)")
        print(f"Mean Answer Relevancy: {sum(valid_rel)/len(valid_rel):.4f} ({len(valid_rel)}/{len(rows)} scored)")
    else:
        print(f"Judge Scores: unavailable (0/{len(rows)} scored; see 'error' column in CSV)")
    print(f"CSV Saved: {output_csv}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run generation quality evaluation with a separate LLM judge.")
    parser.add_argument("--split", type=str, default="development", choices=["development", "held_out_test", "all"])
    parser.add_argument("--output-csv", type=str, default="evaluation/results/generation_eval_results.csv")
    parser.add_argument("--judge-provider", type=str, default="groq")
    parser.add_argument("--judge-model", type=str, default="qwen/qwen3.8-27b")
    args = parser.parse_args()
    run_generation_eval(
        split=args.split,
        output_csv=args.output_csv,
        judge_provider=args.judge_provider,
        judge_model=args.judge_model
    )
