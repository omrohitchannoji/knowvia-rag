"""
Stage-Level Tracing (Langfuse v5 SDK + Offline Mock Mode) and Explicit Cost Reporting.
Records per-stage latency spans (guardrail, router, dense_retrieval, bm25_retrieval,
fusion, reranking, generation) and computes cost strictly from configured pricing
constants without sending private payloads, prompts, or secrets by default.
"""

import os
import re
import time
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.core.logging import logger


SENSITIVE_TRACE_KEYS = {
    "query", "search_query", "prompt", "text", "answer", "raw_answer",
    "document_text", "context", "chunks", "token", "access_token",
    "secret", "password", "authorization", "api_key", "headers"
}

STAGE_TO_OBSERVATION_TYPE = {
    "guardrail": "guardrail",
    "router": "span",
    "dense_retrieval": "retriever",
    "bm25_retrieval": "retriever",
    "fusion": "span",
    "reranking": "span",
    "generation": "generation",
}

_SECRET_VALUE_PATTERN = re.compile(
    r"(Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*|gsk_[A-Za-z0-9]+|sk-lf-[A-Za-z0-9\-]+|pk-lf-[A-Za-z0-9\-]+|sk-[A-Za-z0-9]{16,})",
    re.IGNORECASE,
)


class TraceSpan(BaseModel):
    stage: str = Field(description="Name of the pipeline stage")
    duration_ms: float = Field(description="Stage execution latency in milliseconds")
    status: str = Field(default="ok", description="ok or error")
    details: Dict[str, Any] = Field(default_factory=dict, description="Redacted operational details")


class TokenUsage(BaseModel):
    usage_available: bool = False
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class PipelineTrace(BaseModel):
    trace_id: str
    langfuse_trace_id: Optional[str] = None
    langfuse_mode: str = "offline_mock"
    total_latency_ms: float = 0.0
    spans: List[TraceSpan] = Field(default_factory=list)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    model_name: Optional[str] = None
    estimated_cost_usd: Optional[float] = None
    cost_calculation_details: Optional[Dict[str, Any]] = Field(default_factory=dict)


def calculate_cost(
    model_name: str,
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
    usage_available: bool = False
) -> Tuple[Optional[float], Dict[str, Any]]:
    """
    Computes dollar cost strictly from settings.MODEL_PRICING dictionary.
    Never estimates or guesses rates. Returns None when usage or pricing is unset.
    """
    if not usage_available or prompt_tokens is None or completion_tokens is None:
        return None, {"cost_available": False, "note": "Token usage unavailable from provider."}

    if not isinstance(model_name, str):
        model_name = str(model_name or "")

    pricing_table = getattr(settings, "MODEL_PRICING", {})
    model_rates = pricing_table.get(model_name)
    if not model_rates:
        model_lower = model_name.lower()
        for key, rates in pricing_table.items():
            key_lower = str(key).lower()
            if key_lower in model_lower or model_lower in key_lower:
                model_rates = rates
                break

    if not model_rates:
        return None, {"cost_available": False, "note": f"Model '{model_name}' not found in MODEL_PRICING."}

    input_rate = model_rates.get("input_per_m")
    output_rate = model_rates.get("output_per_m")

    if input_rate is None or output_rate is None:
        return None, {
            "cost_available": False,
            "model": model_name,
            "note": f"Pricing rates for '{model_name}' are unset (None) in MODEL_PRICING."
        }

    input_cost = (prompt_tokens / 1_000_000.0) * float(input_rate)
    output_cost = (completion_tokens / 1_000_000.0) * float(output_rate)
    total_cost = round(input_cost + output_cost, 6)

    details = {
        "cost_available": True,
        "model": model_name,
        "input_rate_per_m": input_rate,
        "output_rate_per_m": output_rate,
        "input_cost": round(input_cost, 6),
        "output_cost": round(output_cost, 6),
        "total_cost": total_cost
    }
    return total_cost, details


def _redact_string(val: str) -> str:
    return _SECRET_VALUE_PATTERN.sub("[REDACTED]", val)


def _sanitize_detail_value(val: Any) -> Any:
    if isinstance(val, (int, float, bool)) or val is None:
        return val
    if isinstance(val, str):
        return _redact_string(val) if settings.TRACE_REDACT_PAYLOADS else val
    if isinstance(val, (list, tuple)):
        return [_sanitize_detail_value(x) for x in val[:50]]
    if isinstance(val, dict):
        sanitized = {}
        for k, v in val.items():
            if settings.TRACE_REDACT_PAYLOADS and str(k).lower() in SENSITIVE_TRACE_KEYS:
                continue
            sanitized[str(k)] = _sanitize_detail_value(v)
        return sanitized
    s = str(val)
    if "MagicMock" in s or "Mock" in s:
        return "mock"
    return _redact_string(s) if settings.TRACE_REDACT_PAYLOADS else s


_langfuse_client_cache: Optional[Any] = None
_langfuse_client_key: Optional[Tuple[str, str]] = None


def get_langfuse_client() -> Optional[Any]:
    """
    Returns a configured Langfuse v5 client if LANGFUSE_ENABLED=True and credentials are present,
    otherwise returns None so tracing stays in offline_mock mode.
    """
    global _langfuse_client_cache, _langfuse_client_key

    if not getattr(settings, "ENABLE_TRACING", True):
        return None
    if not getattr(settings, "LANGFUSE_ENABLED", False):
        return None

    pub_key = os.getenv("LANGFUSE_PUBLIC_KEY") or getattr(settings, "LANGFUSE_PUBLIC_KEY", None)
    sec_key = os.getenv("LANGFUSE_SECRET_KEY") or getattr(settings, "LANGFUSE_SECRET_KEY", None)
    host = os.getenv("LANGFUSE_HOST") or getattr(settings, "LANGFUSE_HOST", None) or "https://cloud.langfuse.com"

    if not pub_key or not sec_key:
        return None
    if "your-public-key" in pub_key or "your-secret-key" in sec_key:
        return None

    cache_key = (pub_key, host)
    if _langfuse_client_cache is not None and _langfuse_client_key == cache_key:
        return _langfuse_client_cache

    try:
        from langfuse import Langfuse
        client = Langfuse(
            public_key=pub_key,
            secret_key=sec_key,
            base_url=host,
        )
        _langfuse_client_cache = client
        _langfuse_client_key = cache_key
        return client
    except Exception as e:
        logger.warning(f"Langfuse client initialization failed; falling back to offline_mock: {type(e).__name__}")
        return None


class PipelineTracer:
    """Contextual collector for pipeline stage trace spans (Langfuse v5 + Offline Mock)."""

    def __init__(self, trace_id: str, mode: str = "rag_query"):
        self.trace_id = trace_id
        self.mode = mode
        self.start_time = time.perf_counter()
        self.spans: List[TraceSpan] = []
        self.token_usage = TokenUsage()
        self.model_name: Optional[str] = None
        self._lf_client: Optional[Any] = None
        self._lf_root_span: Optional[Any] = None
        self.langfuse_trace_id: Optional[str] = None
        self.langfuse_mode: str = "offline_mock"
        self._usage_by_stage: Dict[str, Dict[str, Any]] = {}
        self._usage_incomplete = False

        self._init_live_trace()

    def _init_live_trace(self):
        client = get_langfuse_client()
        if client is None:
            return
        try:
            lf_trace_id = client.create_trace_id(seed=self.trace_id)
            root_span = client.start_observation(
                trace_context={"trace_id": lf_trace_id},
                name="knowvia_rag_query",
                as_type="chain",
                metadata={
                    "knowvia_trace_id": self.trace_id,
                    "mode": self.mode,
                    "payload_redaction": settings.TRACE_REDACT_PAYLOADS,
                },
            )
            self._lf_client = client
            self._lf_root_span = root_span
            self.langfuse_trace_id = lf_trace_id
            self.langfuse_mode = "live"
        except Exception as e:
            logger.warning(f"Langfuse trace start failed; falling back to offline_mock: {type(e).__name__}")
            self._lf_client = None
            self._lf_root_span = None
            self.langfuse_trace_id = None
            self.langfuse_mode = "offline_mock"

    def record_span(
        self,
        stage: str,
        duration_ms: float,
        status: str = "ok",
        details: Optional[Dict[str, Any]] = None
    ):
        """Records a single stage execution span with redacted details."""
        safe_details: Dict[str, Any] = {}
        for k, v in (details or {}).items():
            key_lower = str(k).lower()
            if settings.TRACE_REDACT_PAYLOADS and key_lower in SENSITIVE_TRACE_KEYS:
                continue
            safe_details[str(k)] = _sanitize_detail_value(v)

        span = TraceSpan(
            stage=stage,
            duration_ms=round(duration_ms, 2),
            status=status,
            details=safe_details
        )
        self.spans.append(span)

        if self._lf_root_span is not None:
            try:
                obs_type = STAGE_TO_OBSERVATION_TYPE.get(stage, "span")
                obs_kwargs: Dict[str, Any] = {
                    "name": stage,
                    "as_type": obs_type,
                    "metadata": {
                        "duration_ms": span.duration_ms,
                        "status": status,
                        **safe_details,
                    },
                    "level": "ERROR" if status == "error" else "DEFAULT",
                }
                stage_usage = self._usage_by_stage.get(stage)
                if stage_usage is not None:
                    obs_kwargs["metadata"]["token_usage_available"] = bool(stage_usage.get("usage_available"))
                    if stage_usage.get("usage_available"):
                        obs_kwargs["metadata"].update({
                            "input_tokens": stage_usage["prompt_tokens"],
                            "output_tokens": stage_usage["completion_tokens"],
                            "total_tokens": stage_usage["total_tokens"],
                        })
                    else:
                        obs_kwargs["metadata"]["token_usage"] = "unavailable"
                if status == "error" and "error_type" in safe_details:
                    obs_kwargs["status_message"] = str(safe_details["error_type"])

                if obs_type == "generation":
                    obs_kwargs["model"] = self.model_name or settings.LLM_MODEL
                    if stage_usage and stage_usage.get("usage_available"):
                        obs_kwargs["usage_details"] = {
                            "input": stage_usage["prompt_tokens"],
                            "output": stage_usage["completion_tokens"],
                            "total": stage_usage["total_tokens"],
                        }
                    else:
                        obs_kwargs["metadata"]["token_usage"] = (
                            "unavailable" if stage_usage is not None else "not_called"
                        )

                obs = self._lf_root_span.start_observation(**obs_kwargs)
                obs.end()
            except Exception as e:
                logger.warning(f"Langfuse span '{stage}' skipped: {type(e).__name__}")

    def record_llm_usage(
        self,
        model_name: str,
        prompt_tokens: Optional[int],
        completion_tokens: Optional[int],
        total_tokens: Optional[int] = None,
        usage_available: bool = False,
        stage: str = "generation",
    ):
        """Records real token usage from the LLM provider, or marks unavailable."""
        self.model_name = model_name
        if not usage_available or prompt_tokens is None or completion_tokens is None:
            self._usage_by_stage[stage] = {"usage_available": False}
            self._usage_incomplete = True
            self.token_usage.usage_available = False
            self.token_usage.prompt_tokens = None
            self.token_usage.completion_tokens = None
            self.token_usage.total_tokens = None
            return

        computed_total = total_tokens if total_tokens is not None else (int(prompt_tokens) + int(completion_tokens))
        call_usage = {
            "usage_available": True,
            "prompt_tokens": int(prompt_tokens),
            "completion_tokens": int(completion_tokens),
            "total_tokens": int(computed_total),
        }
        self._usage_by_stage[stage] = call_usage

        # Aggregate only when every LLM call made for this query reported usage.
        if self._usage_incomplete:
            return
        self.token_usage.usage_available = True
        self.token_usage.prompt_tokens = (self.token_usage.prompt_tokens or 0) + call_usage["prompt_tokens"]
        self.token_usage.completion_tokens = (self.token_usage.completion_tokens or 0) + call_usage["completion_tokens"]
        self.token_usage.total_tokens = (self.token_usage.total_tokens or 0) + call_usage["total_tokens"]

    def finalize(self) -> PipelineTrace:
        """Computes total latency, cost (if rates & usage available), flushes Langfuse, and returns trace."""
        total_latency = round((time.perf_counter() - self.start_time) * 1000, 2)
        total_cost, cost_details = calculate_cost(
            self.model_name or settings.LLM_MODEL,
            self.token_usage.prompt_tokens,
            self.token_usage.completion_tokens,
            usage_available=self.token_usage.usage_available
        )

        if self._lf_root_span is not None:
            try:
                self._lf_root_span.update(
                    metadata={
                        "knowvia_trace_id": self.trace_id,
                        "mode": self.mode,
                        "model": self.model_name or settings.LLM_MODEL,
                        "total_latency_ms": total_latency,
                        "usage_available": self.token_usage.usage_available,
                        "prompt_tokens": self.token_usage.prompt_tokens,
                        "completion_tokens": self.token_usage.completion_tokens,
                        "total_tokens": self.token_usage.total_tokens,
                        "cost_available": bool(cost_details.get("cost_available", False)),
                        "estimated_cost_usd": total_cost if total_cost is not None else "unavailable",
                    }
                )
                self._lf_root_span.end()
                if self._lf_client is not None:
                    self._lf_client.flush()
            except Exception as e:
                logger.warning(f"Langfuse finalize/flush skipped: {type(e).__name__}")

        return PipelineTrace(
            trace_id=self.trace_id,
            langfuse_trace_id=self.langfuse_trace_id,
            langfuse_mode=self.langfuse_mode,
            total_latency_ms=total_latency,
            spans=self.spans,
            token_usage=self.token_usage,
            model_name=self.model_name or settings.LLM_MODEL,
            estimated_cost_usd=total_cost,
            cost_calculation_details=cost_details
        )
