"""
Configuration Module for Adaptive Lecture Summarizer
====================================================

Manages environment variables and application settings for:
- Whisper transcription mode (API or local)
- File size limits
- Supported file formats
- API keys

Author: Hackathon Team
Date: November 2025
"""

import os
from enum import Enum
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class WhisperMode(str, Enum):
    """Whisper transcription mode options"""
    API = "api"      # Use OpenAI Whisper API (cloud-based)
    LOCAL = "local"  # Use local Whisper model


class Config:
    """Application configuration from environment variables"""

    # ===== Whisper Configuration =====
    WHISPER_MODE = WhisperMode(os.getenv("WHISPER_MODE", "api"))
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")

    # ===== File Size Limits (in bytes) =====
    MAX_PDF_SIZE = int(os.getenv("MAX_PDF_SIZE_MB", "50")) * 1024 * 1024      # Default: 50MB
    MAX_AUDIO_SIZE = int(os.getenv("MAX_AUDIO_SIZE_MB", "200")) * 1024 * 1024  # Default: 200MB

    # ===== Supported File Formats =====
    AUDIO_FORMATS = {".mp3", ".wav", ".m4a"}
    PDF_FORMAT = ".pdf"

    # ===== Anthropic API =====
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

    # ===== Validation =====
    @classmethod
    def validate(cls):
        """Validate configuration on startup"""
        errors = []

        # Check Anthropic API key
        if not cls.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY is not set in .env file")

        # Check OpenAI API key if using API mode
        if cls.WHISPER_MODE == WhisperMode.API and not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required when WHISPER_MODE=api")

        if errors:
            error_msg = "Configuration errors:\n" + "\n".join(f"  - {err}" for err in errors)
            raise ValueError(error_msg)

        return True


# Singleton configuration instance
config = Config()
