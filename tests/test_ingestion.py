import os
import pytest
from backend.app.ingestion.loaders import load_markdown_file
from backend.app.ingestion.parser import parse_markdown_structure
from backend.app.ingestion.chunker import create_structure_aware_chunks
from backend.app.ingestion.metadata import build_chunk_metadata

TEST_MD_PATH = "data/synthetic_policies/nexacloud_sec_v2.md"
TEST_TECH_PATH = "data/technical/fastapi/fastapi_core.md"

def test_load_markdown_file_and_frontmatter():
    assert os.path.exists(TEST_MD_PATH)
    content, frontmatter = load_markdown_file(TEST_MD_PATH)
    assert content is not None
    assert len(content) > 0
    assert frontmatter.get("document_id") == "doc_nexacloud_sec_v2"
    assert frontmatter.get("version") == "2.0"
    assert frontmatter.get("status") == "active"

def test_parse_markdown_structure():
    content, frontmatter = load_markdown_file(TEST_TECH_PATH)
    sections = parse_markdown_structure(content, "FastAPI Core")
    assert len(sections) > 0
    
    # Verify code block preservation
    code_block_found = False
    for sec in sections:
        if "```python" in sec.content:
            code_block_found = True
            break
    assert code_block_found, "Fenced Python code block must be preserved inside parsed sections."

def test_structure_aware_chunking_and_context():
    content, frontmatter = load_markdown_file(TEST_TECH_PATH)
    sections = parse_markdown_structure(content, "FastAPI Core Guide")
    chunks = create_structure_aware_chunks(sections, "doc_fastapi_core", "FastAPI Core Guide")
    
    assert len(chunks) > 0
    first_chunk = chunks[0]
    assert "[Document: FastAPI Core Guide" in first_chunk.text
    assert first_chunk.chunk_id.startswith("doc_fastapi_core_chk_")

def test_chunk_metadata_building():
    content, frontmatter = load_markdown_file(TEST_MD_PATH)
    sections = parse_markdown_structure(content, frontmatter.get("document_name"))
    chunks = create_structure_aware_chunks(sections, frontmatter.get("document_id"), frontmatter.get("document_name"))
    
    metadata = build_chunk_metadata(chunks[0], frontmatter)
    assert metadata["document_id"] == "doc_nexacloud_sec_v2"
    assert metadata["version"] == "2.0"
    assert metadata["status"] == "active"
    assert metadata["access_level"] == "internal"
