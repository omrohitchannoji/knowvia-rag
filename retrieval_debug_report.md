# NexaCloud RAG Retrieval & Reranking Diagnostic Report

This report presents empirical diagnostic trace data for queries executed through the NexaCloud RAG Pipeline.
No algorithm, threshold, or model modifications were applied during this diagnostic run.

---

## Query: `explain api`

- **Intent:** `knowledge`
- **Final Search Query:** `Explain the NexaCloud API`
- **Contextualized:** `False`
- **Retrieval Executed:** `True`
- **Top Reranker Score:** `0.3277`
- **Threshold:** `0.3`
- **Abstained:** `False`

### 1. Dense Vector Search Candidates (Top-10 Before RRF)

| Rank | Chunk ID | Cosine Score | Document | Section | Access Level |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_nexacloud_sec_v2_chk_002` | `0.6473` | `NexaCloud Information Security Policy v2.0` | `1. Purpose & Scope` | `internal` |
| 2 | `doc_README_chk_004` | `0.6466` | `README.md` | `Attribution & Legal Notice` | `public` |
| 3 | `doc_nexacloud_sec_v2_chk_001` | `0.6371` | `NexaCloud Information Security Policy v2.0` | `NexaCloud Information Security Policy v2.0` | `internal` |
| 4 | `doc_nexacloud_sec_v2_chk_003` | `0.5908` | `NexaCloud Information Security Policy v2.0` | `2. Updated User Authentication Requirements` | `internal` |
| 5 | `doc_nexacloud_prompt_inj_v1_chk_002` | `0.5826` | `NexaCloud Employee Onboarding & Security Guidance` | `2. Equipment Provisioning` | `internal` |
| 6 | `doc_nexacloud_sec_v2_chk_006` | `0.5712` | `NexaCloud Information Security Policy v2.0` | `3. Production System Access` | `internal` |
| 7 | `doc_nexacloud_ir_retention_v1_chk_001` | `0.5589` | `NexaCloud Incident Response & Data Retention Policy` | `1. Incident Severity Classification & SLAs` | `internal` |
| 8 | `doc_nexacloud_prompt_inj_v1_chk_003` | `0.5514` | `NexaCloud Employee Onboarding & Security Guidance` | `3. Workplace Communication Rules` | `internal` |
| 9 | `doc_nexacloud_backup_v1_chk_001` | `0.5514` | `NexaCloud Data Backup & Recovery Policy` | `1. Overview` | `internal` |
| 10 | `doc_nexacloud_prompt_inj_v1_chk_001` | `0.5434` | `NexaCloud Employee Onboarding & Security Guidance` | `1. Welcome to NexaCloud` | `internal` |

### 2. BM25 Sparse Search Candidates (Top-10 Before RRF)

| Rank | Chunk ID | BM25 Score | Document | Section | Access Level |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_api_test_policy_chk_001` | `4.5441` | `api_test_policy.md` | `API Test Policy` | `PUBLIC_USER` |
| 2 | `doc_fastapi_security_chk_001` | `2.8995` | `FastAPI Security & OAuth2 Bearer Authentication` | `1. Overview of Security Tools` | `public` |
| 3 | `doc_nexacloud_sec_v2_chk_004` | `2.4985` | `NexaCloud Information Security Policy v2.0` | `2.1 Password Complexity Rules` | `internal` |
| 4 | `doc_docker_engine_chk_002` | `0.7379` | `docker_engine.md` | `Key Instructions:` | `public` |
| 5 | `doc_docker_basics_chk_001` | `0.6863` | `Docker Basics & Dockerfile Reference` | `1. Core Architecture` | `public` |
| 6 | `doc_README_chk_001` | `0.6842` | `README.md` | `DATASET CORPUS DOCUMENTATION & ATTRIBUTION` | `public` |
| 7 | `doc_nexacloud_sec_v2_chk_002` | `0.6537` | `NexaCloud Information Security Policy v2.0` | `1. Purpose & Scope` | `internal` |
| 8 | `doc_nexacloud_ir_retention_v1_chk_003` | `0.5924` | `NexaCloud Incident Response & Data Retention Policy` | `3. Data Retention Schedule` | `internal` |
| 9 | `doc_nexacloud_ir_retention_v1_chk_002` | `0.5519` | `NexaCloud Incident Response & Data Retention Policy` | `2. Mandatory Reporting Procedures` | `internal` |
| 10 | `doc_owasp_top10_chk_002` | `0.5415` | `OWASP Top 10 Web Application Security Risks` | `Common Vulnerabilities:` | `public` |

### 3. Reciprocal Rank Fusion (RRF) Candidates

| Fused Rank | Chunk ID | Dense Rank | BM25 Rank | RRF Score | Calculation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_nexacloud_sec_v2_chk_002` | `1` | `7` | `0.015659` | `DenseRank(1): 0.008197 + BM25Rank(7): 0.007463 = 0.015659` |
| 2 | `doc_api_test_policy_chk_001` | `None` | `1` | `0.008197` | `DenseRank(None): 0.000000 + BM25Rank(1): 0.008197 = 0.008197` |
| 3 | `doc_README_chk_004` | `2` | `None` | `0.008065` | `DenseRank(2): 0.008065 + BM25Rank(None): 0.000000 = 0.008065` |
| 4 | `doc_fastapi_security_chk_001` | `None` | `2` | `0.008065` | `DenseRank(None): 0.000000 + BM25Rank(2): 0.008065 = 0.008065` |
| 5 | `doc_nexacloud_sec_v2_chk_001` | `3` | `None` | `0.007937` | `DenseRank(3): 0.007937 + BM25Rank(None): 0.000000 = 0.007937` |

### 4. Cross-Encoder Reranking & Sigmoid Logits

| Candidate | Chunk ID | Document | Raw Logit | Sigmoid Prob | Text Length | Preview |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_nexacloud_sec_v2_chk_002` | `NexaCloud Information Security Policy v2.0` | `-0.7186` | `0.3277` | 290 chars | `[Document: NexaCloud Information Security Policy v2.0 | Lineage: NexaCloud Information Security Poli...` |
| 2 | `doc_api_test_policy_chk_001` | `api_test_policy.md` | `-10.9933` | `0.0` | 126 chars | `[Document: api_test_policy.md | Lineage: API Test Policy]  API tokens for public integrations must b...` |
| 3 | `doc_README_chk_004` | `README.md` | `-1.5646` | `0.173` | 707 chars | `[Document: README.md | Lineage: DATASET CORPUS DOCUMENTATION & ATTRIBUTION > Attribution & Legal Not...` |
| 4 | `doc_fastapi_security_chk_001` | `FastAPI Security & OAuth2 Bearer Authentication` | `-11.1952` | `0.0` | 301 chars | `[Document: FastAPI Security & OAuth2 Bearer Authentication | Lineage: FastAPI Security & OAuth2 Bear...` |
| 5 | `doc_nexacloud_sec_v2_chk_001` | `NexaCloud Information Security Policy v2.0` | `-2.4691` | `0.078` | 250 chars | `[Document: NexaCloud Information Security Policy v2.0 | Lineage: NexaCloud Information Security Poli...` |

---

## Query: `explain api specifications`

- **Intent:** `knowledge`
- **Final Search Query:** `explain API specifications`
- **Contextualized:** `False`
- **Retrieval Executed:** `True`
- **Top Reranker Score:** `0.005`
- **Threshold:** `0.3`
- **Abstained:** `True`

### 1. Dense Vector Search Candidates (Top-10 Before RRF)

| Rank | Chunk ID | Cosine Score | Document | Section | Access Level |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_fastapi_core_chk_001` | `0.4383` | `FastAPI Core & Dependency Injection Guide` | `1. Introduction to FastAPI` | `public` |
| 2 | `doc_fastapi_security_chk_001` | `0.3533` | `FastAPI Security & OAuth2 Bearer Authentication` | `1. Overview of Security Tools` | `public` |
| 3 | `doc_fastapi_core_chk_004` | `0.3519` | `FastAPI Core & Dependency Injection Guide` | `3.1 Benefits of `Depends`` | `public` |
| 4 | `doc_README_chk_003` | `0.3182` | `README.md` | `Document Manifest & Licensing Table` | `public` |
| 5 | `doc_README_chk_002` | `0.3024` | `README.md` | `Corpus Structure` | `public` |
| 6 | `doc_owasp_top10_chk_003` | `0.2896` | `OWASP Top 10 Web Application Security Risks` | `Mitigation Strategies:` | `public` |
| 7 | `doc_fastapi_core_chk_002` | `0.2889` | `FastAPI Core & Dependency Injection Guide` | `2. Path & Query Parameters` | `public` |
| 8 | `doc_fastapi_core_chk_003` | `0.2886` | `FastAPI Core & Dependency Injection Guide` | `3. Dependency Injection System` | `public` |
| 9 | `doc_README_chk_004` | `0.2878` | `README.md` | `Attribution & Legal Notice` | `public` |
| 10 | `doc_nexacloud_backup_v1_chk_001` | `0.2795` | `NexaCloud Data Backup & Recovery Policy` | `1. Overview` | `internal` |

### 2. BM25 Sparse Search Candidates (Top-10 Before RRF)

| Rank | Chunk ID | BM25 Score | Document | Section | Access Level |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_api_test_policy_chk_001` | `4.5441` | `api_test_policy.md` | `API Test Policy` | `PUBLIC_USER` |
| 2 | `doc_fastapi_security_chk_003` | `3.7779` | `FastAPI Security & OAuth2 Bearer Authentication` | `3. Error Codes & Handling` | `public` |
| 3 | `doc_fastapi_security_chk_001` | `2.8995` | `FastAPI Security & OAuth2 Bearer Authentication` | `1. Overview of Security Tools` | `public` |
| 4 | `doc_nexacloud_sec_v2_chk_004` | `2.3558` | `NexaCloud Information Security Policy v2.0` | `2.1 Password Complexity Rules` | `internal` |

### 3. Reciprocal Rank Fusion (RRF) Candidates

| Fused Rank | Chunk ID | Dense Rank | BM25 Rank | RRF Score | Calculation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_fastapi_security_chk_001` | `2` | `3` | `0.016001` | `DenseRank(2): 0.008065 + BM25Rank(3): 0.007937 = 0.016001` |
| 2 | `doc_fastapi_core_chk_001` | `1` | `None` | `0.008197` | `DenseRank(1): 0.008197 + BM25Rank(None): 0.000000 = 0.008197` |
| 3 | `doc_api_test_policy_chk_001` | `None` | `1` | `0.008197` | `DenseRank(None): 0.000000 + BM25Rank(1): 0.008197 = 0.008197` |
| 4 | `doc_fastapi_security_chk_003` | `None` | `2` | `0.008065` | `DenseRank(None): 0.000000 + BM25Rank(2): 0.008065 = 0.008065` |
| 5 | `doc_fastapi_core_chk_004` | `3` | `None` | `0.007937` | `DenseRank(3): 0.007937 + BM25Rank(None): 0.000000 = 0.007937` |

### 4. Cross-Encoder Reranking & Sigmoid Logits

| Candidate | Chunk ID | Document | Raw Logit | Sigmoid Prob | Text Length | Preview |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_fastapi_security_chk_001` | `FastAPI Security & OAuth2 Bearer Authentication` | `-8.9827` | `0.0001` | 301 chars | `[Document: FastAPI Security & OAuth2 Bearer Authentication | Lineage: FastAPI Security & OAuth2 Bear...` |
| 2 | `doc_fastapi_core_chk_001` | `FastAPI Core & Dependency Injection Guide` | `-6.9095` | `0.001` | 470 chars | `[Document: FastAPI Core & Dependency Injection Guide | Lineage: FastAPI Core & Dependency Injection ...` |
| 3 | `doc_api_test_policy_chk_001` | `api_test_policy.md` | `-5.2927` | `0.005` | 126 chars | `[Document: api_test_policy.md | Lineage: API Test Policy]  API tokens for public integrations must b...` |
| 4 | `doc_fastapi_security_chk_003` | `FastAPI Security & OAuth2 Bearer Authentication` | `-10.4882` | `0.0` | 423 chars | `[Document: FastAPI Security & OAuth2 Bearer Authentication | Lineage: FastAPI Security & OAuth2 Bear...` |
| 5 | `doc_fastapi_core_chk_004` | `FastAPI Core & Dependency Injection Guide` | `-10.9842` | `0.0` | 325 chars | `[Document: FastAPI Core & Dependency Injection Guide | Lineage: FastAPI Core & Dependency Injection ...` |

---

## Query: `what are the api token refresh requirements`

- **Intent:** `knowledge`
- **Final Search Query:** `api token refresh requirements`
- **Contextualized:** `False`
- **Retrieval Executed:** `True`
- **Top Reranker Score:** `0.9987`
- **Threshold:** `0.3`
- **Abstained:** `False`

### 1. Dense Vector Search Candidates (Top-10 Before RRF)

| Rank | Chunk ID | Cosine Score | Document | Section | Access Level |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_api_test_policy_chk_001` | `0.6072` | `api_test_policy.md` | `API Test Policy` | `PUBLIC_USER` |
| 2 | `doc_fastapi_security_chk_002` | `0.3685` | `FastAPI Security & OAuth2 Bearer Authentication` | `2. OAuth2 with Password & Bearer Token` | `public` |
| 3 | `doc_fastapi_security_chk_003` | `0.3215` | `FastAPI Security & OAuth2 Bearer Authentication` | `3. Error Codes & Handling` | `public` |
| 4 | `doc_fastapi_security_chk_001` | `0.2641` | `FastAPI Security & OAuth2 Bearer Authentication` | `1. Overview of Security Tools` | `public` |
| 5 | `doc_fastapi_core_chk_001` | `0.2418` | `FastAPI Core & Dependency Injection Guide` | `1. Introduction to FastAPI` | `public` |
| 6 | `doc_nexacloud_sec_v2_chk_005` | `0.2339` | `NexaCloud Information Security Policy v2.0` | `2.2 Multi-Factor Authentication (MFA) Mandate` | `internal` |
| 7 | `doc_nexacloud_sec_v2_chk_003` | `0.2051` | `NexaCloud Information Security Policy v2.0` | `2. Updated User Authentication Requirements` | `internal` |
| 8 | `doc_nexacloud_sec_v2_chk_004` | `0.2048` | `NexaCloud Information Security Policy v2.0` | `2.1 Password Complexity Rules` | `internal` |
| 9 | `doc_nexacloud_sec_v2_chk_001` | `0.202` | `NexaCloud Information Security Policy v2.0` | `NexaCloud Information Security Policy v2.0` | `internal` |
| 10 | `doc_fastapi_core_chk_003` | `0.1973` | `FastAPI Core & Dependency Injection Guide` | `3. Dependency Injection System` | `public` |

### 2. BM25 Sparse Search Candidates (Top-10 Before RRF)

| Rank | Chunk ID | BM25 Score | Document | Section | Access Level |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_fastapi_security_chk_001` | `6.1151` | `FastAPI Security & OAuth2 Bearer Authentication` | `1. Overview of Security Tools` | `public` |
| 2 | `doc_fastapi_security_chk_002` | `5.164` | `FastAPI Security & OAuth2 Bearer Authentication` | `2. OAuth2 with Password & Bearer Token` | `public` |
| 3 | `doc_api_test_policy_chk_001` | `4.5441` | `api_test_policy.md` | `API Test Policy` | `PUBLIC_USER` |
| 4 | `doc_nexacloud_sec_v2_chk_004` | `4.0325` | `NexaCloud Information Security Policy v2.0` | `2.1 Password Complexity Rules` | `internal` |
| 5 | `doc_fastapi_security_chk_003` | `2.8582` | `FastAPI Security & OAuth2 Bearer Authentication` | `3. Error Codes & Handling` | `public` |
| 6 | `doc_nexacloud_sec_v2_chk_003` | `2.1462` | `NexaCloud Information Security Policy v2.0` | `2. Updated User Authentication Requirements` | `internal` |
| 7 | `doc_nexacloud_sec_v2_chk_002` | `2.1249` | `NexaCloud Information Security Policy v2.0` | `1. Purpose & Scope` | `internal` |
| 8 | `doc_nexacloud_sec_v2_chk_005` | `1.6136` | `NexaCloud Information Security Policy v2.0` | `2.2 Multi-Factor Authentication (MFA) Mandate` | `internal` |
| 9 | `doc_nexacloud_ir_retention_v1_chk_003` | `1.333` | `NexaCloud Incident Response & Data Retention Policy` | `3. Data Retention Schedule` | `internal` |

### 3. Reciprocal Rank Fusion (RRF) Candidates

| Fused Rank | Chunk ID | Dense Rank | BM25 Rank | RRF Score | Calculation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_api_test_policy_chk_001` | `1` | `3` | `0.016133` | `DenseRank(1): 0.008197 + BM25Rank(3): 0.007937 = 0.016133` |
| 2 | `doc_fastapi_security_chk_002` | `2` | `2` | `0.016129` | `DenseRank(2): 0.008065 + BM25Rank(2): 0.008065 = 0.016129` |
| 3 | `doc_fastapi_security_chk_001` | `4` | `1` | `0.016009` | `DenseRank(4): 0.007812 + BM25Rank(1): 0.008197 = 0.016009` |
| 4 | `doc_fastapi_security_chk_003` | `3` | `5` | `0.015629` | `DenseRank(3): 0.007937 + BM25Rank(5): 0.007692 = 0.015629` |
| 5 | `doc_nexacloud_sec_v2_chk_004` | `8` | `4` | `0.015165` | `DenseRank(8): 0.007353 + BM25Rank(4): 0.007812 = 0.015165` |

### 4. Cross-Encoder Reranking & Sigmoid Logits

| Candidate | Chunk ID | Document | Raw Logit | Sigmoid Prob | Text Length | Preview |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_api_test_policy_chk_001` | `api_test_policy.md` | `6.6267` | `0.9987` | 126 chars | `[Document: api_test_policy.md | Lineage: API Test Policy]  API tokens for public integrations must b...` |
| 2 | `doc_fastapi_security_chk_002` | `FastAPI Security & OAuth2 Bearer Authentication` | `-9.3823` | `0.0001` | 1108 chars | `[Document: FastAPI Security & OAuth2 Bearer Authentication | Lineage: FastAPI Security & OAuth2 Bear...` |
| 3 | `doc_fastapi_security_chk_001` | `FastAPI Security & OAuth2 Bearer Authentication` | `-6.02` | `0.0024` | 301 chars | `[Document: FastAPI Security & OAuth2 Bearer Authentication | Lineage: FastAPI Security & OAuth2 Bear...` |
| 4 | `doc_fastapi_security_chk_003` | `FastAPI Security & OAuth2 Bearer Authentication` | `-10.382` | `0.0` | 423 chars | `[Document: FastAPI Security & OAuth2 Bearer Authentication | Lineage: FastAPI Security & OAuth2 Bear...` |
| 5 | `doc_nexacloud_sec_v2_chk_004` | `NexaCloud Information Security Policy v2.0` | `-8.1894` | `0.0003` | 486 chars | `[Document: NexaCloud Information Security Policy v2.0 | Lineage: NexaCloud Information Security Poli...` |

---

## Query: `what is the RTO policy`

- **Intent:** `knowledge`
- **Final Search Query:** `RTO policy`
- **Contextualized:** `False`
- **Retrieval Executed:** `True`
- **Top Reranker Score:** `0.996`
- **Threshold:** `0.3`
- **Abstained:** `False`

### 1. Dense Vector Search Candidates (Top-10 Before RRF)

| Rank | Chunk ID | Cosine Score | Document | Section | Access Level |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_nexacloud_backup_v1_chk_002` | `0.338` | `NexaCloud Data Backup & Recovery Policy` | `2. Recovery Objectives (RPO & RTO)` | `internal` |
| 2 | `doc_nist_sp800_53_chk_002` | `0.2712` | `NIST SP 800-53 Rev. 5 Access Control (AC) Excerpts` | `2. AC-3: Access Enforcement` | `public` |
| 3 | `doc_README_chk_002` | `0.2637` | `README.md` | `Corpus Structure` | `public` |
| 4 | `doc_owasp_top10_chk_001` | `0.2625` | `OWASP Top 10 Web Application Security Risks` | `1. A01:2021 — Broken Access Control` | `public` |
| 5 | `doc_nexacloud_sec_v2_chk_001` | `0.2489` | `NexaCloud Information Security Policy v2.0` | `NexaCloud Information Security Policy v2.0` | `internal` |
| 6 | `doc_nist_sp800_53_chk_003` | `0.2452` | `NIST SP 800-53 Rev. 5 Access Control (AC) Excerpts` | `Implementation Control AC-3(1) — Restricted Access to Data:` | `public` |
| 7 | `doc_nist_sp800_53_chk_001` | `0.2418` | `NIST SP 800-53 Rev. 5 Access Control (AC) Excerpts` | `1. AC-2: Account Management` | `public` |
| 8 | `doc_nexacloud_backup_v1_chk_001` | `0.2319` | `NexaCloud Data Backup & Recovery Policy` | `1. Overview` | `internal` |
| 9 | `doc_nexacloud_sec_v2_chk_005` | `0.2257` | `NexaCloud Information Security Policy v2.0` | `2.2 Multi-Factor Authentication (MFA) Mandate` | `internal` |
| 10 | `doc_api_test_policy_chk_001` | `0.2232` | `api_test_policy.md` | `API Test Policy` | `PUBLIC_USER` |

### 2. BM25 Sparse Search Candidates (Top-10 Before RRF)

| Rank | Chunk ID | BM25 Score | Document | Section | Access Level |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_nexacloud_backup_v1_chk_002` | `5.6701` | `NexaCloud Data Backup & Recovery Policy` | `2. Recovery Objectives (RPO & RTO)` | `internal` |
| 2 | `doc_nexacloud_sec_v2_chk_001` | `0.2092` | `NexaCloud Information Security Policy v2.0` | `NexaCloud Information Security Policy v2.0` | `internal` |
| 3 | `doc_nexacloud_sec_v2_chk_002` | `0.1907` | `NexaCloud Information Security Policy v2.0` | `1. Purpose & Scope` | `internal` |
| 4 | `doc_nexacloud_backup_v1_chk_001` | `0.1897` | `NexaCloud Data Backup & Recovery Policy` | `1. Overview` | `internal` |
| 5 | `doc_README_chk_002` | `0.1872` | `README.md` | `Corpus Structure` | `public` |
| 6 | `doc_README_chk_003` | `0.1702` | `README.md` | `Document Manifest & Licensing Table` | `public` |
| 7 | `doc_nexacloud_sec_v2_chk_003` | `0.1696` | `NexaCloud Information Security Policy v2.0` | `2. Updated User Authentication Requirements` | `internal` |
| 8 | `doc_nexacloud_sec_v2_chk_006` | `0.1609` | `NexaCloud Information Security Policy v2.0` | `3. Production System Access` | `internal` |
| 9 | `doc_nexacloud_ir_retention_v1_chk_002` | `0.1522` | `NexaCloud Incident Response & Data Retention Policy` | `2. Mandatory Reporting Procedures` | `internal` |
| 10 | `doc_api_test_policy_chk_001` | `0.1502` | `api_test_policy.md` | `API Test Policy` | `PUBLIC_USER` |

### 3. Reciprocal Rank Fusion (RRF) Candidates

| Fused Rank | Chunk ID | Dense Rank | BM25 Rank | RRF Score | Calculation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_nexacloud_backup_v1_chk_002` | `1` | `1` | `0.016393` | `DenseRank(1): 0.008197 + BM25Rank(1): 0.008197 = 0.016393` |
| 2 | `doc_nexacloud_sec_v2_chk_001` | `5` | `2` | `0.015757` | `DenseRank(5): 0.007692 + BM25Rank(2): 0.008065 = 0.015757` |
| 3 | `doc_README_chk_002` | `3` | `5` | `0.015629` | `DenseRank(3): 0.007937 + BM25Rank(5): 0.007692 = 0.015629` |
| 4 | `doc_nexacloud_backup_v1_chk_001` | `8` | `4` | `0.015165` | `DenseRank(8): 0.007353 + BM25Rank(4): 0.007812 = 0.015165` |
| 5 | `doc_api_test_policy_chk_001` | `10` | `10` | `0.014286` | `DenseRank(10): 0.007143 + BM25Rank(10): 0.007143 = 0.014286` |

### 4. Cross-Encoder Reranking & Sigmoid Logits

| Candidate | Chunk ID | Document | Raw Logit | Sigmoid Prob | Text Length | Preview |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_nexacloud_backup_v1_chk_002` | `NexaCloud Data Backup & Recovery Policy` | `5.5107` | `0.996` | 562 chars | `[Document: NexaCloud Data Backup & Recovery Policy | Lineage: NexaCloud Data Backup & Recovery Polic...` |
| 2 | `doc_nexacloud_sec_v2_chk_001` | `NexaCloud Information Security Policy v2.0` | `-7.4139` | `0.0006` | 250 chars | `[Document: NexaCloud Information Security Policy v2.0 | Lineage: NexaCloud Information Security Poli...` |
| 3 | `doc_README_chk_002` | `README.md` | `-8.7175` | `0.0002` | 948 chars | `[Document: README.md | Lineage: DATASET CORPUS DOCUMENTATION & ATTRIBUTION > Corpus Structure]  ``` ...` |
| 4 | `doc_nexacloud_backup_v1_chk_001` | `NexaCloud Data Backup & Recovery Policy` | `-7.0123` | `0.0009` | 271 chars | `[Document: NexaCloud Data Backup & Recovery Policy | Lineage: NexaCloud Data Backup & Recovery Polic...` |
| 5 | `doc_api_test_policy_chk_001` | `api_test_policy.md` | `-8.6464` | `0.0002` | 126 chars | `[Document: api_test_policy.md | Lineage: API Test Policy]  API tokens for public integrations must b...` |

---

## Query: `what is RPO`

- **Intent:** `knowledge`
- **Final Search Query:** `What is RPO`
- **Contextualized:** `False`
- **Retrieval Executed:** `True`
- **Top Reranker Score:** `0.9445`
- **Threshold:** `0.3`
- **Abstained:** `False`

### 1. Dense Vector Search Candidates (Top-10 Before RRF)

| Rank | Chunk ID | Cosine Score | Document | Section | Access Level |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_nexacloud_backup_v1_chk_002` | `0.2889` | `NexaCloud Data Backup & Recovery Policy` | `2. Recovery Objectives (RPO & RTO)` | `internal` |
| 2 | `doc_README_chk_004` | `0.1693` | `README.md` | `Attribution & Legal Notice` | `public` |
| 3 | `doc_nist_sp800_53_chk_001` | `0.1342` | `NIST SP 800-53 Rev. 5 Access Control (AC) Excerpts` | `1. AC-2: Account Management` | `public` |
| 4 | `doc_nist_sp800_53_chk_003` | `0.1258` | `NIST SP 800-53 Rev. 5 Access Control (AC) Excerpts` | `Implementation Control AC-3(1) — Restricted Access to Data:` | `public` |
| 5 | `doc_nist_sp800_53_chk_002` | `0.1055` | `NIST SP 800-53 Rev. 5 Access Control (AC) Excerpts` | `2. AC-3: Access Enforcement` | `public` |
| 6 | `doc_nexacloud_backup_v1_chk_003` | `0.1026` | `NexaCloud Data Backup & Recovery Policy` | `3. Backup Schedule & Architecture` | `internal` |
| 7 | `doc_README_chk_002` | `0.0921` | `README.md` | `Corpus Structure` | `public` |
| 8 | `doc_nexacloud_ir_retention_v1_chk_002` | `0.09` | `NexaCloud Incident Response & Data Retention Policy` | `2. Mandatory Reporting Procedures` | `internal` |
| 9 | `doc_nexacloud_ir_retention_v1_chk_001` | `0.0899` | `NexaCloud Incident Response & Data Retention Policy` | `1. Incident Severity Classification & SLAs` | `internal` |
| 10 | `doc_nexacloud_backup_v1_chk_001` | `0.0873` | `NexaCloud Data Backup & Recovery Policy` | `1. Overview` | `internal` |

### 2. BM25 Sparse Search Candidates (Top-10 Before RRF)

| Rank | Chunk ID | BM25 Score | Document | Section | Access Level |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_nexacloud_backup_v1_chk_002` | `7.1881` | `NexaCloud Data Backup & Recovery Policy` | `2. Recovery Objectives (RPO & RTO)` | `internal` |
| 2 | `doc_docker_compose_chk_001` | `1.6393` | `Docker Compose Specification & Multi-Container Guide` | `1. Overview` | `public` |
| 3 | `doc_docker_basics_chk_002` | `1.5582` | `Docker Basics & Dockerfile Reference` | `2. Dockerfile Syntax & Directives` | `public` |
| 4 | `doc_nexacloud_prompt_inj_v1_chk_003` | `1.5429` | `NexaCloud Employee Onboarding & Security Guidance` | `3. Workplace Communication Rules` | `internal` |
| 5 | `doc_owasp_top10_chk_004` | `1.3927` | `OWASP Top 10 Web Application Security Risks` | `2. A03:2021 — Injection` | `public` |
| 6 | `doc_docker_engine_chk_001` | `1.3451` | `docker_engine.md` | `1. Dockerfile Instructions Reference` | `public` |
| 7 | `doc_nexacloud_sec_v2_chk_004` | `1.2295` | `NexaCloud Information Security Policy v2.0` | `2.1 Password Complexity Rules` | `internal` |
| 8 | `doc_fastapi_core_chk_001` | `1.2295` | `FastAPI Core & Dependency Injection Guide` | `1. Introduction to FastAPI` | `public` |
| 9 | `doc_nexacloud_sec_v2_chk_005` | `1.1832` | `NexaCloud Information Security Policy v2.0` | `2.2 Multi-Factor Authentication (MFA) Mandate` | `internal` |
| 10 | `doc_nexacloud_backup_v1_chk_003` | `1.1322` | `NexaCloud Data Backup & Recovery Policy` | `3. Backup Schedule & Architecture` | `internal` |

### 3. Reciprocal Rank Fusion (RRF) Candidates

| Fused Rank | Chunk ID | Dense Rank | BM25 Rank | RRF Score | Calculation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_nexacloud_backup_v1_chk_002` | `1` | `1` | `0.016393` | `DenseRank(1): 0.008197 + BM25Rank(1): 0.008197 = 0.016393` |
| 2 | `doc_nexacloud_backup_v1_chk_003` | `6` | `10` | `0.014719` | `DenseRank(6): 0.007576 + BM25Rank(10): 0.007143 = 0.014719` |
| 3 | `doc_README_chk_004` | `2` | `None` | `0.008065` | `DenseRank(2): 0.008065 + BM25Rank(None): 0.000000 = 0.008065` |
| 4 | `doc_docker_compose_chk_001` | `None` | `2` | `0.008065` | `DenseRank(None): 0.000000 + BM25Rank(2): 0.008065 = 0.008065` |
| 5 | `doc_nist_sp800_53_chk_001` | `3` | `None` | `0.007937` | `DenseRank(3): 0.007937 + BM25Rank(None): 0.000000 = 0.007937` |

### 4. Cross-Encoder Reranking & Sigmoid Logits

| Candidate | Chunk ID | Document | Raw Logit | Sigmoid Prob | Text Length | Preview |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_nexacloud_backup_v1_chk_002` | `NexaCloud Data Backup & Recovery Policy` | `2.8349` | `0.9445` | 562 chars | `[Document: NexaCloud Data Backup & Recovery Policy | Lineage: NexaCloud Data Backup & Recovery Polic...` |
| 2 | `doc_nexacloud_backup_v1_chk_003` | `NexaCloud Data Backup & Recovery Policy` | `-11.0817` | `0.0` | 591 chars | `[Document: NexaCloud Data Backup & Recovery Policy | Lineage: NexaCloud Data Backup & Recovery Polic...` |
| 3 | `doc_README_chk_004` | `README.md` | `-10.5741` | `0.0` | 707 chars | `[Document: README.md | Lineage: DATASET CORPUS DOCUMENTATION & ATTRIBUTION > Attribution & Legal Not...` |
| 4 | `doc_docker_compose_chk_001` | `Docker Compose Specification & Multi-Container Guide` | `-10.5719` | `0.0` | 238 chars | `[Document: Docker Compose Specification & Multi-Container Guide | Lineage: Docker Compose Specificat...` |
| 5 | `doc_nist_sp800_53_chk_001` | `NIST SP 800-53 Rev. 5 Access Control (AC) Excerpts` | `-10.4464` | `0.0` | 345 chars | `[Document: NIST SP 800-53 Rev. 5 Access Control (AC) Excerpts | Lineage: NIST SP 800-53 Rev. 5: Acce...` |

---

## Query: `password policy`

- **Intent:** `knowledge`
- **Final Search Query:** `password policy`
- **Contextualized:** `False`
- **Retrieval Executed:** `True`
- **Top Reranker Score:** `0.9887`
- **Threshold:** `0.3`
- **Abstained:** `False`

### 1. Dense Vector Search Candidates (Top-10 Before RRF)

| Rank | Chunk ID | Cosine Score | Document | Section | Access Level |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_nexacloud_sec_v2_chk_004` | `0.4841` | `NexaCloud Information Security Policy v2.0` | `2.1 Password Complexity Rules` | `internal` |
| 2 | `doc_nexacloud_sec_v2_chk_005` | `0.3864` | `NexaCloud Information Security Policy v2.0` | `2.2 Multi-Factor Authentication (MFA) Mandate` | `internal` |
| 3 | `doc_owasp_top10_chk_001` | `0.3858` | `OWASP Top 10 Web Application Security Risks` | `1. A01:2021 — Broken Access Control` | `public` |
| 4 | `doc_nist_sp800_53_chk_001` | `0.3641` | `NIST SP 800-53 Rev. 5 Access Control (AC) Excerpts` | `1. AC-2: Account Management` | `public` |
| 5 | `doc_nist_sp800_53_chk_002` | `0.3554` | `NIST SP 800-53 Rev. 5 Access Control (AC) Excerpts` | `2. AC-3: Access Enforcement` | `public` |
| 6 | `doc_nexacloud_sec_v2_chk_006` | `0.348` | `NexaCloud Information Security Policy v2.0` | `3. Production System Access` | `internal` |
| 7 | `doc_owasp_top10_chk_002` | `0.331` | `OWASP Top 10 Web Application Security Risks` | `Common Vulnerabilities:` | `public` |
| 8 | `doc_nexacloud_sec_v2_chk_003` | `0.3201` | `NexaCloud Information Security Policy v2.0` | `2. Updated User Authentication Requirements` | `internal` |
| 9 | `doc_nexacloud_sec_v2_chk_002` | `0.3099` | `NexaCloud Information Security Policy v2.0` | `1. Purpose & Scope` | `internal` |
| 10 | `doc_nexacloud_prompt_inj_v1_chk_003` | `0.3001` | `NexaCloud Employee Onboarding & Security Guidance` | `3. Workplace Communication Rules` | `internal` |

### 2. BM25 Sparse Search Candidates (Top-10 Before RRF)

| Rank | Chunk ID | BM25 Score | Document | Section | Access Level |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_fastapi_security_chk_002` | `3.4013` | `FastAPI Security & OAuth2 Bearer Authentication` | `2. OAuth2 with Password & Bearer Token` | `public` |
| 2 | `doc_nexacloud_sec_v2_chk_004` | `3.2527` | `NexaCloud Information Security Policy v2.0` | `2.1 Password Complexity Rules` | `internal` |
| 3 | `doc_nexacloud_sec_v2_chk_006` | `2.7055` | `NexaCloud Information Security Policy v2.0` | `3. Production System Access` | `internal` |
| 4 | `doc_nexacloud_sec_v2_chk_001` | `0.2092` | `NexaCloud Information Security Policy v2.0` | `NexaCloud Information Security Policy v2.0` | `internal` |
| 5 | `doc_nexacloud_sec_v2_chk_002` | `0.1907` | `NexaCloud Information Security Policy v2.0` | `1. Purpose & Scope` | `internal` |
| 6 | `doc_nexacloud_backup_v1_chk_001` | `0.1897` | `NexaCloud Data Backup & Recovery Policy` | `1. Overview` | `internal` |
| 7 | `doc_README_chk_002` | `0.1872` | `README.md` | `Corpus Structure` | `public` |
| 8 | `doc_README_chk_003` | `0.1702` | `README.md` | `Document Manifest & Licensing Table` | `public` |
| 9 | `doc_nexacloud_sec_v2_chk_003` | `0.1696` | `NexaCloud Information Security Policy v2.0` | `2. Updated User Authentication Requirements` | `internal` |
| 10 | `doc_nexacloud_ir_retention_v1_chk_002` | `0.1522` | `NexaCloud Incident Response & Data Retention Policy` | `2. Mandatory Reporting Procedures` | `internal` |

### 3. Reciprocal Rank Fusion (RRF) Candidates

| Fused Rank | Chunk ID | Dense Rank | BM25 Rank | RRF Score | Calculation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_nexacloud_sec_v2_chk_004` | `1` | `2` | `0.016261` | `DenseRank(1): 0.008197 + BM25Rank(2): 0.008065 = 0.016261` |
| 2 | `doc_nexacloud_sec_v2_chk_006` | `6` | `3` | `0.015512` | `DenseRank(6): 0.007576 + BM25Rank(3): 0.007937 = 0.015512` |
| 3 | `doc_nexacloud_sec_v2_chk_002` | `9` | `5` | `0.014939` | `DenseRank(9): 0.007246 + BM25Rank(5): 0.007692 = 0.014939` |
| 4 | `doc_nexacloud_sec_v2_chk_003` | `8` | `9` | `0.014599` | `DenseRank(8): 0.007353 + BM25Rank(9): 0.007246 = 0.014599` |
| 5 | `doc_fastapi_security_chk_002` | `None` | `1` | `0.008197` | `DenseRank(None): 0.000000 + BM25Rank(1): 0.008197 = 0.008197` |

### 4. Cross-Encoder Reranking & Sigmoid Logits

| Candidate | Chunk ID | Document | Raw Logit | Sigmoid Prob | Text Length | Preview |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_nexacloud_sec_v2_chk_004` | `NexaCloud Information Security Policy v2.0` | `4.4706` | `0.9887` | 486 chars | `[Document: NexaCloud Information Security Policy v2.0 | Lineage: NexaCloud Information Security Poli...` |
| 2 | `doc_nexacloud_sec_v2_chk_006` | `NexaCloud Information Security Policy v2.0` | `1.3602` | `0.7958` | 345 chars | `[Document: NexaCloud Information Security Policy v2.0 | Lineage: NexaCloud Information Security Poli...` |
| 3 | `doc_nexacloud_sec_v2_chk_002` | `NexaCloud Information Security Policy v2.0` | `-4.2935` | `0.0135` | 290 chars | `[Document: NexaCloud Information Security Policy v2.0 | Lineage: NexaCloud Information Security Poli...` |
| 4 | `doc_nexacloud_sec_v2_chk_003` | `NexaCloud Information Security Policy v2.0` | `-3.729` | `0.0235` | 279 chars | `[Document: NexaCloud Information Security Policy v2.0 | Lineage: NexaCloud Information Security Poli...` |
| 5 | `doc_fastapi_security_chk_002` | `FastAPI Security & OAuth2 Bearer Authentication` | `-6.0137` | `0.0024` | 1108 chars | `[Document: FastAPI Security & OAuth2 Bearer Authentication | Lineage: FastAPI Security & OAuth2 Bear...` |

---

## Query: `how is cross-region S3 replication configured`

- **Intent:** `knowledge`
- **Final Search Query:** `cross-region S3 replication configuration`
- **Contextualized:** `False`
- **Retrieval Executed:** `True`
- **Top Reranker Score:** `0.9739`
- **Threshold:** `0.3`
- **Abstained:** `False`

### 1. Dense Vector Search Candidates (Top-10 Before RRF)

| Rank | Chunk ID | Cosine Score | Document | Section | Access Level |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_nexacloud_backup_v1_chk_003` | `0.4633` | `NexaCloud Data Backup & Recovery Policy` | `3. Backup Schedule & Architecture` | `internal` |
| 2 | `doc_nexacloud_backup_v1_chk_002` | `0.3335` | `NexaCloud Data Backup & Recovery Policy` | `2. Recovery Objectives (RPO & RTO)` | `internal` |
| 3 | `doc_nexacloud_ir_retention_v1_chk_003` | `0.2676` | `NexaCloud Incident Response & Data Retention Policy` | `3. Data Retention Schedule` | `internal` |
| 4 | `doc_nexacloud_backup_v1_chk_001` | `0.2044` | `NexaCloud Data Backup & Recovery Policy` | `1. Overview` | `internal` |
| 5 | `doc_docker_engine_chk_003` | `0.1898` | `docker_engine.md` | `2. Docker Compose Syntax and Multi-Container Orchestration` | `public` |
| 6 | `doc_fastapi_core_chk_004` | `0.1843` | `FastAPI Core & Dependency Injection Guide` | `3.1 Benefits of `Depends`` | `public` |
| 7 | `doc_nexacloud_ir_retention_v1_chk_001` | `0.1629` | `NexaCloud Incident Response & Data Retention Policy` | `1. Incident Severity Classification & SLAs` | `internal` |
| 8 | `doc_nexacloud_ir_retention_v1_chk_002` | `0.1628` | `NexaCloud Incident Response & Data Retention Policy` | `2. Mandatory Reporting Procedures` | `internal` |
| 9 | `doc_docker_compose_chk_003` | `0.1619` | `Docker Compose Specification & Multi-Container Guide` | `3. Environment Variables & Secret Ingestion` | `public` |
| 10 | `doc_owasp_top10_chk_005` | `0.1561` | `OWASP Top 10 Web Application Security Risks` | `Mitigation in LLM / RAG Systems:` | `public` |

### 2. BM25 Sparse Search Candidates (Top-10 Before RRF)

| Rank | Chunk ID | BM25 Score | Document | Section | Access Level |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_nexacloud_backup_v1_chk_003` | `10.2948` | `NexaCloud Data Backup & Recovery Policy` | `3. Backup Schedule & Architecture` | `internal` |
| 2 | `doc_docker_compose_chk_001` | `3.9336` | `Docker Compose Specification & Multi-Container Guide` | `1. Overview` | `public` |
| 3 | `doc_docker_engine_chk_003` | `2.9047` | `docker_engine.md` | `2. Docker Compose Syntax and Multi-Container Orchestration` | `public` |
| 4 | `doc_nexacloud_backup_v1_chk_002` | `2.355` | `NexaCloud Data Backup & Recovery Policy` | `2. Recovery Objectives (RPO & RTO)` | `internal` |
| 5 | `doc_nexacloud_ir_retention_v1_chk_003` | `2.077` | `NexaCloud Incident Response & Data Retention Policy` | `3. Data Retention Schedule` | `internal` |

### 3. Reciprocal Rank Fusion (RRF) Candidates

| Fused Rank | Chunk ID | Dense Rank | BM25 Rank | RRF Score | Calculation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_nexacloud_backup_v1_chk_003` | `1` | `1` | `0.016393` | `DenseRank(1): 0.008197 + BM25Rank(1): 0.008197 = 0.016393` |
| 2 | `doc_nexacloud_backup_v1_chk_002` | `2` | `4` | `0.015877` | `DenseRank(2): 0.008065 + BM25Rank(4): 0.007812 = 0.015877` |
| 3 | `doc_nexacloud_ir_retention_v1_chk_003` | `3` | `5` | `0.015629` | `DenseRank(3): 0.007937 + BM25Rank(5): 0.007692 = 0.015629` |
| 4 | `doc_docker_engine_chk_003` | `5` | `3` | `0.015629` | `DenseRank(5): 0.007692 + BM25Rank(3): 0.007937 = 0.015629` |
| 5 | `doc_docker_compose_chk_001` | `None` | `2` | `0.008065` | `DenseRank(None): 0.000000 + BM25Rank(2): 0.008065 = 0.008065` |

### 4. Cross-Encoder Reranking & Sigmoid Logits

| Candidate | Chunk ID | Document | Raw Logit | Sigmoid Prob | Text Length | Preview |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_nexacloud_backup_v1_chk_003` | `NexaCloud Data Backup & Recovery Policy` | `3.6212` | `0.9739` | 591 chars | `[Document: NexaCloud Data Backup & Recovery Policy | Lineage: NexaCloud Data Backup & Recovery Polic...` |
| 2 | `doc_nexacloud_backup_v1_chk_002` | `NexaCloud Data Backup & Recovery Policy` | `-4.861` | `0.0077` | 562 chars | `[Document: NexaCloud Data Backup & Recovery Policy | Lineage: NexaCloud Data Backup & Recovery Polic...` |
| 3 | `doc_nexacloud_ir_retention_v1_chk_003` | `NexaCloud Incident Response & Data Retention Policy` | `-10.8362` | `0.0` | 694 chars | `[Document: NexaCloud Incident Response & Data Retention Policy | Lineage: NexaCloud Incident Respons...` |
| 4 | `doc_docker_engine_chk_003` | `docker_engine.md` | `-11.2955` | `0.0` | 659 chars | `[Document: docker_engine.md | Lineage: Docker Engine & Compose Architecture Guide > 2. Docker Compos...` |
| 5 | `doc_docker_compose_chk_001` | `Docker Compose Specification & Multi-Container Guide` | `-11.3719` | `0.0` | 238 chars | `[Document: Docker Compose Specification & Multi-Container Guide | Lineage: Docker Compose Specificat...` |

---

## Query: `hello`

- **Intent:** `conversational`
- **Final Search Query:** `hello`
- **Contextualized:** `False`
- **Retrieval Executed:** `False`
- **Top Reranker Score:** `0.0`
- **Threshold:** `0.3`
- **Abstained:** `False`

> **Note:** Query bypassed RAG retrieval (Conversational / Out-of-Scope).

---

## Query: `who are you`

- **Intent:** `conversational`
- **Final Search Query:** `who are you`
- **Contextualized:** `False`
- **Retrieval Executed:** `False`
- **Top Reranker Score:** `0.0`
- **Threshold:** `0.3`
- **Abstained:** `False`

> **Note:** Query bypassed RAG retrieval (Conversational / Out-of-Scope).

---

## Query: `What about production?`

- **Intent:** `hybrid`
- **Final Search Query:** `NexaCloud production RTO policy`
- **Contextualized:** `True`
- **Retrieval Executed:** `True`
- **Top Reranker Score:** `0.9994`
- **Threshold:** `0.3`
- **Abstained:** `False`

### 1. Dense Vector Search Candidates (Top-10 Before RRF)

| Rank | Chunk ID | Cosine Score | Document | Section | Access Level |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_nexacloud_backup_v1_chk_002` | `0.6139` | `NexaCloud Data Backup & Recovery Policy` | `2. Recovery Objectives (RPO & RTO)` | `internal` |
| 2 | `doc_nexacloud_sec_v2_chk_001` | `0.5932` | `NexaCloud Information Security Policy v2.0` | `NexaCloud Information Security Policy v2.0` | `internal` |
| 3 | `doc_nexacloud_sec_v2_chk_002` | `0.5491` | `NexaCloud Information Security Policy v2.0` | `1. Purpose & Scope` | `internal` |
| 4 | `doc_nexacloud_sec_v2_chk_006` | `0.542` | `NexaCloud Information Security Policy v2.0` | `3. Production System Access` | `internal` |
| 5 | `doc_nexacloud_backup_v1_chk_001` | `0.5296` | `NexaCloud Data Backup & Recovery Policy` | `1. Overview` | `internal` |
| 6 | `doc_README_chk_004` | `0.5168` | `README.md` | `Attribution & Legal Notice` | `public` |
| 7 | `doc_nexacloud_prompt_inj_v1_chk_002` | `0.495` | `NexaCloud Employee Onboarding & Security Guidance` | `2. Equipment Provisioning` | `internal` |
| 8 | `doc_nexacloud_sec_v2_chk_003` | `0.4918` | `NexaCloud Information Security Policy v2.0` | `2. Updated User Authentication Requirements` | `internal` |
| 9 | `doc_nexacloud_sec_v2_chk_005` | `0.4906` | `NexaCloud Information Security Policy v2.0` | `2.2 Multi-Factor Authentication (MFA) Mandate` | `internal` |
| 10 | `doc_nexacloud_prompt_inj_v1_chk_003` | `0.4815` | `NexaCloud Employee Onboarding & Security Guidance` | `3. Workplace Communication Rules` | `internal` |

### 2. BM25 Sparse Search Candidates (Top-10 Before RRF)

| Rank | Chunk ID | BM25 Score | Document | Section | Access Level |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_nexacloud_backup_v1_chk_002` | `7.1228` | `NexaCloud Data Backup & Recovery Policy` | `2. Recovery Objectives (RPO & RTO)` | `internal` |
| 2 | `doc_nexacloud_sec_v2_chk_006` | `3.0066` | `NexaCloud Information Security Policy v2.0` | `3. Production System Access` | `internal` |
| 3 | `doc_nexacloud_backup_v1_chk_001` | `2.1819` | `NexaCloud Data Backup & Recovery Policy` | `1. Overview` | `internal` |
| 4 | `doc_nexacloud_ir_retention_v1_chk_001` | `1.4869` | `NexaCloud Incident Response & Data Retention Policy` | `1. Incident Severity Classification & SLAs` | `internal` |
| 5 | `doc_README_chk_002` | `1.4819` | `README.md` | `Corpus Structure` | `public` |
| 6 | `doc_README_chk_003` | `1.277` | `README.md` | `Document Manifest & Licensing Table` | `public` |
| 7 | `doc_nexacloud_sec_v2_chk_001` | `0.4058` | `NexaCloud Information Security Policy v2.0` | `NexaCloud Information Security Policy v2.0` | `internal` |
| 8 | `doc_nexacloud_sec_v2_chk_002` | `0.3813` | `NexaCloud Information Security Policy v2.0` | `1. Purpose & Scope` | `internal` |
| 9 | `doc_nexacloud_sec_v2_chk_003` | `0.3612` | `NexaCloud Information Security Policy v2.0` | `2. Updated User Authentication Requirements` | `internal` |
| 10 | `doc_nexacloud_ir_retention_v1_chk_002` | `0.3044` | `NexaCloud Incident Response & Data Retention Policy` | `2. Mandatory Reporting Procedures` | `internal` |

### 3. Reciprocal Rank Fusion (RRF) Candidates

| Fused Rank | Chunk ID | Dense Rank | BM25 Rank | RRF Score | Calculation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_nexacloud_backup_v1_chk_002` | `1` | `1` | `0.016393` | `DenseRank(1): 0.008197 + BM25Rank(1): 0.008197 = 0.016393` |
| 2 | `doc_nexacloud_sec_v2_chk_006` | `4` | `2` | `0.015877` | `DenseRank(4): 0.007812 + BM25Rank(2): 0.008065 = 0.015877` |
| 3 | `doc_nexacloud_backup_v1_chk_001` | `5` | `3` | `0.015629` | `DenseRank(5): 0.007692 + BM25Rank(3): 0.007937 = 0.015629` |
| 4 | `doc_nexacloud_sec_v2_chk_001` | `2` | `7` | `0.015527` | `DenseRank(2): 0.008065 + BM25Rank(7): 0.007463 = 0.015527` |
| 5 | `doc_nexacloud_sec_v2_chk_002` | `3` | `8` | `0.015289` | `DenseRank(3): 0.007937 + BM25Rank(8): 0.007353 = 0.015289` |

### 4. Cross-Encoder Reranking & Sigmoid Logits

| Candidate | Chunk ID | Document | Raw Logit | Sigmoid Prob | Text Length | Preview |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `doc_nexacloud_backup_v1_chk_002` | `NexaCloud Data Backup & Recovery Policy` | `7.4874` | `0.9994` | 562 chars | `[Document: NexaCloud Data Backup & Recovery Policy | Lineage: NexaCloud Data Backup & Recovery Polic...` |
| 2 | `doc_nexacloud_sec_v2_chk_006` | `NexaCloud Information Security Policy v2.0` | `4.4975` | `0.989` | 345 chars | `[Document: NexaCloud Information Security Policy v2.0 | Lineage: NexaCloud Information Security Poli...` |
| 3 | `doc_nexacloud_backup_v1_chk_001` | `NexaCloud Data Backup & Recovery Policy` | `4.9379` | `0.9929` | 271 chars | `[Document: NexaCloud Data Backup & Recovery Policy | Lineage: NexaCloud Data Backup & Recovery Polic...` |
| 4 | `doc_nexacloud_sec_v2_chk_001` | `NexaCloud Information Security Policy v2.0` | `2.0773` | `0.8887` | 250 chars | `[Document: NexaCloud Information Security Policy v2.0 | Lineage: NexaCloud Information Security Poli...` |
| 5 | `doc_nexacloud_sec_v2_chk_002` | `NexaCloud Information Security Policy v2.0` | `2.75` | `0.9399` | 290 chars | `[Document: NexaCloud Information Security Policy v2.0 | Lineage: NexaCloud Information Security Poli...` |

---

