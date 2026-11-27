import os
import time
import requests
import streamlit as st

# ----------------------------------------------------------------------------
# Page Configuration
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Knowvia AI — Grounded Document Intelligence",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Resolve API Base URL (Streamlit Secrets > Env Var > Static EC2 IP)
def get_api_base_url():
    try:
        secret_api_base_url = st.secrets.get("API_BASE_URL")
        if secret_api_base_url:
            return secret_api_base_url
    except Exception:
        pass
    return os.getenv("API_BASE_URL", "http://13.205.104.107:8000/api/v1")


API_BASE_URL = get_api_base_url()
HEALTH_TTL = 15
DOCS_TTL = 10

EXAMPLE_PROMPTS = [
    {
        "tag": "Kubernetes",
        "title": "CronJob vs. Job",
        "query": "How does a Kubernetes CronJob differ from a Job?",
    },
    {
        "tag": "Autoscaling",
        "title": "Production HPA Policy",
        "query": "Summarize our HPA scaling policy for prod",
    },
    {
        "tag": "Data Engineering",
        "title": "Databricks ETL Sizing",
        "query": "What's the recommended Databricks cluster config for ETL jobs?",
    },
]

# ----------------------------------------------------------------------------
# Custom Theme & Glassmorphic Styling
# ----------------------------------------------------------------------------
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    :root {
        --kv-bg: #080a0f;
        --kv-bg-glow: radial-gradient(circle at 50% -10%, rgba(99, 102, 241, 0.14), transparent 55%);
        --kv-surface: #11141d;
        --kv-surface-2: #171b26;
        --kv-surface-hover: #1e2332;
        --kv-border: rgba(255, 255, 255, 0.08);
        --kv-border-accent: rgba(99, 102, 241, 0.35);
        --kv-accent: #6366f1;
        --kv-accent-light: #818cf8;
        --kv-accent-2: #4f46e5;
        --kv-cyan: #22d3ee;
        --kv-emerald: #34d399;
        --kv-amber: #fbbf24;
        --kv-rose: #f87171;
        --kv-text: #f1f5f9;
        --kv-text-secondary: #cbd5e1;
        --kv-text-muted: #8b95a7;
        --kv-radius: 14px;
        --kv-font: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        --kv-mono: 'JetBrains Mono', monospace;
    }

    html, body, [class*="css"] {
        font-family: var(--kv-font);
    }

    code, pre {
        font-family: var(--kv-mono) !important;
    }

    .stApp {
        background-color: var(--kv-bg);
        background-image: var(--kv-bg-glow);
        background-attachment: fixed;
        color: var(--kv-text);
    }

    #MainMenu, footer, header { visibility: hidden; }

    /* ---- Custom Scrollbar ---- */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.12); border-radius: 999px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.22); }

    /* ---- Sidebar ---- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1017 0%, #11141d 100%);
        border-right: 1px solid var(--kv-border);
    }

    section[data-testid="stSidebar"] .stButton > button {
        width: 100%;
        text-align: left;
        justify-content: flex-start;
        background: transparent;
        color: var(--kv-text-muted);
        border: 1px solid transparent;
        font-weight: 500;
        font-size: 0.9rem;
        box-shadow: none;
        padding: 10px 14px;
        border-radius: 10px;
        transition: all 0.18s ease;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        background: var(--kv-surface-2);
        color: var(--kv-text);
        border-color: var(--kv-border);
        transform: translateX(2px);
    }

    /* Active nav button styling via primary kind */
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, rgba(99, 102, 241, 0.18) 0%, rgba(99, 102, 241, 0.06) 100%);
        color: #ffffff;
        border: 1px solid var(--kv-border-accent);
        font-weight: 600;
    }

    .brand-card {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 12px;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid var(--kv-border);
        border-radius: 12px;
        margin-bottom: 14px;
    }

    .brand-icon {
        width: 38px;
        height: 38px;
        border-radius: 10px;
        background: linear-gradient(135deg, var(--kv-accent) 0%, #8b5cf6 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.25rem;
        box-shadow: 0 4px 16px rgba(99, 102, 241, 0.35);
    }

    .brand-title {
        font-size: 1.08rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: var(--kv-text);
        margin: 0;
        line-height: 1.2;
    }

    .brand-sub {
        color: var(--kv-text-muted);
        font-size: 0.74rem;
        margin: 2px 0 0 0;
    }

    .sidebar-section-label {
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--kv-text-muted);
        margin: 14px 0 6px 4px;
    }

    .role-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(99, 102, 241, 0.12);
        border: 1px solid rgba(99, 102, 241, 0.28);
        color: var(--kv-accent-light);
        font-family: var(--kv-mono);
        font-size: 0.73rem;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 6px;
        margin-top: 4px;
    }

    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        padding: 5px 12px;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 600;
        border: 1px solid transparent;
    }
    .status-online {
        background: rgba(52, 211, 153, 0.1);
        color: var(--kv-emerald);
        border-color: rgba(52, 211, 153, 0.25);
    }
    .status-degraded {
        background: rgba(251, 191, 36, 0.1);
        color: var(--kv-amber);
        border-color: rgba(251, 191, 36, 0.25);
    }
    .status-offline {
        background: rgba(248, 113, 113, 0.1);
        color: var(--kv-rose);
        border-color: rgba(248, 113, 113, 0.25);
    }
    .dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: currentColor;
        display: inline-block;
        box-shadow: 0 0 8px currentColor;
    }

    /* ---- Main Container ---- */
    .main .block-container {
        max-width: 940px;
        padding-top: 1.75rem;
        padding-bottom: 7rem;
    }

    /* ---- Hero & Headers ---- */
    .hero-banner {
        background: linear-gradient(135deg, rgba(23, 27, 38, 0.9) 0%, rgba(17, 20, 29, 0.95) 100%);
        border: 1px solid var(--kv-border);
        border-radius: 18px;
        padding: 28px 30px;
        margin-bottom: 22px;
        position: relative;
        overflow: hidden;
    }

    .hero-banner::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, var(--kv-accent), var(--kv-cyan), transparent);
    }

    .hero-kicker {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--kv-cyan);
        background: rgba(34, 211, 238, 0.08);
        border: 1px solid rgba(34, 211, 238, 0.22);
        padding: 3px 10px;
        border-radius: 999px;
        margin-bottom: 10px;
    }

    .hero-title {
        font-size: 1.65rem;
        font-weight: 800;
        letter-spacing: -0.025em;
        color: var(--kv-text);
        margin: 0 0 6px 0;
    }

    .hero-sub {
        color: var(--kv-text-muted);
        font-size: 0.92rem;
        margin: 0;
        line-height: 1.5;
    }

    .capability-chips {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 16px;
    }

    .cap-chip {
        font-size: 0.74rem;
        color: var(--kv-text-secondary);
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid var(--kv-border);
        padding: 4px 10px;
        border-radius: 8px;
        font-family: var(--kv-mono);
    }

    /* ---- Chat Messages ---- */
    div[data-testid="stChatMessage"] {
        background: var(--kv-surface);
        border: 1px solid var(--kv-border);
        border-radius: 16px;
        padding: 14px 18px;
        margin-bottom: 14px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.18);
    }

    /* ---- Telemetry Pills ---- */
    .telemetry-bar {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 8px;
        margin-top: 12px;
        padding-top: 10px;
        border-top: 1px solid var(--kv-border);
    }

    .tele-pill {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        font-family: var(--kv-mono);
        font-size: 0.72rem;
        padding: 3px 9px;
        border-radius: 6px;
        background: var(--kv-surface-2);
        border: 1px solid var(--kv-border);
        color: var(--kv-text-muted);
    }

    .tele-grounded {
        background: rgba(52, 211, 153, 0.1);
        border-color: rgba(52, 211, 153, 0.28);
        color: var(--kv-emerald);
        font-weight: 600;
    }

    .tele-abstained {
        background: rgba(251, 191, 36, 0.1);
        border-color: rgba(251, 191, 36, 0.28);
        color: var(--kv-amber);
        font-weight: 600;
    }

    /* ---- Citation Cards ---- */
    .citation-card {
        background: var(--kv-surface-2);
        border: 1px solid var(--kv-border);
        border-left: 3px solid var(--kv-accent);
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 8px;
        transition: border-color 0.15s ease;
    }
    .citation-card:hover {
        border-color: var(--kv-border-accent);
    }
    .citation-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
        margin-bottom: 4px;
    }
    .citation-title {
        font-weight: 600;
        font-size: 0.86rem;
        color: var(--kv-text);
    }
    .citation-idx {
        font-family: var(--kv-mono);
        font-size: 0.72rem;
        color: var(--kv-accent-light);
        background: rgba(99, 102, 241, 0.14);
        padding: 2px 7px;
        border-radius: 5px;
    }
    .citation-meta {
        color: var(--kv-text-muted);
        font-size: 0.77rem;
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
    }

    /* ---- Trace Bars ---- */
    .trace-row {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 7px;
        font-size: 0.78rem;
    }
    .trace-label {
        width: 135px;
        font-family: var(--kv-mono);
        color: var(--kv-text-secondary);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .trace-bar-wrap {
        flex: 1;
        height: 7px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 999px;
        overflow: hidden;
    }
    .trace-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--kv-accent), var(--kv-cyan));
        border-radius: 999px;
    }
    .trace-val {
        width: 68px;
        text-align: right;
        font-family: var(--kv-mono);
        color: var(--kv-text-muted);
    }

    /* ---- Prompt Starter Cards ---- */
    .starter-label {
        font-size: 0.78rem;
        font-weight: 600;
        color: var(--kv-text-muted);
        margin-bottom: 10px;
        letter-spacing: 0.02em;
    }

    /* ---- Buttons & Inputs ---- */
    .stButton > button {
        background: linear-gradient(135deg, var(--kv-accent-2) 0%, var(--kv-accent) 100%);
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 9px 16px;
        font-weight: 600;
        font-size: 0.85rem;
        transition: all 0.16s ease;
        box-shadow: 0 2px 10px rgba(79, 70, 229, 0.25);
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        filter: brightness(1.08);
        box-shadow: 0 6px 18px rgba(99, 102, 241, 0.35);
    }

    /* Secondary buttons (example prompts) */
    .stButton > button[kind="secondary"] {
        background: var(--kv-surface);
        border: 1px solid var(--kv-border);
        color: var(--kv-text-secondary);
        box-shadow: none;
        text-align: left;
        justify-content: flex-start;
        height: auto;
        min-height: 76px;
        padding: 12px 14px;
        line-height: 1.4;
        font-weight: 500;
    }

    .stButton > button[kind="secondary"]:hover {
        background: var(--kv-surface-hover);
        border-color: var(--kv-border-accent);
        color: #ffffff;
    }

    /* ---- Bottom Chat Input & Wrapper (Fix Brown Footer Tint) ---- */
    div[data-testid="stBottom"],
    div[data-testid="stBottom"] > div,
    section[data-testid="stBottom"],
    section[data-testid="stBottom"] > div {
        background: var(--kv-bg) !important;
        background-color: var(--kv-bg) !important;
        border-top: 1px solid var(--kv-border) !important;
    }

    div[data-testid="stChatInput"] {
        max-width: 940px;
        margin: 0 auto;
        background: transparent !important;
    }
    div[data-testid="stChatInput"] > div {
        background: var(--kv-surface) !important;
        border: 1px solid var(--kv-border-accent) !important;
        border-radius: 14px !important;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.45);
    }
    div[data-testid="stChatInput"] textarea {
        background: transparent !important;
        color: var(--kv-text) !important;
    }

    /* ---- File Uploader Dropzone ---- */
    section[data-testid="stFileUploaderDropzone"],
    div[data-testid="stFileUploaderDropzone"] {
        background-color: var(--kv-surface) !important;
        border: 1px dashed var(--kv-border-accent) !important;
        border-radius: 12px !important;
        color: var(--kv-text-secondary) !important;
    }
    section[data-testid="stFileUploaderDropzone"] button,
    div[data-testid="stFileUploaderDropzone"] button {
        background: var(--kv-surface-2) !important;
        color: var(--kv-accent-light) !important;
        border: 1px solid var(--kv-border-accent) !important;
        box-shadow: none !important;
    }

    /* ---- Page Headers & Metric Cards ---- */
    .page-header {
        margin-bottom: 1.25rem;
    }
    .page-title {
        font-size: 1.5rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: var(--kv-text);
        margin: 0;
    }
    .page-sub {
        color: var(--kv-text-muted);
        font-size: 0.9rem;
        margin-top: 4px;
    }

    .metric-card {
        background: linear-gradient(180deg, var(--kv-surface-2) 0%, var(--kv-surface) 100%);
        border: 1px solid var(--kv-border);
        border-radius: 14px;
        padding: 18px 16px;
        text-align: left;
        transition: border-color 0.2s ease, transform 0.2s ease;
    }
    .metric-card:hover {
        border-color: var(--kv-border-accent);
        transform: translateY(-2px);
    }
    .metric-label {
        color: var(--kv-text-muted);
        font-size: 0.76rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 1.75rem;
        font-weight: 800;
        font-family: var(--kv-mono);
        color: var(--kv-text);
        margin: 6px 0 4px 0;
    }
    .metric-delta {
        color: var(--kv-emerald);
        font-size: 0.76rem;
        font-weight: 500;
    }

    .arch-card {
        background: var(--kv-surface);
        border: 1px solid var(--kv-border);
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 10px;
    }
    .arch-step {
        font-family: var(--kv-mono);
        font-size: 0.72rem;
        color: var(--kv-accent-light);
        font-weight: 700;
    }
    .arch-title {
        font-weight: 700;
        font-size: 0.94rem;
        color: var(--kv-text);
        margin: 2px 0 4px 0;
    }
    .arch-desc {
        font-size: 0.83rem;
        color: var(--kv-text-muted);
        margin: 0;
        line-height: 1.45;
    }

    .empty-box {
        border: 1px dashed var(--kv-border);
        background: rgba(255, 255, 255, 0.015);
        border-radius: 14px;
        padding: 36px 20px;
        text-align: center;
        color: var(--kv-text-muted);
    }
</style>
""",
    unsafe_allow_html=True,
)

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

DEMO_CREDENTIALS = {
    "public_guest": ("public_guest", "GuestPass2026!", "PUBLIC_USER", "Public Guest"),
    "internal_analyst": ("internal_analyst", "InternalPass2026!", "INTERNAL_USER", "Internal Analyst"),
    "admin": ("admin", "AdminPass2026!", "ADMIN", "System Administrator"),
}


# ----------------------------------------------------------------------------
# Authentication & Backend Calls
# ----------------------------------------------------------------------------
def login_to_backend(username: str, password: str) -> bool:
    try:
        resp = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={"username": username, "password": password},
            timeout=5,
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
    token = st.session_state.get("auth_token")
    if not token:
        u, p, _, _ = DEMO_CREDENTIALS.get(
            st.session_state.get("auth_user", "public_guest"),
            DEMO_CREDENTIALS["public_guest"],
        )
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
    res = requests.post(
        f"{API_BASE_URL}/query",
        json=payload,
        headers=get_auth_headers(),
        timeout=45,
    )
    res.raise_for_status()
    return res.json()


def render_citations(citations):
    if not citations:
        return
    with st.expander(f"📚 Grounded Sources ({len(citations)})", expanded=False):
        for cit in citations:
            page_html = f"<span>Page {cit.get('page')}</span>" if cit.get("page") else ""
            st.markdown(
                f"""
                <div class="citation-card">
                    <div class="citation-header">
                        <span class="citation-title">📄 {cit.get('document_name', 'Unknown Document')}</span>
                        <span class="citation-idx">Source {cit.get('source_index', '?')}</span>
                    </div>
                    <div class="citation-meta">
                        <span>Section: <strong>{cit.get('section', 'General')}</strong></span>
                        <span>Access: <code>{cit.get('access_level', 'PUBLIC_USER')}</code></span>
                        {page_html}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_meta(msg):
    grounded = not msg.get("is_abstained", False)
    status_cls = "tele-grounded" if grounded else "tele-abstained"
    status_txt = "✓ Grounded" if grounded else "⚠ Abstained"

    pills = [
        f'<span class="tele-pill {status_cls}">{status_txt}</span>',
        f'<span class="tele-pill">⏱ {msg.get("latency", 0):.0f} ms</span>',
        f'<span class="tele-pill">🧩 {msg.get("chunks_count", 0)} chunks</span>',
    ]

    tokens = msg.get("tokens") or {}
    if tokens.get("total_tokens"):
        pills.append(f'<span class="tele-pill">🔤 {tokens["total_tokens"]} tok</span>')

    if msg.get("cost") is not None and msg.get("cost") > 0:
        pills.append(f'<span class="tele-pill">💲 ${msg["cost"]:.5f}</span>')

    st.markdown(f'<div class="telemetry-bar">{"".join(pills)}</div>', unsafe_allow_html=True)

    trace = msg.get("trace")
    if trace and trace.get("spans"):
        spans = trace.get("spans", [])
        max_dur = max((s.get("duration_ms", 0) for s in spans), default=1) or 1
        with st.expander("⚡ Pipeline Execution Trace", expanded=False):
            bars_html = []
            for span in spans:
                stage_name = span.get("stage", "").replace("_", " ").title()
                dur = span.get("duration_ms", 0.0)
                pct = min(max((dur / max_dur) * 100, 3), 100)
                bars_html.append(
                    f"""
                    <div class="trace-row">
                        <div class="trace-label">{stage_name}</div>
                        <div class="trace-bar-wrap">
                            <div class="trace-bar-fill" style="width:{pct:.1f}%;"></div>
                        </div>
                        <div class="trace-val">{dur:.1f} ms</div>
                    </div>
                    """
                )
            st.markdown("".join(bars_html), unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div class="brand-card">
            <div class="brand-icon">🧠</div>
            <div>
                <p class="brand-title">Knowvia AI</p>
                <p class="brand-sub">Hybrid RAG & RBAC Engine</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sidebar-section-label">Workspace</div>', unsafe_allow_html=True)
    nav_items = [
        ("chat", "💬  Intelligence Chat"),
        ("docs", "📂  Knowledge Base"),
        ("bench", "📊  Benchmarks & Architecture"),
    ]
    for key, label in nav_items:
        is_active = st.session_state.view == key
        if st.button(
            label,
            key=f"nav_{key}",
            type="primary" if is_active else "secondary",
            use_container_width=True,
        ):
            st.session_state.view = key
            st.rerun()

    st.markdown('<div class="sidebar-section-label">Access Control (RBAC)</div>', unsafe_allow_html=True)
    user_key = st.selectbox(
        "Demo Identity",
        options=["public_guest", "internal_analyst", "admin"],
        format_func=lambda k: DEMO_CREDENTIALS[k][3],
        index=["public_guest", "internal_analyst", "admin"].index(
            st.session_state.get("auth_user", "public_guest")
        ),
        label_visibility="collapsed",
    )

    if user_key != st.session_state.get("auth_user"):
        u, p, r, _ = DEMO_CREDENTIALS[user_key]
        if login_to_backend(u, p):
            fetch_documents.clear()
            st.toast(f"Switched identity to {DEMO_CREDENTIALS[user_key][3]}", icon="🔐")
            st.rerun()

    st.markdown(
        f'<div class="role-badge">🛡️ {st.session_state.get("auth_role", "PUBLIC_USER")}</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.view == "chat":
        st.markdown('<div class="sidebar-section-label">Retrieval Controls</div>', unsafe_allow_html=True)
        with st.expander("⚙️ Search & Rerank Settings", expanded=False):
            st.session_state.top_k = st.slider("Top-K Chunks", 1, 10, st.session_state.top_k)
            st.session_state.filter_doc_type = st.selectbox(
                "Document Category",
                options=["All", "technical_documentation", "architecture", "api_spec"],
                index=["All", "technical_documentation", "architecture", "api_spec"].index(
                    st.session_state.filter_doc_type
                ),
            )

        if st.session_state.messages:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button("🗑️  Clear Conversation", type="secondary", use_container_width=True):
                st.session_state.messages = []
                st.session_state.chat_history = []
                st.rerun()

    st.markdown("---")
    status_col, refresh_col = st.columns([3.2, 1])
    try:
        status_code = check_health()
        if status_code == 200:
            status_col.markdown(
                '<span class="status-pill status-online"><span class="dot"></span>API Online</span>',
                unsafe_allow_html=True,
            )
        else:
            status_col.markdown(
                '<span class="status-pill status-degraded"><span class="dot"></span>API Degraded</span>',
                unsafe_allow_html=True,
            )
    except Exception:
        status_col.markdown(
            '<span class="status-pill status-offline"><span class="dot"></span>API Offline</span>',
            unsafe_allow_html=True,
        )

    if refresh_col.button("↻", key="ref_health", type="secondary", use_container_width=True):
        check_health.clear()
        st.rerun()


# ----------------------------------------------------------------------------
# VIEW: Chat & Query Engine
# ----------------------------------------------------------------------------
if st.session_state.view == "chat":
    st.markdown(
        """
        <div class="hero-banner">
            <div class="hero-kicker">⚡ Hybrid Dense + BM25 • Cross-Encoder Reranked</div>
            <h1 class="hero-title">Intelligence Playground</h1>
            <p class="hero-sub">
                Query your indexed infrastructure, architecture, and policy corpus with pre-retrieval role filtering and citation verification.
            </p>
            <div class="capability-chips">
                <span class="cap-chip">Qdrant 384d</span>
                <span class="cap-chip">BM25Okapi + RRF</span>
                <span class="cap-chip">ms-marco-MiniLM-L-6-v2</span>
                <span class="cap-chip">Evidence Abstention</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    picked_example = None
    if not st.session_state.messages:
        st.markdown('<div class="starter-label">✨ Try an example query</div>', unsafe_allow_html=True)
        ex_cols = st.columns(len(EXAMPLE_PROMPTS))
        for col, ex in zip(ex_cols, EXAMPLE_PROMPTS):
            btn_label = f"{ex['tag']} · {ex['title']}\n\n{ex['query']}"
            if col.button(btn_label, type="secondary", use_container_width=True, key=f"ex_{ex['title']}"):
                picked_example = ex["query"]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "🧠"):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "latency" in msg:
                render_meta(msg)
                render_citations(msg.get("citations"))

    typed_prompt = st.chat_input("Ask about Kubernetes, HPA, Databricks, or indexed docs...")
    prompt = typed_prompt or picked_example

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🧠"):
            with st.spinner("Running hybrid retrieval, reranking & evidence check…"):
                try:
                    doc_filter = (
                        None
                        if st.session_state.filter_doc_type == "All"
                        else st.session_state.filter_doc_type
                    )
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
                    cost_val = data.get("estimated_cost_usd")

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
                        "cost": cost_val,
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
    st.markdown(
        """
        <div class="page-header">
            <h1 class="page-title">📂 Knowledge Base Management</h1>
            <p class="page-sub">Ingest documents into Qdrant & BM25 with role-based access levels (public, internal, restricted).</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("📤 Upload & Index New Document", expanded=False):
        uploaded_file = st.file_uploader(
            "Select Markdown, PDF, DOCX, TXT, or HTML file",
            type=["md", "markdown", "pdf", "docx", "txt", "html"],
        )
        up_col1, up_col2 = st.columns(2)
        access_lvl = up_col1.selectbox("Access Level", ["public", "internal", "restricted"])
        doc_category = up_col2.selectbox("Document Category", ["technical", "architecture", "policy"])

        if st.button("🚀 Upload and Index", disabled=uploaded_file is None):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                payload = {"access_level": access_lvl, "document_type": doc_category}
                up_res = requests.post(
                    f"{API_BASE_URL}/documents/upload",
                    files=files,
                    data=payload,
                    headers=get_auth_headers(),
                    timeout=60,
                )
                if up_res.status_code == 200:
                    st.success(f"Successfully ingested `{uploaded_file.name}` into Qdrant & BM25.")
                    fetch_documents.clear()
                    time.sleep(0.8)
                    st.rerun()
                else:
                    st.error(f"Ingestion failed: {up_res.text}")
            except Exception as e:
                st.error(f"Error connecting to backend: {e}")

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    header_col, search_col, refresh_col = st.columns([2.2, 2, 0.8])
    header_col.markdown(
        f"**Indexed Corpus**  <span class='role-badge'>Visible to {st.session_state.get('auth_role')}</span>",
        unsafe_allow_html=True,
    )
    search_term = search_col.text_input(
        "Search", placeholder="🔍 Filter documents by name…", label_visibility="collapsed"
    )
    if refresh_col.button("↻ Refresh", type="secondary", use_container_width=True):
        fetch_documents.clear()

    try:
        docs = fetch_documents()
        if search_term:
            docs = [d for d in docs if search_term.lower() in d["document_name"].lower()]

        if not docs:
            st.markdown(
                '<div class="empty-box">No documents visible for your current role or search filter.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.dataframe(
                [
                    {
                        "Document Name": d["document_name"],
                        "Document ID": d["document_id"],
                        "Access Tier": d["access_level"].upper(),
                        "Indexed Chunks": d["chunk_count"],
                    }
                    for d in docs
                ],
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            del_col1, del_col2 = st.columns([3.2, 1])
            doc_to_delete = del_col1.selectbox(
                "Select document to delete",
                options=[d["document_id"] for d in docs],
                format_func=lambda did: next(d["document_name"] for d in docs if d["document_id"] == did),
                label_visibility="collapsed",
            )
            if del_col2.button("🗑️ Delete Document", type="secondary", use_container_width=True):
                del_res = requests.delete(
                    f"{API_BASE_URL}/documents/{doc_to_delete}",
                    headers=get_auth_headers(),
                )
                if del_res.status_code == 200:
                    st.success(f"Deleted `{doc_to_delete}` and rebuilt BM25 index.")
                    fetch_documents.clear()
                    time.sleep(0.8)
                    st.rerun()
                elif del_res.status_code == 403:
                    st.error(
                        f"Permission Denied: Deletion requires ADMIN role (current: {st.session_state.get('auth_role')})."
                    )
                else:
                    st.error(f"Delete failed: {del_res.text}")
    except Exception as e:
        st.error(f"Error fetching documents list: {e}")


# ----------------------------------------------------------------------------
# VIEW: Benchmarks & Architecture
# ----------------------------------------------------------------------------
elif st.session_state.view == "bench":
    st.markdown(
        """
        <div class="page-header">
            <h1 class="page-title">📊 System Benchmarks & Architecture</h1>
            <p class="page-sub">Evaluation snapshot across 60 benchmark queries (30 development / 30 held-out test) and 4-route hybrid pipeline.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    b1, b2, b3, b4 = st.columns(4)
    metrics = [
        (b1, "Recall@5 (Hybrid)", "1.000", "+16.7% vs Dense Only"),
        (b2, "MRR (Hybrid)", "0.792", "Weighted RRF (k=60)"),
        (b3, "Answer Relevancy", "0.923", "Groq LLM Judge (n=30)"),
        (b4, "Abstention F1", "1.000", "Zero OOS Hallucination"),
    ]
    for col, label, value, delta in metrics:
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                    <div class="metric-delta">{delta}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    st.markdown("#### 🏗️ End-to-End Pipeline Stages")

    stages = [
        (
            "STAGE 01 · AUTH & INPUT GUARDRAILS",
            "Pre-Retrieval JWT Identity & Pattern Checks",
            "Server-minted JWT claims enforce PUBLIC_USER, INTERNAL_USER, and ADMIN access filters prior to vector/lexical scoring, paired with prompt-injection pattern screening.",
        ),
        (
            "STAGE 02 · INTENT ROUTING",
            "Four-Route Query Classifier",
            "Routes incoming requests across CONVERSATIONAL, OUT_OF_SCOPE, HYBRID, and KNOWLEDGE paths to avoid unnecessary retrieval overhead.",
        ),
        (
            "STAGE 03 · HYBRID RETRIEVAL & FUSION",
            "Dense Qdrant (384d) + BM25Okapi via Weighted RRF",
            "Combines semantic embeddings (all-MiniLM-L6-v2) with exact lexical keyword matching using Reciprocal Rank Fusion (k=60).",
        ),
        (
            "STAGE 04 · RERANKING & EVIDENCE GATE",
            "Cross-Encoder Scoring & Multi-Signal Abstention",
            "Re-scores top candidates with ms-marco-MiniLM-L-6-v2 and classifies support as strong, partial, or insufficient before generation.",
        ),
        (
            "STAGE 05 · GROUNDED GENERATION & TRACING",
            "Citation Enforcement, Redaction & Observability",
            "Marks retrieved chunks as untrusted context, enforces [Source X] citations, redacts secret-like patterns, and logs per-stage latency and token costs.",
        ),
    ]

    for step_tag, title, desc in stages:
        st.markdown(
            f"""
            <div class="arch-card">
                <div class="arch-step">{step_tag}</div>
                <div class="arch-title">{title}</div>
                <p class="arch-desc">{desc}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )