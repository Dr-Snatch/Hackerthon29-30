"""
Audio Transcription Module
===========================

Transcribes audio files using OpenAI Whisper.
Supports both API mode (cloud) and local mode (on-device).

Author: Hackathon Team
Date: November 2025
"""

import tempfile
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from config import config, WhisperMode


class AudioTranscriber:
    """Transcribe audio files to text using Whisper"""

    def __init__(self):
        """Initialize transcriber based on configured mode"""
        self.mode = config.WHISPER_MODE
        print(f"Initializing AudioTranscriber in {self.mode.value} mode")

        if self.mode == WhisperMode.API:
            # Import OpenAI client for API mode
            try:
                import openai
                if not config.OPENAI_API_KEY:
                    raise ValueError("OPENAI_API_KEY is required for API mode")
                self.openai_client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
                print("OpenAI Whisper API client initialized")
            except ImportError:
                raise ImportError(
                    "openai package is required for API mode. "
                    "Install with: pip install openai"
                )

        else:  # LOCAL mode
            # Import and load local Whisper model
            try:
                import whisper
                print(f"Loading local Whisper model: {config.WHISPER_MODEL_SIZE}")
                self.whisper_model = whisper.load_model(config.WHISPER_MODEL_SIZE)
                print(f"Local Whisper model '{config.WHISPER_MODEL_SIZE}' loaded successfully")
            except ImportError:
                raise ImportError(
                    "openai-whisper package is required for local mode. "
                    "Install with: pip install openai-whisper torch torchaudio"
                )
            except Exception as e:
                raise RuntimeError(f"Failed to load local Whisper model: {str(e)}")

    async def transcribe_audio_streaming(
        self,
        audio_bytes: bytes,
        filename: str,
        language: Optional[str] = None
    ):
        """
        Transcribe audio and yield segments as they're processed
        Generator function for streaming results
        """
        if self.mode == WhisperMode.API:
            # API mode doesn't support streaming, fall back to full transcription
            text = await self._transcribe_with_api(audio_bytes, filename, language)
            yield {"type": "complete", "text": text}
        else:
            # Local mode - transcribe then stream segments
            async for segment in self._transcribe_local_streaming(audio_bytes, filename, language):
                yield segment

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        filename: str,
        language: Optional[str] = None
    ) -> str:
        """
        Transcribe audio file to text

        Args:
            audio_bytes: Audio file content as bytes
            filename: Original filename (for extension detection)
            language: ISO 639-1 language code (e.g., 'en', 'es', 'fr')
                     None = auto-detect language

        Returns:
            str: Transcribed text

        Raises:
            HTTPException: If transcription fails
        """
        if self.mode == WhisperMode.API:
            return await self._transcribe_with_api(audio_bytes, filename, language)
        else:
            return await self._transcribe_local(audio_bytes, filename, language)

    async def _transcribe_with_api(
        self,
        audio_bytes: bytes,
        filename: str,
        language: Optional[str] = None
    ) -> str:
        """
        Transcribe using OpenAI Whisper API

        OpenAI API does not support streaming for transcription,
        so this method waits for the full result.
        """
        temp_path = None
        try:
            # Create temporary file (API requires file object)
            with tempfile.NamedTemporaryFile(
                suffix=Path(filename).suffix,
                delete=False
            ) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name

            print(f"Transcribing audio via OpenAI API (language: {language or 'auto-detect'})")

            # Run transcription in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=open(temp_path, "rb"),
                    language=language if language and language != 'en' else None,
                    response_format="text"
                )
            )

            transcribed_text = result.strip() if isinstance(result, str) else result

            print(f"Transcription complete: {len(transcribed_text)} characters")
            return transcribed_text

        except Exception as e:
            error_msg = str(e)
            if "rate_limit" in error_msg.lower():
                detail = "OpenAI API rate limit exceeded. Please try again later."
            elif "invalid_api_key" in error_msg.lower() or "unauthorized" in error_msg.lower():
                detail = "Invalid OpenAI API key. Please check your OPENAI_API_KEY configuration."
            elif "insufficient" in error_msg.lower():
                detail = "Insufficient API credits. Please check your OpenAI account."
            else:
                detail = f"Audio transcription failed: {error_msg}"

            raise HTTPException(status_code=500, detail=detail)

        finally:
            # Clean up temporary file
            if temp_path:
                try:
                    Path(temp_path).unlink(missing_ok=True)
                except Exception as cleanup_error:
                    print(f"Warning: Failed to clean up temp file: {cleanup_error}")

    async def _transcribe_local_streaming(
        self,
        audio_bytes: bytes,
        filename: str,
        language: Optional[str] = None
    ):
        """
        Transcribe using local Whisper and yield segments progressively
        """
        temp_path = None
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(
                suffix=Path(filename).suffix,
                delete=False
            ) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name

            print(f"Transcribing audio with local model (language: {language or 'auto-detect'})")

            # Run transcription in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.whisper_model.transcribe(
                    temp_path,
                    language=language if language and language != 'en' else None,
                    fp16=False,
                    verbose=True,
                    task='transcribe',
                    best_of=5,
                    beam_size=5,
                    patience=1.0,
                    temperature=0,
                    condition_on_previous_text=True,
                    initial_prompt=None,
                    compression_ratio_threshold=2.4,
                    logprob_threshold=-1.0,
                    no_speech_threshold=0.6
                )
            )

            # Stream segments as they're formatted with delay for organic feel
            if "segments" in result and result["segments"]:
                print(f"Processing {len(result['segments'])} segments")

                last_end_time = 0
                for i, segment in enumerate(result["segments"]):
                    text = segment["text"].strip()
                    start_time = segment.get("start", 0)
                    end_time = segment.get("end", 0)

                    # Format timestamp
                    minutes = int(start_time // 60)
                    seconds = int(start_time % 60)
                    timestamp = f"[{minutes:02d}:{seconds:02d}]"

                    # Detect natural breaks
                    pause_duration = start_time - last_end_time
                    is_natural_break = pause_duration >= 1.5
                    is_paragraph_break = pause_duration > 3.0
                    is_first_segment = i == 0

                    # Yield segment data
                    yield {
                        "type": "segment",
                        "text": text,
                        "timestamp": timestamp,
                        "is_natural_break": is_natural_break or is_first_segment,
                        "is_paragraph_break": is_paragraph_break,
                        "segment_index": i,
                        "total_segments": len(result["segments"])
                    }

                    # Add small delay between segments for organic streaming feel
                    # 100ms per segment gives smooth appearance without being too slow
                    await asyncio.sleep(0.1)

                    last_end_time = end_time

                yield {"type": "complete"}

        except Exception as e:
            yield {"type": "error", "message": str(e)}

        finally:
            if temp_path:
                try:
                    Path(temp_path).unlink(missing_ok=True)
                except Exception as cleanup_error:
                    print(f"Warning: Failed to clean up temp file: {cleanup_error}")

    async def _transcribe_local(
        self,
        audio_bytes: bytes,
        filename: str,
        language: Optional[str] = None
    ) -> str:
        """
        Transcribe using local Whisper model

        Runs CPU/GPU-intensive transcription in executor to avoid blocking.
        """
        temp_path = None
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(
                suffix=Path(filename).suffix,
                delete=False
            ) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name

            print(f"Transcribing audio with local model (language: {language or 'auto-detect'})")

            # Run transcription in executor (CPU/GPU-intensive operation)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.whisper_model.transcribe(
                    temp_path,
                    language=language if language and language != 'en' else None,
                    fp16=False,  # Use FP32 for CPU compatibility
                    verbose=True,  # Show progress for debugging
                    task='transcribe',  # Explicit transcribe task
                    best_of=5,  # Better accuracy
                    beam_size=5,  # Better for longer sequences
                    patience=1.0,  # Patience for beam search
                    temperature=0,  # More deterministic
                    condition_on_previous_text=True,  # CRITICAL: Enables long-form transcription!
                    initial_prompt=None,  # Let model decide based on audio
                    compression_ratio_threshold=2.4,  # Detect repetition
                    logprob_threshold=-1.0,  # Filter low-probability segments
                    no_speech_threshold=0.6  # Detect silence
                )
            )

            # Get full transcription from segments with timestamps and paragraphs
            # result["text"] can truncate, so we rebuild from segments
            if "segments" in result and result["segments"]:
                print(f"Processing {len(result['segments'])} segments")

                # Format transcription with timestamps and paragraph breaks
                formatted_lines = []
                current_paragraph = []
                last_end_time = 0

                for i, segment in enumerate(result["segments"]):
                    text = segment["text"].strip()
                    start_time = segment.get("start", 0)
                    end_time = segment.get("end", 0)

                    # Format timestamp as [MM:SS]
                    minutes = int(start_time // 60)
                    seconds = int(start_time % 60)
                    timestamp = f"[{minutes:02d}:{seconds:02d}]"

                    # Detect natural breaks in conversation:
                    # 1. Pauses of 1.5+ seconds (speaker changes, breaths, topic shifts)
                    # 2. First segment
                    pause_duration = start_time - last_end_time
                    is_natural_break = pause_duration >= 1.5
                    is_first_segment = i == 0

                    # Add paragraph break if significant pause (3+ seconds)
                    if pause_duration > 3.0 and current_paragraph:
                        # Save current paragraph
                        formatted_lines.append(" ".join(current_paragraph))
                        formatted_lines.append("")  # Empty line for paragraph break
                        current_paragraph = []
                        # After paragraph break, always add timestamp
                        is_natural_break = True

                    # Add timestamp at natural breaks or first segment
                    if is_natural_break or is_first_segment:
                        current_paragraph.append(f"{timestamp} {text}")
                    else:
                        current_paragraph.append(text)

                    last_end_time = end_time

                # Add the last paragraph
                if current_paragraph:
                    formatted_lines.append(" ".join(current_paragraph))

                transcribed_text = "\n".join(formatted_lines)
            else:
                # Fallback to result["text"] if no segments available
                print("Warning: No segments found, using result['text']")
                transcribed_text = result["text"].strip()

            print(f"Transcription complete: {len(transcribed_text)} characters from {len(result.get('segments', []))} segments")
            return transcribed_text

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Local transcription failed: {str(e)}"
            )

        finally:
            # Clean up temporary file
            if temp_path:
                try:
                    Path(temp_path).unlink(missing_ok=True)
                except Exception as cleanup_error:
                    print(f"Warning: Failed to clean up temp file: {cleanup_error}")


# Singleton transcriber instance
# Initialized once on module import to load model only once
transcriber = AudioTranscriber()
