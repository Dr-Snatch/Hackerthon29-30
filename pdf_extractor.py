"""
PDF Text Extraction Module
===========================

Extracts text from PDF files using PyPDF2.
Supports text-based PDFs only (no OCR for scanned documents).

Author: Hackathon Team
Date: November 2025
"""

import io
from PyPDF2 import PdfReader
from fastapi import HTTPException


class PDFExtractor:
    """Extract text content from PDF files"""

    @staticmethod
    def extract_text(pdf_bytes: bytes) -> str:
        """
        Extract text from PDF file

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            str: Extracted text content

        Raises:
            HTTPException: If PDF is empty, unreadable, or image-based
        """
        try:
            # Create PDF reader from bytes
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PdfReader(pdf_file)

            # Check if PDF has pages
            num_pages = len(pdf_reader.pages)
            if num_pages == 0:
                raise HTTPException(
                    status_code=400,
                    detail="PDF file is empty (no pages found)"
                )

            # Extract text from all pages
            text_content = []
            for page_num, page in enumerate(pdf_reader.pages, start=1):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_content.append(page_text)

            # Join all pages with double newlines
            full_text = "\n\n".join(text_content).strip()

            # Validate extraction was successful
            if not full_text or len(full_text) < 50:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Could not extract sufficient text from PDF. "
                        "The PDF may be scanned, image-based, or encrypted. "
                        "Only text-based PDFs are supported. "
                        f"(Extracted only {len(full_text)} characters from {num_pages} pages)"
                    )
                )

            print(f"Successfully extracted {len(full_text)} characters from {num_pages} pages")
            return full_text

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise

        except Exception as e:
            # Catch all other errors (corrupted PDF, invalid format, etc.)
            error_msg = str(e)
            if "encrypted" in error_msg.lower():
                detail = "PDF is encrypted or password-protected. Please provide an unencrypted PDF."
            elif "invalid" in error_msg.lower() or "corrupt" in error_msg.lower():
                detail = f"PDF file appears to be corrupted or invalid: {error_msg}"
            else:
                detail = f"PDF extraction failed: {error_msg}"

            raise HTTPException(
                status_code=500,
                detail=detail
            )

    @staticmethod
    def get_pdf_info(pdf_bytes: bytes) -> dict:
        """
        Get PDF metadata information

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            dict: PDF metadata (pages, title, author, etc.)
        """
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PdfReader(pdf_file)

            metadata = pdf_reader.metadata or {}

            return {
                "num_pages": len(pdf_reader.pages),
                "title": metadata.get("/Title", "Unknown"),
                "author": metadata.get("/Author", "Unknown"),
                "creator": metadata.get("/Creator", "Unknown"),
                "producer": metadata.get("/Producer", "Unknown"),
            }

        except Exception as e:
            # Return minimal info if metadata extraction fails
            return {
                "num_pages": 0,
                "error": str(e)
            }
