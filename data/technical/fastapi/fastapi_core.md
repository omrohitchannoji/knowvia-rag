---
document_id: doc_fastapi_core
document_name: FastAPI Core Guide
version: "1.0"
status: active
access_level: public
---

# FastAPI Core

## 1. Overview
FastAPI is a modern, fast (high-performance) web framework for building APIs with Python 3.8+ based on standard Python type hints.

## 2. Quickstart Code Example
The following is an example demonstrating basic route definition:

```python
from fastapi import FastAPI

app = FastAPI(title="FastAPI Core Demo")

@app.get("/")
def read_root():
    return {"status": "success", "message": "FastAPI is running"}
```

## 3. Dependency Injection
FastAPI provides a powerful and intuitive Dependency Injection system using `Depends`.
