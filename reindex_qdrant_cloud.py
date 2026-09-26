import sys
import os
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.services.document_service import get_document_service

def reindex_qdrant_cloud():
    print("\n================================================================================")
    print("STARTING QDRANT CLOUD RE-INDEXING")
    print(f"Target Qdrant URL: {settings.QDRANT_URL}")
    print("================================================================================")
    
    doc_service = get_document_service()
    
    # 1. Recreate Qdrant collection on Cloud cleanly
    print(f"\n[Step 1] Recreating Qdrant Cloud collection: [{settings.COLLECTION_NAME}]...")
    doc_service.vector_store.recreate_collection()
    
    true_data_dir = os.path.abspath("data/TrueData")
    noisy_data_dir = os.path.abspath("data/NoisyData")

    # 2. Ingest TrueData
    print(f"\n[Step 2] Ingesting TrueData from: [{true_data_dir}]...")
    start_time = time.time()
    true_results = doc_service.ingest_directory(true_data_dir, data_category="true")
    true_indexed = [r for r in true_results if r.get("status") == "indexed"]
    true_chunks = sum(r.get("total_chunks", 0) for r in true_indexed)
    print(f"  -> Ingested {len(true_indexed)} TrueData files ({true_chunks} chunks) in {time.time() - start_time:.2f}s")

    # 3. Ingest NoisyData
    print(f"\n[Step 3] Ingesting NoisyData from: [{noisy_data_dir}]...")
    start_time = time.time()
    noisy_results = doc_service.ingest_directory(noisy_data_dir, data_category="noisy")
    noisy_indexed = [r for r in noisy_results if r.get("status") == "indexed"]
    noisy_chunks = sum(r.get("total_chunks", 0) for r in noisy_indexed)
    print(f"  -> Ingested {len(noisy_indexed)} NoisyData files ({noisy_chunks} chunks) in {time.time() - start_time:.2f}s")

    # 4. Synchronize BM25 Index
    print(f"\n[Step 4] Synchronizing BM25 Index from Qdrant Cloud Vector Store...")
    doc_service.sync_bm25_from_vector_store()
    
    total_qdrant_points = doc_service.vector_store.client.count(collection_name=settings.COLLECTION_NAME).count
    bm25_index_size = len(doc_service.bm25_retriever.indexed_chunks) if doc_service.bm25_retriever.indexed_chunks else 0

    print("\n================================================================================")
    print("QDRANT CLOUD RE-INDEXING SUMMARY")
    print("================================================================================")
    print(f"Qdrant Collection Name : {settings.COLLECTION_NAME}")
    print(f"TrueData Files Index   : {len(true_indexed)} files ({true_chunks} chunks)")
    print(f"NoisyData Files Index  : {len(noisy_indexed)} files ({noisy_chunks} chunks)")
    print(f"Total Qdrant Points    : {total_qdrant_points}")
    print(f"Total BM25 Index Chunks: {bm25_index_size}")
    print("================================================================Calculated successfully!\n")

if __name__ == "__main__":
    reindex_qdrant_cloud()
