import sys
import os

os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["PYTHONWARNINGS"] = "ignore"

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.api.routes_health import router as health_router
from backend.app.api.routes_documents import router as documents_router
from backend.app.api.routes_query import router as query_router

from backend.app.services.document_service import get_document_service

import threading

def _bg_auto_ingest(doc_service):
    try:
        import os
        logger.info("Vector store is empty. Auto-ingesting TrueData and NoisyData corpus in background thread...")
        if os.path.exists("data/TrueData"):
            doc_service.ingest_directory("data/TrueData", data_category="true")
        if os.path.exists("data/NoisyData"):
            doc_service.ingest_directory("data/NoisyData", data_category="noisy")
        logger.info(f"Background auto-ingestion complete. Indexed {len(doc_service.all_chunks)} total chunks into Qdrant & BM25.")
    except Exception as e:
        logger.error(f"Error during background auto-ingestion: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] environment")
    # Initialize DocumentService to synchronize BM25 index with Qdrant points on startup
    doc_service = get_document_service()
    doc_service.sync_bm25_from_vector_store()

    # Launch auto-ingestion in background thread if collection is empty
    if not doc_service.all_chunks:
        threading.Thread(target=_bg_auto_ingest, args=(doc_service,), daemon=True).start()

    yield
    logger.info(f"Shutting down {settings.APP_NAME}")


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="Production-Oriented Technical Documentation & Policy Intelligence RAG System",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )

    # CORS Configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include Routes under /api/v1
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(documents_router, prefix="/api/v1")
    app.include_router(query_router, prefix="/api/v1")

    return app


app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
