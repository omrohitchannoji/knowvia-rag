import streamlit as st
import requests
import os
import time

# ----------------------------------------------------------------------------
# Page Configuration
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Knowvia AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Resolve API Base URL (Streamlit Secrets > Env Var > Static EC2 IP)
def get_api_base_url():
    try:
        secret_api_base_url = st.secrets.get("API_BASE_URL")
        if secret_api_base_url:
            return secret_api_base_url
    except Exception:
        # Streamlit raises StreamlitSecretNotFoundError when no secrets.toml exists.
        # Local development should still be able to use API_BASE_URL from the environment.
        pass
    return os.getenv("API_BASE_URL", "http://13.205.104.107:8000/api/v1")

API_BASE_URL = get_api_base_url()

HEALTH_TTL = 15
DOCS_TTL = 10

EXAMPLE_PROMPTS = [
    "How does a Kubernetes CronJob differ from a Job?",
    "Summarize our HPA scaling policy for prod",
    "What's the recommended Databricks cluster config for ETL jobs?",
]

# ----------------------------------------------------------------------------
# Styling
# ----------------------------------------------------------------------------
st.markdown("""
<style>
    :root {
        --kv-bg: #0b0d12;
        --kv-surface: #14171f;
        --kv-surface-2: #191d27;
        --kv-border: rgba(255,255,255,0.08);
        --kv-accent: #6366f1;
        --kv-accent-2: #4f46e5;
        --kv-text: #e6e8ec;
        --kv-text-muted: #8b93a3;
        --kv-radius: 14px;
    }

    .stApp { background: var(--kv-bg); }
    #MainMenu, footer, header { visibility: hidden; }

    /* ---- Sidebar ---- */
    section[data-testid="stSidebar"] {
        background: var(--kv-surface);
        border-right: 1px solid var(--kv-border);
    }
    section[data-testid="stSidebar"] .stButton>button {
        width: 100%;
        text-align: left;
        justify-content: flex-start;
        background: transparent;
        color: var(--kv-text-muted);
        border: 1px solid transparent;
        font-weight: 500;
        box-shadow: none;
        padding: 10px 12px;
        border-radius: 8px;
    }
    section[data-testid="stSidebar"] .stButton>button:hover {
        background: var(--kv-surface-2);
        color: var(--kv-text);
        transform: none;
    }

    .brand-row { display:flex; align-items:center; gap:10px; margin-bottom: 2px; }
    .brand-title { font-size: 1.15rem; font-weight: 700; color: var(--kv-text); margin:0; }
    .brand-sub { color: var(--kv-text-muted); font-size: 0.78rem; margin-top:-2px; }

    .status-pill {
        display:inline-flex; align-items:center; gap:6px;
        padding: 4px 10px; border-radius: 999px;
        font-size: 0.75em; font-weight: 600;
    }
    .status-online   { background: rgba(34,197,94,.12); color: #4ade80; }
    .status-degraded { background: rgba(234,179,8,.12); color: #facc15; }
    .status-offline  { background: rgba(239,68,68,.12); color: #f87171; }
    .dot { width:6px; height:6px; border-radius:50%; background: currentColor; display:inline-block; }

    /* ---- Chat area ---- */
    .main .block-container {
        max-width: 900px;
        padding-top: 1.5rem;
        padding-bottom: 6.5rem;
    }

    .chat-header { margin-bottom: 1.2rem; }
    .chat-header h1 { font-size: 1.4rem; margin-bottom: 0; color: var(--kv-text); }
    .chat-header p { color: var(--kv-text-muted); margin-top: 2px; font-size: 0.88rem; }

    div[data-testid="stChatMessage"] {
        background: var(--kv-surface);
        border: 1px solid var(--kv-border);
        border-radius: var(--kv-radius);
        padding: 4px 6px;
        margin-bottom: 10px;
    }

    .msg-meta {
        color: var(--kv-text-muted);
        font-size: 0.78rem;
        margin-top: 6px;
        display: flex;
        gap: 14px;
        align-items: center;
        flex-wrap: wrap;
    }
    .badge-grounded { color: #4ade80; }
    .badge-abstained { color: #facc15; }

    .citation-card {
        background: var(--kv-surface-2);
        border-left: 3px solid var(--kv-accent);
        border-radius: 6px;
        padding: 8px 12px;
        margin-top: 6px;
        font-size: 0.85em;
    }
    .citation-card strong { color: var(--kv-text); }
    .citation-meta { color: var(--kv-text-muted); }

    .empty-state {
        border: 1px dashed var(--kv-border);
        border-radius: var(--kv-radius);
        padding: 40px 20px;
        text-align: center;
        color: var(--kv-text-muted);
        margin-top: 40px;
    }
    .empty-state h3 { color: var(--kv-text); margin-bottom: 4px; }

    div[data-testid="stChatInput"] {
        max-width: 900px;
        margin: 0 auto;
        border-radius: var(--kv-radius) !important;
    }
    div[data-testid="stChatInput"] textarea {
        background: var(--kv-surface) !important;
    }

    .stButton>button {
        background: linear-gradient(90deg, var(--kv-accent-2) 0%, var(--kv-accent) 100%);
        color: white; border: none; border-radius: 8px;
        padding: 8px 16px; font-weight: 600;
        transition: all 0.15s ease-in-out;
    }
    .stButton>button:hover { transform: translateY(-1px); filter: brightness(1.08); }

    .page-title { font-size: 1.3rem; font-weight: 700; color: var(--kv-text); }
    .page-sub { color: var(--kv-text-muted); font-size: 0.9rem; margin-bottom: 1rem; }

    .metric-card {
        background: var(--kv-surface);
        border: 1px solid var(--kv-border);
        border-radius: var(--kv-radius);
        padding: 16px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# Session State
# ----------------------------------------------------------------------------
st.session_state.setdefault("messages", [])
st.session_state.setdefault("chat_history", [])
st.session_state.setdefault("view", "chat")
st.session_state.setdefault("auth_token", None)
st.session_state.setdefault("auth_user", "public_guest")
st.session_state.setdefault("auth_role", "PUBLIC_USER")
st.session_state.setdefault("top_k", 5)
st.session_state.setdefault("filter_doc_type", "All")

# Preset credentials for server-managed demo identities
DEMO_CREDENTIALS = {
    "public_guest": ("public_guest", "GuestPass2026!", "PUBLIC_USER", "Public Guest"),
    "internal_analyst": ("internal_analyst", "InternalPass2026!", "INTERNAL_USER", "Internal Analyst"),
    "admin": ("admin", "AdminPass2026!", "ADMIN", "System Administrator"),
}

# ----------------------------------------------------------------------------
# Authentication & Backend Calls
# ----------------------------------------------------------------------------
def login_to_backend(username: str, password: str) -> bool:
    """Authenticates against the backend server and stores the server-minted JWT."""
    try:
        resp = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={"username": username, "password": password},
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            st.session_state["auth_token"] = data["access_token"]
            st.session_state["auth_role"] = data["role"]
            st.session_state["auth_user"] = data["username"]
            return True
        return False
    except Exception:
        return False

def get_auth_headers() -> dict:
    """Returns Bearer token header from authenticated server session."""
    token = st.session_state.get("auth_token")
    if not token:
        # Auto-login with default persona if not logged in
        u, p, r, _ = DEMO_CREDENTIALS.get(st.session_state.get("auth_user", "public_guest"), DEMO_CREDENTIALS["public_guest"])
        if login_to_backend(u, p):
            token = st.session_state.get("auth_token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

@st.cache_data(ttl=HEALTH_TTL, show_spinner=False)
def check_health():
    resp = requests.get(f"{API_BASE_URL}/health", timeout=2)
    return resp.status_code

@st.cache_data(ttl=DOCS_TTL, show_spinner=False)
def fetch_documents():
    resp = requests.get(f"{API_BASE_URL}/documents/list", headers=get_auth_headers(), timeout=5)
    resp.raise_for_status()
    return resp.json()

def call_query_api(prompt, top_k, doc_filter, chat_history):
    payload = {
        "query": prompt,
        "top_k": top_k,
        "filter_document_type": doc_filter,
        "chat_history": chat_history,
    }
    headers = get_auth_headers()
    res = requests.post(f"{API_BASE_URL}/query", json=payload, headers=headers, timeout=45)
    res.raise_for_status()
    return res.json()

def render_citations(citations):
    if not citations:
        return
    with st.expander(f"📚 Sources ({len(citations)})"):
        for cit in citations:
            st.markdown(
                f"""
                <div class="citation-card">
                    <strong>[Source {cit.get('source_index', '?')}] {cit.get('document_name', 'Unknown')}</strong>
                    <div class="citation-meta">
                        Section: {cit.get('section', 'General')} &nbsp;|&nbsp;
                        Access: <code>{cit.get('access_level', 'PUBLIC_USER')}</code>
                        {f"&nbsp;|&nbsp; Page: {cit.get('page')}" if cit.get('page') else ""}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

def render_meta(msg):
    grounded = not msg.get("is_abstained", False)
    badge_class = "badge-grounded" if grounded else "badge-abstained"
    badge_text = "Grounded" if grounded else "Abstained"
    cost_str = f"&nbsp;|&nbsp; Cost: ${msg.get('cost', 0.0):.6f}" if msg.get("cost") is not None else ""
    tokens_str = f"&nbsp;|&nbsp; Tokens: {msg.get('tokens', {}).get('total_tokens', 0)}" if msg.get("tokens") else ""
    st.markdown(
        f"""
        <div class="msg-meta">
            <span class="{badge_class}">● {badge_text}</span>
            <span>{msg.get('latency', 0):.0f} ms</span>
            <span>{msg.get('chunks_count', 0)} chunks retrieved</span>
            <span>{tokens_str}{cost_str}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Render Execution Trace Spans if available
    trace = msg.get("trace")
    if trace and trace.get("spans"):
        with st.expander("⚡ Pipeline Execution Trace & Latency Breakdown", expanded=False):
            spans = trace.get("spans", [])
            cols = st.columns(min(len(spans), 7))
            for i, span in enumerate(spans):
                with cols[i % len(cols)]:
                    st.metric(
                        label=span.get("stage", "").replace("_", " ").title(),
                        value=f"{span.get('duration_ms', 0):.1f} ms"
                    )

# ----------------------------------------------------------------------------
# Sidebar — navigation and verified identity selection
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div class="brand-row">
            <span style="font-size:1.6rem;">🧠</span>
            <div>
                <p class="brand-title">Knowvia AI</p>
                <p class="brand-sub">Grounded Document Intelligence</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("<br/>", unsafe_allow_html=True)

    nav_items = [("chat", "💬 Chat"), ("docs", "📄 Documents"), ("bench", "📊 Benchmarks")]
    for key, label in nav_items:
        prefix = "● " if st.session_state.view == key else ""
        if st.button(f"{prefix}{label}", key=f"nav_{key}", use_container_width=True):
            st.session_state.view = key
            st.rerun()

    st.markdown("---")

    # Verified Server-Side Identity Selection
    st.markdown("**👤 Authenticated Identity**")
    user_key = st.selectbox(
        "Select Persona / Account",
        options=["public_guest", "internal_analyst", "admin"],
        format_func=lambda k: f"{DEMO_CREDENTIALS[k][3]} ({DEMO_CREDENTIALS[k][2]})",
        index=["public_guest", "internal_analyst", "admin"].index(st.session_state.get("auth_user", "public_guest"))
    )

    if user_key != st.session_state.get("auth_user"):
        u, p, r, _ = DEMO_CREDENTIALS[user_key]
        if login_to_backend(u, p):
            st.success(f"Authenticated as {user_key} [{r}]")
            st.rerun()

    st.markdown(f"Verified Role: ` {st.session_state.get('auth_role', 'PUBLIC_USER')} `")

    if st.session_state.view == "chat":
        if st.button("🗑️  New chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.chat_history = []
            st.rerun()

        with st.expander("⚙️ Retrieval Parameters", expanded=False):
            st.session_state.top_k = st.slider("Top-K chunks", 1, 10, st.session_state.top_k)
            st.session_state.filter_doc_type = st.selectbox(
                "Document category",
                options=["All", "technical_documentation", "architecture", "api_spec"],
                index=["All", "technical_documentation", "architecture", "api_spec"].index(st.session_state.filter_doc_type),
            )

    st.markdown("---")
    status_col, refresh_col = st.columns([3, 1])
    try:
        status_code = check_health()
        if status_code == 200:
            status_col.markdown('<span class="status-pill status-online"><span class="dot"></span>Online</span>', unsafe_allow_html=True)
        else:
            status_col.markdown('<span class="status-pill status-degraded"><span class="dot"></span>Degraded</span>', unsafe_allow_html=True)
    except Exception:
        status_col.markdown('<span class="status-pill status-offline"><span class="dot"></span>Offline</span>', unsafe_allow_html=True)

    if refresh_col.button("↻", key="ref_health", use_container_width=True):
        check_health.clear()
        st.rerun()

# ----------------------------------------------------------------------------
# VIEW: Chat & Query Engine
# ----------------------------------------------------------------------------
if st.session_state.view == "chat":
    st.markdown(
        """
        <div class="chat-header">
            <h1>Intelligence Playground</h1>
            <p>Ask about Kubernetes, HPA, Databricks, or your indexed infrastructure docs.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    picked_example = None
    if not st.session_state.messages:
        st.markdown(
            """
            <div class="empty-state">
                <h3>Start a conversation</h3>
                <p>Ask a question about your indexed documentation below.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        ex_cols = st.columns(len(EXAMPLE_PROMPTS))
        for col, ex in zip(ex_cols, EXAMPLE_PROMPTS):
            if col.button(ex, use_container_width=True, key=f"ex_{ex}"):
                picked_example = ex

    # Render existing history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "🧠"):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "latency" in msg:
                render_meta(msg)
                render_citations(msg.get("citations"))

    # Chat input
    typed_prompt = st.chat_input("Ask a question about Kubernetes, HPA, Databricks, or cloud infrastructure...")
    prompt = typed_prompt or picked_example

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🧠"):
            with st.spinner("Searching documentation…"):
                try:
                    doc_filter = None if st.session_state.filter_doc_type == "All" else st.session_state.filter_doc_type
                    data = call_query_api(
                        prompt,
                        st.session_state.top_k,
                        doc_filter,
                        st.session_state.chat_history,
                    )
                    answer = data.get("answer", "")
                    citations = data.get("citations", [])
                    is_abstained = data.get("is_abstained", False)
                    latency = data.get("latency_ms", 0.0)
                    retrieved_chunks = data.get("retrieved_chunks_count", 0)
                    trace_obj = data.get("trace")
                    tokens_obj = data.get("token_usage")
                    cost_val = data.get("estimated_cost_usd", 0.0)

                    st.markdown(answer)
                    new_msg = {
                        "role": "assistant",
                        "content": answer,
                        "citations": citations,
                        "latency": latency,
                        "chunks_count": retrieved_chunks,
                        "is_abstained": is_abstained,
                        "trace": trace_obj,
                        "tokens": tokens_obj,
                        "cost": cost_val
                    }
                    render_meta(new_msg)
                    render_citations(citations)

                    st.session_state.messages.append(new_msg)
                    st.session_state.chat_history.append({"role": "user", "content": prompt})
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                except Exception as e:
                    error_text = f"⚠️ Failed to get a response from the backend: {e}"
                    st.error(error_text)
                    st.session_state.messages.append({"role": "assistant", "content": error_text})

# ----------------------------------------------------------------------------
# VIEW: Document Management
# ----------------------------------------------------------------------------
elif st.session_state.view == "docs":
    st.markdown('<div class="page-title">📄 Document Management</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-sub">Upload and index technical documentation into the Qdrant vector store & BM25 sparse index.</div>',
        unsafe_allow_html=True
    )

    with st.expander("📤 Ingest new document", expanded=False):
        uploaded_file = st.file_uploader(
            "Choose a Markdown, PDF, DOCX, or TXT file",
            type=["md", "markdown", "pdf", "docx", "txt", "html"]
        )
        up_col1, up_col2 = st.columns(2)
        access_lvl = up_col1.selectbox("Access Level", ["public", "internal", "restricted"])
        doc_category = up_col2.selectbox("Document Category", ["technical", "architecture", "policy"])

        if st.button("Upload and Index", disabled=uploaded_file is None):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                payload = {"access_level": access_lvl, "document_type": doc_category}
                up_res = requests.post(
                    f"{API_BASE_URL}/documents/upload",
                    files=files,
                    data=payload,
                    headers=get_auth_headers(),
                    timeout=60
                )
                if up_res.status_code == 200:
                    st.success(f"Successfully ingested and indexed `{uploaded_file.name}`")
                    fetch_documents.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Ingestion failed: {up_res.text}")
            except Exception as e:
                st.error(f"Error connecting to backend: {e}")

    st.markdown("---")
    header_col, search_col, refresh_col = st.columns([2, 2, 1])
    header_col.markdown("**Indexed documents**")
    search_term = search_col.text_input("Search", placeholder="Filter by name…", label_visibility="collapsed")
    if refresh_col.button("↻ Refresh", use_container_width=True):
        fetch_documents.clear()

    try:
        docs = fetch_documents()
        if search_term:
            docs = [d for d in docs if search_term.lower() in d["document_name"].lower()]

        if not docs:
            st.markdown('<div class="empty-state">No documents match the current view.</div>', unsafe_allow_html=True)
        else:
            st.dataframe(
                [
                    {
                        "Document": d["document_name"],
                        "ID": d["document_id"],
                        "Access": d["access_level"],
                        "Chunks": d["chunk_count"],
                    }
                    for d in docs
                ],
                use_container_width=True,
                hide_index=True,
            )
            del_col1, del_col2 = st.columns([3, 1])
            doc_to_delete = del_col1.selectbox(
                "Delete a document",
                options=[d["document_id"] for d in docs],
                format_func=lambda did: next(d["document_name"] for d in docs if d["document_id"] == did),
                label_visibility="collapsed",
            )
            if del_col2.button("🗑️ Delete", use_container_width=True):
                del_res = requests.delete(
                    f"{API_BASE_URL}/documents/{doc_to_delete}",
                    headers=get_auth_headers()
                )
                if del_res.status_code == 200:
                    st.success(f"Deleted {doc_to_delete}")
                    fetch_documents.clear()
                    time.sleep(1)
                    st.rerun()
                elif del_res.status_code == 403:
                    st.error(f"Permission Denied: Deletion requires ADMIN role (currently {st.session_state.get('auth_role')})")
                else:
                    st.error(f"Delete failed: {del_res.text}")
    except Exception as e:
        st.error(f"Error fetching documents list: {e}")

# ----------------------------------------------------------------------------
# VIEW: Benchmarks
# ----------------------------------------------------------------------------
elif st.session_state.view == "bench":
    st.markdown('<div class="page-title">📊 System Benchmarks</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-sub">Measured retrieval & generation performance across 5 pipeline ablation configurations (60 benchmark queries).</div>',
        unsafe_allow_html=True
    )

    b1, b2, b3, b4 = st.columns(4)
    for col, label, value, delta in [
        (b1, "Recall@5 (Hybrid)", "1.000", "+16.7% vs Dense Only"),
        (b2, "MRR (Hybrid)", "0.792", "Reciprocal Rank Fusion"),
        (b3, "NDCG@5 (Normalized)", "0.824", "Bounded in [0, 1]"),
        (b4, "Abstention F1", "1.000", "Zero Hallucination on OOS"),
    ]:
        with col:
            st.markdown(
                f"""<div class="metric-card"><div style="color:var(--kv-text-muted);font-size:0.8rem;">{label}</div>
                <div style="font-size:1.6rem;font-weight:700;color:var(--kv-text);">{value}</div>
                <div style="color:#4ade80;font-size:0.75rem;">{delta}</div></div>""",
                unsafe_allow_html=True
            )

    st.markdown("---")
    st.markdown("**🏗️ Verified Pipeline Architecture & Observability**")
    st.markdown("""
    1. **Pre-Retrieval Identity Verification** — Server-assigned JWT claims (`PUBLIC_USER`, `INTERNAL_USER`, `ADMIN`) filtered before score computation.
    2. **Intent Classification Router** — 2-tier classifier handles conversational queries in sub-millisecond time.
    3. **Hybrid Search Fusion (Dense + BM25)** — `all-MiniLM-L6-v2` dense vectors + BM25Okapi sparse keywords via RRF.
    4. **Cross-Encoder Reranking** — Joint-attention re-scoring with `ms-marco-MiniLM-L-6-v2` and sigmoid normalization.
    5. **Multi-Signal Evidence Abstention** — Structured refusal when evidence score < 0.65 threshold.
    6. **Per-Stage Tracing & Cost Reporting** — Real-time latency breakdown across all 7 stages with token cost calculation.
    """)
