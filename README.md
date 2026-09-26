# 🧠 Knowvia AI — Grounded Knowledge & Document Intelligence Platform

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Qdrant](https://img.shields.io/badge/VectorDB-Qdrant%20Cloud-dc2626.svg)](https://qdrant.tech/)
[![Groq](https://img.shields.io/badge/LLM-Groq%20Cloud-f97316.svg)](https://groq.com/)

**Knowvia AI** is an enterprise-grade Retrieval-Augmented Generation (RAG) platform designed to deliver precise, citation-backed answers from complex technical documentation and noisy data corpora.

---

## 🌐 Live Deployments

* **Frontend UI (Streamlit Cloud):** [Deploy / Access App on Streamlit Cloud](https://share.streamlit.io)
* **API Server (AWS EC2 Static IP):** `http://13.205.104.107:8000/api/v1`
* **Swagger API Documentation:** `http://13.205.104.107:8000/docs`
* **Health Endpoint:** `http://13.205.104.107:8000/api/v1/health`

---

## ✨ Key Features

* **🔍 Hybrid Search Engine:** Combines Dense Vector Search (`sentence-transformers/all-MiniLM-L6-v2`) with Sparse BM25 Keyword Search fused via **Reciprocal Rank Fusion (RRF)**.
* **🎯 Cross-Encoder Reranking:** Re-scores retrieved candidate chunks using `cross-encoder/ms-marco-MiniLM-L-6-v2` for maximum precision.
* **🧠 Adaptive Intent Routing:** Automatically detects query complexity and routes queries across optimal strategies (`HYBRID`, `DENSE`, `SPARSE`, `DIRECT`).
* **🛡️ Answerability & Guardrails:** Evaluates relevance confidence before generating answers to mitigate hallucinations and restrict out-of-domain responses.
* **💬 Citation & Source Verification:** Every generated answer is grounded in exact source document chunks with page/file citations.
* **🎨 Modern Streamlit Glassmorphic UI:** Features dark-mode aesthetics, prompt shortcuts, document filters, and live benchmark metrics.

---

## 🏗️ Architecture Overview

```
                          ┌──────────────────────────┐
                          │   Streamlit Cloud UI     │
                          └────────────┬─────────────┘
                                       │ HTTP / REST API
                                       ▼
                          ┌──────────────────────────┐
                          │   AWS EC2 FastAPI Backend│
                          │   (Static: 13.205.104.107)│
                          └─────┬──────────────┬─────┘
                                │              │
                    ┌───────────┴──┐        ┌──┴─────────────┐
                    │ Qdrant Cloud │        │ Groq LLM API   │
                    │ Vector DB    │        │ (gpt-oss-20b)  │
                    └──────────────┘        └────────────────┘
```

---

## 📁 Repository Structure

```text
├── backend/
│   └── app/
│       ├── api/               # FastAPI endpoints (/query, /documents, /health)
│       ├── answerability/     # Confidence evaluation & hallucination guards
│       ├── core/              # Global config & logging
│       ├── embeddings/        # SentenceTransformer embedding service
│       ├── generation/        # LLM client (Groq) & prompt templates
│       ├── ingestion/         # Document parsing & chunking pipeline
│       ├── retrieval/         # Dense, BM25, Hybrid RRF & Reranker modules
│       └── security/          # Access control & guardrails
├── frontend/
│   └── app.py                 # Streamlit UI application
├── data/                      # Sample document corpora & benchmarks
├── evaluation/                # Retrieval & generation benchmark suite
├── tests/                     # Pytest suite (43 passing tests)
├── Dockerfile                 # Container image specification
└── docker-compose.yml         # Local orchestration config
```

---

## 🚀 Quickstart (Local Development)

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/omrohitchannoji/knowvia-rag.git
cd knowvia-rag

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory:
```ini
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-20b
GROQ_API_KEY=your_groq_api_key

VECTOR_DB_TYPE=qdrant
QDRANT_URL=https://your-cluster-id.cloud.qdrant.io:6333
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_COLLECTION=tech_doc_collection

EMBEDDING_PROVIDER=sentence_transformers
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
```

### 3. Run FastAPI Backend Server
```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Run Streamlit Frontend
In a separate terminal window:
```bash
streamlit run frontend/app.py
```
Open `http://localhost:8501` in your browser.

---

## 🧪 Running Tests & Benchmarks

Run the complete test suite:
```bash
pytest
```

Run retrieval evaluation benchmark:
```bash
python evaluation/run_eval.py
```

---

## 🛠️ Deployment Details

| Component | Provider | Details |
| :--- | :--- | :--- |
| **Frontend UI** | Streamlit Community Cloud | Continuous Deployment from `main` branch |
| **Backend API** | AWS EC2 (`t3.small`) | Permanent Elastic IP: `13.205.104.107:8000` |
| **Vector DB** | Qdrant Cloud | Indexed collection with payload filters |
| **LLM Inference** | Groq Cloud | Ultra-low latency LPU execution (`openai/gpt-oss-20b`) |

---

## 📜 License
Distributed under the MIT License. See `LICENSE` for more information.
