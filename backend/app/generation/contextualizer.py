import re
from typing import List, Dict, Any, Optional
from backend.app.core.logging import logger

class QueryContextualizer:
    """
    Disambiguates short follow-up questions using conversation chat history.
    Example:
      History: User: "What is NexaCloud's RPO?" Assistant: "1 hour."
      Query: "What about RTO?"
      Rewritten: "What is NexaCloud's Recovery Time Objective (RTO)?"
    """
    
    @staticmethod
    def contextualize_query(query: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        if not chat_history or len(chat_history) == 0:
            return query

        clean_q = query.strip()
        lower_q = clean_q.lower()

        # Check for coreferential / follow-up keywords
        follow_up_triggers = ["rto", "rpo", "that", "it", "this", "the first one", "the second one", "what about", "how about", "tell me more"]
        is_follow_up = any(trigger in lower_q for trigger in follow_up_triggers) or len(clean_q.split()) <= 4

        if not is_follow_up:
            return query

        # Extract last user topic from chat history
        last_user_msg = ""
        for msg in reversed(chat_history):
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user" and content:
                last_user_msg = content
                break

        if not last_user_msg:
            return query

        # Apply deterministic rule-based rewriting for common patterns
        if "what about rto" in lower_q or lower_q == "rto" or lower_q == "rto?":
            rewritten = "What is NexaCloud's Recovery Time Objective (RTO) downtime target?"
            logger.info(f"Query Contextualizer: Rewrote '{query}' -> '{rewritten}'")
            return rewritten

        if "what about rpo" in lower_q or lower_q == "rpo" or lower_q == "rpo?":
            rewritten = "What is NexaCloud's Recovery Point Objective (RPO) data loss target?"
            logger.info(f"Query Contextualizer: Rewrote '{query}' -> '{rewritten}'")
            return rewritten

        # Combine last question context with current follow-up
        rewritten = f"{last_user_msg} - {query}"
        logger.info(f"Query Contextualizer: Combined query context '{query}' -> '{rewritten}'")
        return rewritten
