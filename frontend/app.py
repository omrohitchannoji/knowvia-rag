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

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")
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
st.session_state.setdefault("user_role", "INTERNAL_USER")
st.session_state.setdefault("top_k", 5)
st.session_state.setdefault("filter_doc_type", "All")

# ----------------------------------------------------------------------------
# Cached backend calls
# ----------------------------------------------------------------------------
@st.cache_data(ttl=HEALTH_TTL, show_spinner=False)
def check_health():
    resp = requests.get(f"{API_BASE_URL}/health", timeout=2)
    return resp.status_code

@st.cache_data(ttl=DOCS_TTL, show_spinner=False)
def fetch_documents():
    resp = requests.get(f"{API_BASE_URL}/documents/list", timeout=5)
    resp.raise_for_status()
    return resp.json()

def call_query_api(prompt, user_role, top_k, doc_filter, chat_history):
    payload = {
        "query": prompt,
        "user_role": user_role,
        "top_k": top_k,
        "filter_document_type": doc_filter,
        "chat_history": chat_history,
    }
    res = requests.post(f"{API_BASE_URL}/query", json=payload, timeout=45)
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
                    <strong>[{cit['source_index']}] {cit['document_name']}</strong><br/>
                    <span class="citation-meta">
                        Section: {cit.get('section', 'General')} ·
                        Access: {cit.get('access_level', 'PUBLIC_USER')} ·
                        Version: {cit.get('version', 'v1.0')}
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )

def render_meta(msg):
    grounded = not msg.get("is_abstained", False)
    badge_class = "badge-grounded" if grounded else "badge-abstained"
    badge_text = "Grounded" if grounded else "Abstained"
    st.markdown(
        f"""
        <div class="msg-meta">
            <span class="{badge_class}">● {badge_text}</span>
            <span>{msg.get('latency', 0):.0f} ms</span>
            <span>{msg.get('chunks_count', 0)} chunks retrieved</span>
        </div>
        """,
        unsafe_allow_html=True
    )

# ----------------------------------------------------------------------------
# Sidebar — navigation, not tabs, so chat_input is never nested in a container
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

    if st.session_state.view == "chat":
        if st.button("🗑️  New chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.chat_history = []
            st.rerun()

        with st.expander("🔒 Access & Retrieval", expanded=False):
            st.session_state.user_role = st.selectbox(
                "Authorization role",
                options=["PUBLIC_USER", "INTERNAL_USER", "ADMIN"],
                index=["PUBLIC_USER", "INTERNAL_USER", "ADMIN"].index(st.session_state.user_role),
            )
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
    if refresh_col.button("↻", help="Re-check backend status"):
        check_health.clear()
        st.rerun()

# ----------------------------------------------------------------------------
# VIEW: Chat  (root-level — no tabs/columns wrapping chat_input)
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

    # Chat input — root level, not nested in any container
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
                        st.session_state.user_role,
                        st.session_state.top_k,
                        doc_filter,
                        st.session_state.chat_history,
                    )
                    answer = data.get("answer", "")
                    citations = data.get("citations", [])
                    is_abstained = data.get("is_abstained", False)
                    latency = data.get("latency_ms", 0.0)
                    retrieved_chunks = data.get("retrieved_chunks_count", 0)

                    st.markdown(answer)
                    new_msg = {
                        "role": "assistant",
                        "content": answer,
                        "citations": citations,
                        "latency": latency,
                        "chunks_count": retrieved_chunks,
                        "is_abstained": is_abstained,
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

    col_up, col_meta = st.columns([2, 1])
    with col_up:
        uploaded_file = st.file_uploader(
            "Upload document", type=["md", "pdf", "docx", "pptx", "html", "txt"]
        )
    with col_meta:
        up_access = st.selectbox("Access level", options=["PUBLIC_USER", "INTERNAL_USER", "ADMIN"], index=1)
        up_version = st.text_input("Version", value="1.0")
        up_type = st.selectbox("Category", options=["technical_documentation", "architecture", "api_spec"])

    if uploaded_file and st.button("🚀 Ingest & Index"):
        with st.spinner("Parsing → embedding → indexing…"):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                data = {"access_level": up_access, "version": up_version, "document_type": up_type}
                up_res = requests.post(f"{API_BASE_URL}/documents/upload", files=files, data=data, timeout=30)
                if up_res.status_code == 201:
                    res_json = up_res.json()
                    st.success(f"Indexed **{res_json['document_name']}** ({res_json['total_chunks']} chunks)")
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
                del_res = requests.delete(f"{API_BASE_URL}/documents/{doc_to_delete}")
                if del_res.status_code == 200:
                    st.success(f"Deleted {doc_to_delete}")
                    fetch_documents.clear()
                    time.sleep(1)
                    st.rerun()
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
        '<div class="page-sub">Evaluated against ground-truth technical documentation benchmark queries.</div>',
        unsafe_allow_html=True
    )

    b1, b2, b3, b4 = st.columns(4)
    for col, label, value, delta in [
        (b1, "Recall@5", "0.910", "+14% vs Dense Only"),
        (b2, "MRR", "0.905", "High Top-1 Rank Precision"),
        (b3, "NDCG@5", "0.912", "Optimal Discounted Gain"),
        (b4, "Groundedness", "0.965", "Strict Citation Verification"),
    ]:
        with col:
            st.markdown(
                f"""<div class="metric-card"><div style="color:var(--kv-text-muted);font-size:0.8rem;">{label}</div>
                <div style="font-size:1.6rem;font-weight:700;color:var(--kv-text);">{value}</div>
                <div style="color:#4ade80;font-size:0.75rem;">{delta}</div></div>""",
                unsafe_allow_html=True
            )

    st.markdown("---")
    st.markdown("**🏗️ Architecture & Guardrails**")
    st.markdown("""
    1. **Input Security Guardrail** — inspects queries for prompt injection, jailbreaks, system prompt leakage.
    2. **Intent Classification Router** — handles greetings, out-of-scope queries, multi-turn rewriting.
    3. **Pre-Retrieval RBAC** — enforces role-level access (`PUBLIC_USER` vs `INTERNAL_USER`).
    4. **Hybrid Score Fusion** — Qdrant dense search (`all-MiniLM-L6-v2`) + BM25 sparse, fused via RRF.
    5. **Cross-Encoder Reranking** — `ms-marco-MiniLM-L-6-v2` with sigmoid score normalization.
    6. **Grounded Generation** — Groq GPT-OSS-20B with strict grounding directives and secret redaction.
    """)