import re
from typing import List, Dict, Any

class ParsedSection:
    def __init__(self, title: str, level: int, content: str, breadcrumbs: List[str]):
        self.title = title
        self.level = level # 1 for #, 2 for ##, etc.
        self.content = content
        self.breadcrumbs = breadcrumbs # e.g. ["FastAPI Security", "OAuth2 Bearer"]

    def get_lineage_header(self) -> str:
        if not self.breadcrumbs:
            return f"[Section: {self.title}]"
        lineage = " > ".join(self.breadcrumbs)
        return f"[Lineage: {lineage}]"

def parse_markdown_structure(content: str, doc_name: str) -> List[ParsedSection]:
    """
    Parses Markdown text into structural sections while tracking heading lineage.
    Preserves fenced code blocks intact inside section contents.
    """
    lines = content.splitlines()
    sections: List[ParsedSection] = []
    
    current_title = doc_name
    current_level = 0
    current_lines: List[str] = []
    breadcrumb_stack: List[Tuple[int, str]] = [] # [(level, title)]
    
    in_code_block = False
    
    for line in lines:
        stripped = line.strip()
        
        # Track fenced code block state to prevent interpreting '#' inside code blocks as headers
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            current_lines.append(line)
            continue
            
        if not in_code_block and stripped.startswith("#"):
            # Count header level
            match = re.match(r"^(#+)\s+(.*)$", stripped)
            if match:
                # Flush previous section
                if current_lines:
                    section_content = "\n".join(current_lines).strip()
                    breadcrumbs = [b[1] for b in breadcrumb_stack]
                    if section_content:
                        sections.append(ParsedSection(
                            title=current_title,
                            level=current_level,
                            content=section_content,
                            breadcrumbs=breadcrumbs
                        ))
                    current_lines = []
                    
                level = len(match.group(1))
                title = match.group(2).strip()
                
                # Update breadcrumb stack
                while breadcrumb_stack and breadcrumb_stack[-1][0] >= level:
                    breadcrumb_stack.pop()
                breadcrumb_stack.append((level, title))
                
                current_title = title
                current_level = level
                continue
                
        current_lines.append(line)
        
    # Flush final section
    if current_lines:
        section_content = "\n".join(current_lines).strip()
        breadcrumbs = [b[1] for b in breadcrumb_stack]
        if section_content:
            sections.append(ParsedSection(
                title=current_title,
                level=current_level,
                content=section_content,
                breadcrumbs=breadcrumbs
            ))
            
    return sections
