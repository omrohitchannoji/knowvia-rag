# DATASET CORPUS DOCUMENTATION & ATTRIBUTION

This directory contains the document corpus for the **Technical Documentation & Policy Intelligence RAG System**.

---

## Corpus Layout

```
data/
├── README.md        # Dataset manifest, attribution & licensing notes
├── TrueData/        # Category A: Clean System Architecture, SLAs & Operations Docs
│   ├── architecture.pptx        # System Architecture & Topology Presentation
│   ├── cronjobs.docx            # Automated Job Scheduling & Maintenance Policy
│   ├── job_management.html      # Job Lifecycle & Task Orchestration Manual
│   ├── monitor_job.docx         # Health Monitoring & Alerting Specification
│   ├── parallel_work_queue.txt  # Asynchronous Queue & Worker Thread Design
│   └── pods_autoscale.html      # Pod Auto-scaling & Resource Management Guide
└── NoisyData/       # Category B: Multi-Format Complex Technical Corpus (PDFs, PPTX, HTML, TXT)
    ├── 100G Networking Technology Overview.pdf
    ├── 2018 CppCon Unwinding the Stack.pdf
    ├── 5-Level Paging and 5-Level EPT (Intel).pdf
    ├── A GPU-friendly Skiplist Algorithm.pdf
    ├── A Journey in Creating an Operating System Kernel.pdf / .html / .txt
    ├── A Mathematical Theory of Communication (Shannon).pdf / .pptx
    ├── A Pattern Language (Alexander).pdf / .txt
    └── ... (50+ Real-World Technical Papers, RFCs & Systems Docs)
```

---

## Document Manifest & Categories

| Dataset Category | Directory | File Formats | Primary Technical Purpose |
| :--- | :--- | :--- | :--- |
| **Clean Authoritative Specs** | `data/TrueData/` | `.pptx`, `.docx`, `.html`, `.txt` | Tests clean document ingestion, SLA lookup, cronjob scheduling, and pod auto-scaling queries. |
| **Complex Technical Corpus** | `data/NoisyData/` | `.pdf`, `.pptx`, `.html`, `.txt` | Tests multi-format extraction, low-level systems keyword search, complex PDF layout parsing, and BM25 tokenization. |

---

## Legal & Licensing Notice

1. **Clean Specs (`TrueData`):** Contains organizational architecture, SLA, and operational runbook documentation formatted across PPTX, DOCX, HTML, and TXT files.
2. **Technical & Academic Literature (`NoisyData`):** Technical papers, public slides, and educational standards included for evaluation of multi-format document parsing and large-scale technical retrieval.
