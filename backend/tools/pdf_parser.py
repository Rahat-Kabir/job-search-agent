"""
PDF parsing tool for CV extraction.

Extracts text content from PDF files using pypdf.
"""

from io import BytesIO

from langchain_core.tools import tool
from pypdf import PdfReader


@tool
def parse_pdf(pdf_content: bytes) -> str:
    """
    Extract text from a PDF file.

    Args:
        pdf_content: Raw bytes of the PDF file

    Returns:
        Extracted text content from all pages
    """
    try:
        reader = PdfReader(BytesIO(pdf_content))
        text_parts = []

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        return "\n\n".join(text_parts)

    except Exception as e:
        return f"Error parsing PDF: {str(e)}"


def parse_pdf_from_path(file_path: str) -> str:
    """
    Extract text from a PDF file path.

    Args:
        file_path: Path to the PDF file

    Returns:
        Extracted text content
    """
    with open(file_path, "rb") as f:
        return parse_pdf.invoke({"pdf_content": f.read()})
