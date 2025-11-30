"""
File Validation Utilities
==========================

Validates uploaded files (PDFs and audio files) for:
- File type/extension
- File size limits
- Content validity

Author: Hackathon Team
Date: November 2025
"""

from pathlib import Path
from fastapi import UploadFile, HTTPException
from config import config


class FileValidator:
    """Validates uploaded files against size and type constraints"""

    @staticmethod
    async def validate_document(file: UploadFile) -> bytes:
        """
        Validate document file size and format (PDF, DOC, DOCX, PPT, PPTX, TXT)

        Args:
            file: Uploaded document file from FastAPI

        Returns:
            bytes: File content as bytes

        Raises:
            HTTPException: If file is invalid (wrong type, too large)
        """
        # Supported document formats
        SUPPORTED_FORMATS = {'.pdf', '.doc', '.docx', '.ppt', '.pptx', '.txt'}

        # Check file extension
        file_extension = '.' + file.filename.lower().split('.')[-1] if '.' in file.filename else ''

        if file_extension not in SUPPORTED_FORMATS:
            supported_list = ', '.join(SUPPORTED_FORMATS)
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format. Supported formats: {supported_list}"
            )

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Check file size
        if file_size > config.MAX_PDF_SIZE:  # Reuse PDF size limit for all documents
            max_size_mb = config.MAX_PDF_SIZE / (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {max_size_mb:.0f}MB"
            )

        # Check minimum size (prevent empty files)
        if file_size < 100:
            raise HTTPException(
                status_code=400,
                detail="File is too small or empty"
            )

        # Reset file pointer for further processing
        await file.seek(0)
        return content

    @staticmethod
    async def validate_pdf(file: UploadFile) -> bytes:
        """
        Validate PDF file (legacy method for backwards compatibility)
        Use validate_document instead
        """
        return await FileValidator.validate_document(file)

    @staticmethod
    async def validate_audio(file: UploadFile) -> bytes:
        """
        Validate audio file size and format

        Args:
            file: Uploaded audio file from FastAPI

        Returns:
            bytes: File content as bytes

        Raises:
            HTTPException: If file is invalid (wrong format, too large)
        """
        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in config.AUDIO_FORMATS:
            supported_formats = ", ".join(config.AUDIO_FORMATS)
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio format. Supported formats: {supported_formats}"
            )

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Check file size
        if file_size > config.MAX_AUDIO_SIZE:
            max_size_mb = config.MAX_AUDIO_SIZE / (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"Audio file too large. Maximum size: {max_size_mb:.0f}MB"
            )

        # Check minimum size (prevent empty files)
        if file_size < 1000:
            raise HTTPException(
                status_code=400,
                detail="Audio file is too small or empty"
            )

        # Reset file pointer
        await file.seek(0)
        return content

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        Format file size in human-readable format

        Args:
            size_bytes: Size in bytes

        Returns:
            str: Formatted size (e.g., "1.5 MB")
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
