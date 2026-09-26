import os
import yaml
from typing import Dict, Any, Tuple, List
from backend.app.core.logging import logger

def load_markdown_file(file_path: str) -> Tuple[str, Dict[str, Any]]:
    """
    Loads a Markdown (.md) file and extracts YAML frontmatter if present.
    
    Returns:
        Tuple[str, Dict[str, Any]]: (clean_content, frontmatter_dict)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Markdown file not found: {file_path}")
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="latin-1") as f:
            raw_text = f.read()
        
    frontmatter = {}
    content = raw_text
    
    if raw_text.startswith("---"):
        parts = raw_text.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
                content = parts[2].strip()
            except yaml.YAMLError as e:
                logger.warning(f"Failed to parse YAML frontmatter in {file_path}: {e}")
                
    return content, frontmatter

def load_txt_file(file_path: str) -> str:
    """
    Loads a plain text (.txt) file with UTF-8 / latin-1 encoding fallback.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Text file not found: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="latin-1") as f:
            return f.read()

def load_pdf_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Loads a PDF (.pdf) file and extracts text page-by-page preserving page numbers.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")
        
    pages = []
    try:
        import pypdf
        reader = pypdf.PdfReader(file_path)
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append({
                    "page_number": i + 1,
                    "text": page_text.strip()
                })
    except Exception as e:
        logger.error(f"Error reading PDF file {file_path}: {e}")
        
    return pages

def load_docx_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Loads a Word Document (.docx) file preserving paragraph headings.
    
    Returns:
        List[Dict[str, Any]]: List of sections containing heading title and content text.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"DOCX file not found: {file_path}")

    sections = []
    try:
        import docx
        doc = docx.Document(file_path)
        current_heading = "General"
        current_paragraphs = []

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            if p.style.name.startswith("Heading"):
                if current_paragraphs:
                    sections.append({
                        "heading": current_heading,
                        "text": "\n".join(current_paragraphs)
                    })
                    current_paragraphs = []
                current_heading = text
            else:
                current_paragraphs.append(text)

        if current_paragraphs:
            sections.append({
                "heading": current_heading,
                "text": "\n".join(current_paragraphs)
            })
    except Exception as e:
        logger.error(f"Error reading DOCX file {file_path}: {e}")

    return sections

def load_pptx_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Loads a PowerPoint presentation (.pptx) preserving slide numbers and titles.
    
    Returns:
        List[Dict[str, Any]]: List of slide dicts with slide_number, title, and text.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PPTX file not found: {file_path}")

    slides = []
    try:
        import pptx
        prs = pptx.Presentation(file_path)
        for idx, slide in enumerate(prs.slides, start=1):
            slide_text_blocks = []
            slide_title = f"Slide {idx}"

            if slide.shapes.title and slide.shapes.title.text:
                slide_title = slide.shapes.title.text.strip()

            for shape in slide.shapes:
                if hasattr(shape, "text_frame") and shape.text_frame:
                    t = shape.text_frame.text.strip()
                    if t and t != slide_title:
                        slide_text_blocks.append(t)

            combined_text = f"{slide_title}\n\n" + "\n".join(slide_text_blocks)
            if combined_text.strip():
                slides.append({
                    "slide_number": idx,
                    "title": slide_title,
                    "text": combined_text.strip()
                })
    except Exception as e:
        logger.error(f"Error reading PPTX file {file_path}: {e}")

    return slides

def load_html_file(file_path: str) -> Dict[str, Any]:
    """
    Loads an HTML (.html / .htm) file and extracts clean text and document title using BeautifulSoup.
    
    Returns:
        Dict[str, Any]: Dict containing title and clean body text.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"HTML file not found: {file_path}")

    try:
        from bs4 import BeautifulSoup
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_html = f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin-1") as f:
                raw_html = f.read()

        soup = BeautifulSoup(raw_html, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        title = soup.title.string.strip() if (soup.title and soup.title.string) else os.path.basename(file_path)
        
        # Extract structured text with headings preserved
        text = soup.get_text(separator="\n", strip=True)
        return {
            "title": title,
            "text": text
        }
    except Exception as e:
        logger.error(f"Error reading HTML file {file_path}: {e}")
        return {"title": os.path.basename(file_path), "text": ""}
