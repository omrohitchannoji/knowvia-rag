# DATASET CORPUS DOCUMENTATION & ATTRIBUTION

This directory contains the document corpus for the **Technical Documentation & Policy Intelligence RAG System**.

---

## Corpus Structure

```
data/
├── README.md                  # Dataset manifest, attribution & licensing notes
├── technical/                 # Category A: Real Authoritative Technical & Security Docs
│   ├── fastapi/               # FastAPI documentation excerpts (Markdown)
│   ├── docker/                # Docker documentation excerpts (Markdown)
│   └── owasp/                 # OWASP & NIST security guidance excerpts (Markdown/PDF)
└── synthetic_policies/        # Category B: Controlled Synthetic Organizational Policies
    ├── nexacloud_sec_v1.md    # Deprecated Security Policy v1.0
    ├── nexacloud_sec_v2.md    # Active Security Policy v2.0
    ├── nexacloud_access.md    # Restricted Production Access Policy
    ├── nexacloud_ir_retention.md # Incident Response & Data Retention Policy
    └── nexacloud_backup.md    # Data Backup & Recovery Policy
```

---

## Document Manifest & Licensing Table

| Document Identifier | Document Name | Source Organization | Original URL | License | Type | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `fastapi_core` | FastAPI Core Guide | FastAPI / Sebastián Ramírez | `https://github.com/tiangolo/fastapi` | MIT License | Technical | Official |
| `docker_engine` | Docker Engine Overview | Docker Inc. | `https://github.com/docker/docs` | Apache 2.0 | Technical | Official |
| `owasp_top10` | OWASP Top 10 Security Guidance | OWASP Foundation | `https://owasp.org/www-project-top-ten/` | CC BY 3.0 | Security | Official |
| `nist_sp800_53` | NIST SP 800-53 Excerpts | NIST (US Dept. of Commerce) | `https://csrc.nist.gov/` | Public Domain | Security | Official |
| `nexacloud_sec_v1` | NexaCloud Security Policy v1.0 | NexaCloud Inc. (Synthetic) | `synthetic://nexacloud/policies` | Synthetic / Public Domain | Policy | Expired |
| `nexacloud_sec_v2` | NexaCloud Security Policy v2.0 | NexaCloud Inc. (Synthetic) | `synthetic://nexacloud/policies` | Synthetic / Public Domain | Policy | Active |
| `nexacloud_access` | NexaCloud Production Access Policy | NexaCloud Inc. (Synthetic) | `synthetic://nexacloud/policies` | Synthetic / Public Domain | Policy | Active (Restricted) |

---

## Attribution & Legal Notice

1. **Third-Party Open-Source Content:** Technical documentation from FastAPI, Docker, OWASP, and NIST is included for educational and portfolio demonstration under their respective open-source licenses (MIT, Apache 2.0, CC BY 3.0, and US Public Domain). Original copyright remains with the respective authors and organizations.
2. **Synthetic Data Disclaimer:** All NexaCloud documents are **100% synthetic demonstration data** created specifically for testing versioning, temporal queries, access control, and prompt injection defenses. They do not represent real-world corporate policies or secrets.
