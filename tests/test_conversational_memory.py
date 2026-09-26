from backend.app.generation.intent_router import get_intent_router, QueryIntent, OUT_OF_SCOPE_RESPONSE
from backend.app.generation.contextualizer import QueryContextualizer

def test_intent_router_conversational_queries():
    router = get_intent_router()
    queries = [
        "who are u",
        "who are you",
        "what do you do",
        "what can you do",
        "what questions can I ask you?",
        "what should I ask you?",
        "hello",
        "thanks"
    ]
    for q in queries:
        res = router.route(q)
        assert res.intent == QueryIntent.CONVERSATIONAL, f"Failed for query: {q}"

def test_intent_router_out_of_scope():
    router = get_intent_router()
    queries = [
        "what is the weather today?",
        "tell me a joke",
        "who won yesterday's match?"
    ]
    for q in queries:
        res = router.route(q)
        assert res.intent == QueryIntent.OUT_OF_SCOPE, f"Failed for query: {q}"

def test_intent_router_knowledge_queries():
    router = get_intent_router()
    queries = [
        "What is NexaCloud's RTO policy?",
        "What is the RPO?",
        "Explain the password policy.",
        "What are the API token refresh requirements?"
    ]
    for q in queries:
        res = router.route(q)
        assert res.intent == QueryIntent.KNOWLEDGE, f"Failed for query: {q}"

def test_intent_router_history_does_not_force_hybrid():
    router = get_intent_router()
    history = [
        {"role": "user", "content": "What is NexaCloud's RPO?"},
        {"role": "assistant", "content": "RPO is 1 hour."}
    ]
    # Standalone knowledge query with history present -> KNOWLEDGE
    res_know = router.route("What is NexaCloud's RTO policy?", history)
    assert res_know.intent == QueryIntent.KNOWLEDGE

    # Conversational query with history present -> CONVERSATIONAL
    res_conv1 = router.route("who are you?", history)
    assert res_conv1.intent == QueryIntent.CONVERSATIONAL

    res_conv2 = router.route("what questions can i ask you", history)
    assert res_conv2.intent == QueryIntent.CONVERSATIONAL

def test_query_contextualizer_follow_up():
    chat_history = [
        {"role": "user", "content": "What is NexaCloud's RPO?"},
        {"role": "assistant", "content": "NexaCloud's RPO is 1 hour."}
    ]
    rewritten = QueryContextualizer.contextualize_query("What about RTO?", chat_history)
    assert "Recovery Time Objective" in rewritten or "RTO" in rewritten

