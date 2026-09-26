import re
import json
from typing import Tuple, Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, ValidationError
from backend.app.core.logging import logger
from backend.app.generation.llm import get_llm_client, BaseLLMClient

class QueryIntent(str, Enum):
    CONVERSATIONAL = "conversational"
    KNOWLEDGE = "knowledge"
    HYBRID = "hybrid"
    OUT_OF_SCOPE = "out_of_scope"

class RouterResult(BaseModel):
    intent: QueryIntent = Field(description="Strict intent: conversational, knowledge, hybrid, out_of_scope")
    search_query: Optional[str] = Field(default=None, description="Rewritten standalone search query if knowledge or hybrid")
    reason: Optional[str] = Field(default=None, description="Brief routing rationale")

ROUTER_SYSTEM_PROMPT = """You are the Technical Documentation Intent Classifier & Query Router Engine.
Your job is to classify the user query into EXACTLY ONE of these 4 intents:

1. "conversational": Greetings, assistant identity ("who are you"), capabilities ("what can I ask", "what can you do"), how to interact, thanks, or basic conversation.
2. "knowledge": Standalone technical documentation, architecture, or container/cloud questions (e.g., "What is a Kubernetes Job?", "What is HPA?", "How do CronJobs work?", "How are Databricks jobs managed?", "What is the purpose of parallelism?").
3. "hybrid": A follow-up question that DEPENDS on previous conversation history (e.g., Turn 1: "What is a Kubernetes Job?", Turn 2: "What about parallelism?"). NOTE: The existence of conversation history alone does NOT make a standalone question hybrid.
4. "out_of_scope": Questions outside technical documentation domain (weather, stock market, sports, jokes, general world trivia).

STRICT OUTPUT FORMAT:
You MUST respond with a valid JSON object matching this schema ONLY:
{
    "intent": "conversational" | "knowledge" | "hybrid" | "out_of_scope",
    "search_query": "standalone search query if knowledge or hybrid, else null",
    "reason": "brief classification rationale"
}
"""

OUT_OF_SCOPE_RESPONSE = (
    "I am specialized strictly in Technical Documentation and Cloud Infrastructure intelligence. "
    "I am unable to answer general world knowledge, weather, stock market, or sports questions. "
    "Please ask a technical question related to Kubernetes Jobs, CronJobs, Pod Autoscaling (HPA), Databricks job management, or container infrastructure."
)

# Tier 1 Deterministic Patterns
GREETING_PATTERNS = [
    r"^\s*(hi|hello|hey|greetings|good\s+(morning|afternoon|evening))\b",
    r"\bwho\s+(are|r)\s+(you|u)\b",
    r"\bwho\s+r\s+u\b",
    r"\bwhat\s+is\s+your\s+name\b",
    r"\bwhat\s+(can|do|r|should|could)\s+(you|u|i)\s+(do|help|here|ask)\b",
    r"\bwhat\s+questions?\s+(can|should|could)?\s*(i|you)?\s*(ask|do)\b",
    r"\bwhat\s+(should|can)\s+i\s+ask\b",
    r"\bwhat\s+(is|are)\s+this\s+(app|application|bot|system)\s*(for|doing)?\b",
    r"\bwhat\s+are\s+(you|u)\s+doing\s+here\b",
    r"\bare\s+(you|u)\s+a\s+(rag|ai)\s+(assistant|bot)\b",
    r"\bhelp\b",
    r"\bthanks\b",
    r"\bthank\s+(you|u)\b"
]

OUT_OF_SCOPE_PATTERNS = [
    r"\b(weather|weather\s+today)\b",
    r"\bstock\s+market\b",
    r"\btell\s+me\s+a\s+joke\b",
    r"\bsing\s+a\s+song\b",
    r"\b(cricket|football)\s+match\b",
    r"\bwho\s+won\s+yesterday\b"
]

class IntentRouter:
    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self.llm_client = llm_client or get_llm_client()

    def route(
        self,
        query: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> RouterResult:
        """
        Two-Tier Query Router:
        Tier 1: Fast deterministic pattern check for obvious greetings, identity, thanks, out-of-scope.
        Tier 2: LLM Semantic Classification returning strict JSON (conversational, knowledge, hybrid, out_of_scope).
        """
        if not query or not query.strip():
            return RouterResult(intent=QueryIntent.CONVERSATIONAL, reason="Empty query")

        clean_q = query.strip()
        normalized_q = re.sub(r"[^\w\s]", "", clean_q.lower()).strip()

        # Check for technical terms that indicate Knowledge RAG evaluation
        tech_pattern = r"\b(kubernetes|job|jobs|cronjob|cronjobs|hpa|vpa|autoscale|autoscaling|databricks|parallelism|pod|pods|queue|workload|container|docker|api|apis|token|auth|security|replication|cluster)\b"
        has_tech_keyword = bool(re.search(tech_pattern, normalized_q))

        if not has_tech_keyword:
            # Tier 1: Check Conversational Patterns
            for pattern in GREETING_PATTERNS:
                if re.search(pattern, normalized_q):
                    logger.info(f"Query='{clean_q}' | Intent=conversational | Retrieval=False (Tier 1 Pattern Match)")
                    return RouterResult(intent=QueryIntent.CONVERSATIONAL, reason="Tier 1 Conversational Pattern Match")

            # Tier 1: Check Out of Scope Patterns
            for pattern in OUT_OF_SCOPE_PATTERNS:
                if re.search(pattern, normalized_q):
                    logger.info(f"Query='{clean_q}' | Intent=out_of_scope | Retrieval=False (Tier 1 Pattern Match)")
                    return RouterResult(intent=QueryIntent.OUT_OF_SCOPE, reason="Tier 1 Out Of Scope Pattern Match")

        # Tier 2: LLM Semantic Router for queries requiring contextual or deep classification
        history_str = ""
        if chat_history and len(chat_history) > 0:
            formatted_turns = [f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in chat_history[-3:]]
            history_str = "\n".join(formatted_turns)

        user_prompt = f"USER QUERY: {clean_q}"
        if history_str:
            user_prompt = f"RECENT CHAT HISTORY:\n{history_str}\n\n{user_prompt}"

        try:
            raw_response = self.llm_client.generate(
                system_prompt=ROUTER_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.0
            )

            # Parse JSON from LLM response
            json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if json_match:
                json_data = json.loads(json_match.group(0))
                result = RouterResult(**json_data)
                retrieval_flag = result.intent in [QueryIntent.KNOWLEDGE, QueryIntent.HYBRID]
                logger.info(f"Query='{clean_q}' | Intent={result.intent.value} | Retrieval={retrieval_flag} (Tier 2 LLM Router)")
                return result

        except (json.JSONDecodeError, ValidationError, Exception) as e:
            logger.warning(f"Tier 2 LLM Router parsing error ({e}). Falling back to default routing logic.")

        # Fallback Logic if LLM router response parsing or API fails
        if has_tech_keyword:
            return RouterResult(intent=QueryIntent.KNOWLEDGE, search_query=clean_q, reason="Fallback Technical Keyword Match")

        if chat_history and len(chat_history) > 0:
            follow_up_triggers = ["what about", "how about", "what of", "and for", "can you explain", "tell me more", "that", "this", "it"]
            if any(t in normalized_q for t in follow_up_triggers) or len(clean_q.split()) <= 4:
                return RouterResult(intent=QueryIntent.HYBRID, search_query=clean_q, reason="Fallback Follow-up Hybrid Match")

        return RouterResult(intent=QueryIntent.CONVERSATIONAL, reason="Fallback Conversational Default")

# Singleton helper
_intent_router_instance = None

def get_intent_router() -> IntentRouter:
    global _intent_router_instance
    if _intent_router_instance is None:
        _intent_router_instance = IntentRouter()
    return _intent_router_instance
