import re
from typing import List, Dict, Any, Optional
from backend.app.ingestion.parser import ParsedSection

class Chunk:
    def __init__(
        self,
        chunk_id: str,
        text: str,
        section_title: str,
        breadcrumbs: Optional[List[str]] = None,
        page_number: Optional[int] = None,
        slide_number: Optional[int] = None,
        chunk_index: int = 0
    ):
        self.chunk_id = chunk_id
        self.text = text
        self.section_title = section_title
        self.breadcrumbs = breadcrumbs or []
        self.page_number = page_number
        self.slide_number = slide_number
        self.chunk_index = chunk_index

def create_structure_aware_chunks(
    sections: List[ParsedSection],
    document_id: str,
    document_name: str,
    max_chunk_chars: int = 1800,
    overlap_chars: int = 250
) -> List[Chunk]:
    """
    Creates structure-aware chunks from parsed Markdown sections.
    Prepends header breadcrumbs to every chunk for contextual integrity.
    Preserves fenced code blocks as indivisible units where possible.
    """
    chunks: List[Chunk] = []
    global_chunk_idx = 0

    for section in sections:
        lineage_str = " > ".join(section.breadcrumbs) if section.breadcrumbs else section.title
        header_context = f"[Document: {document_name} | Lineage: {lineage_str}]\n\n"
        
        content = section.content.strip()
        if not content:
            continue

        # If content fits in a single chunk with header context
        if len(header_context) + len(content) <= max_chunk_chars:
            global_chunk_idx += 1
            chunk_id = f"{document_id}_chk_{global_chunk_idx:03d}"
            chunks.append(Chunk(
                chunk_id=chunk_id,
                text=header_context + content,
                section_title=section.title,
                breadcrumbs=section.breadcrumbs,
                chunk_index=global_chunk_idx
            ))
            continue

        # If section content is long, split on paragraph breaks or code blocks
        blocks = split_content_into_blocks(content)
        current_chunk_text = ""

        for block in blocks:
            # If adding block exceeds max_chunk_chars, flush current chunk
            if current_chunk_text and (len(header_context) + len(current_chunk_text) + len(block) > max_chunk_chars):
                global_chunk_idx += 1
                chunk_id = f"{document_id}_chk_{global_chunk_idx:03d}"
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    text=header_context + current_chunk_text.strip(),
                    section_title=section.title,
                    breadcrumbs=section.breadcrumbs,
                    chunk_index=global_chunk_idx
                ))
                
                # Apply overlap from the end of current_chunk_text if possible
                overlap_text = current_chunk_text[-overlap_chars:] if len(current_chunk_text) > overlap_chars else ""
                current_chunk_text = overlap_text + "\n\n" + block
            else:
                if current_chunk_text:
                    current_chunk_text += "\n\n" + block
                else:
                    current_chunk_text = block

        # Flush trailing chunk
        if current_chunk_text.strip():
            global_chunk_idx += 1
            chunk_id = f"{document_id}_chk_{global_chunk_idx:03d}"
            chunks.append(Chunk(
                chunk_id=chunk_id,
                text=header_context + current_chunk_text.strip(),
                section_title=section.title,
                breadcrumbs=section.breadcrumbs,
                chunk_index=global_chunk_idx
            ))

    return chunks

def split_content_into_blocks(content: str) -> List[str]:
    """
    Splits text content into semantic paragraphs while keeping fenced code blocks intact.
    """
    blocks: List[str] = []
    lines = content.splitlines()
    
    current_block: List[str] = []
    in_code = False
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            current_block.append(line)
            if not in_code: # End of code block
                blocks.append("\n".join(current_block))
                current_block = []
            continue
            
        if in_code:
            current_block.append(line)
        else:
            if not stripped: # Paragraph break
                if current_block:
                    blocks.append("\n".join(current_block))
                    current_block = []
            else:
                current_block.append(line)
                
    if current_block:
        blocks.append("\n".join(current_block))
        
    return blocks
