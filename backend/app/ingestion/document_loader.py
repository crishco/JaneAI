"""Document text extraction for supported file formats."""

import logging
from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from app.config.settings import Settings

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".markdown"}


class DocumentLoaderError(Exception):
    """Raised when a document cannot be loaded or parsed."""


class DocumentLoader:
    """Extracts plain text from PDF, DOCX, TXT, and Markdown files."""

    def __init__(self, settings: Settings) -> None:
        self._allowed_extensions = {
            ext.lower() for ext in settings.allowed_upload_extensions
        }

    def validate_extension(self, filename: str) -> str:
        """Return the normalized file extension if supported."""
        extension = Path(filename).suffix.lower()
        if extension not in self._allowed_extensions:
            supported = ", ".join(sorted(self._allowed_extensions))
            raise DocumentLoaderError(
                f"Unsupported file type '{extension}'. Supported: {supported}"
            )
        return extension

    def extract_text(self, filename: str, content: bytes) -> str:
        """Extract text from raw file bytes based on the filename extension."""
        extension = self.validate_extension(filename)
        logger.info("Extracting text from %s (%d bytes)", filename, len(content))

        try:
            if extension == ".pdf":
                text = self._extract_pdf(content)
            elif extension == ".docx":
                text = self._extract_docx(content)
            else:
                text = self._extract_plain_text(content)
        except DocumentLoaderError:
            raise
        except Exception as exc:
            logger.error("Failed to extract text from %s", filename)
            raise DocumentLoaderError(f"Failed to extract text from {filename}") from exc

        cleaned = " ".join(text.split())
        if not cleaned:
            raise DocumentLoaderError(f"No text content found in {filename}")

        logger.info("Extracted %d characters from %s", len(cleaned), filename)
        return cleaned

    @staticmethod
    def _extract_pdf(content: bytes) -> str:
        reader = PdfReader(BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages).strip()
        if not text:
            raise DocumentLoaderError("PDF contains no extractable text")
        return text

    @staticmethod
    def _extract_docx(content: bytes) -> str:
        document = Document(BytesIO(content))
        paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
        text = "\n".join(paragraphs).strip()
        if not text:
            raise DocumentLoaderError("DOCX contains no extractable text")
        return text

    @staticmethod
    def _extract_plain_text(content: bytes) -> str:
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise DocumentLoaderError("Unable to decode text file")
