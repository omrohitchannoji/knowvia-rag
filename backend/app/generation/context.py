from typing import List, Dict, Any, Tuple
from backend.app.schemas.query import Citation

class ContextBuilder:
    """
    Formats candidate chunks into structured context blocks for the LLM prompt.
    Generates inline citation markers [Source 1], [Source 2] and maps them
    back to explicit Citation objects.
    """
    
    @staticmethod
    def format_context(candidates: List[Dict[str, Any]]) -> Tuple[str, List[Citation]]:
        """
        Takes a list of candidate chunk dicts and constructs:
        1. A formatted context block string for LLM injection.
        2. A list of Citation objects matching [Source 1], [Source 2], etc.
        """
        if not candidates:
            return "", []

        formatted_blocks = []
        citations = []

        for idx, candidate in enumerate(candidates, start=1):
            text = candidate.get("text", "").strip()
            metadata = candidate.get("metadata", {})
            
            doc_name = metadata.get("document_name", metadata.get("title", "Unknown Document"))
            section = metadata.get("heading_lineage", metadata.get("section", "General"))
            access_level = metadata.get("access_level", "PUBLIC_USER")
            version = metadata.get("version", "v1.0")
            page = metadata.get("page")
            source_url = metadata.get("source_url")

            # Build Citation mapping schema
            citation = Citation(
                source_index=idx,
                document_name=doc_name,
                section=section,
                page=page,
                version=version,
                access_level=access_level,
                source_url=source_url
            )
            citations.append(citation)

            # Build structured context string block with explicit metadata header
            header = f"[Source {idx}] [Document: {doc_name}] [Section: {section}] [Access Level: {access_level}]"
            block = f"{header}\n{text}"
            formatted_blocks.append(block)

        context_str = "\n\n---\n\n".join(formatted_blocks)
        return context_str, citations
