import os
import logging
import httpx
import asyncio
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from config import FISH_AUDIO_API_KEY

# Configure logger
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("speech_recognizer")

# Fish Audio ASR API endpoint
ASR_API_URL = "https://api.fish.audio/v1/asr"


class TextSegment(BaseModel):
    """Model for a segment of transcribed text with timestamps"""
    text: str
    start: float
    end: float


class ASRResponse(BaseModel):
    """Model for Fish Audio ASR response"""
    text: str
    duration: float
    segments: List[TextSegment]


class ASRRequest(BaseModel):
    """Model for ASR request to Fish Audio API"""
    audio: bytes
    language: Optional[str] = None
    ignore_timestamps: bool = True


@asynccontextmanager
async def get_httpx_client(timeout=60.0):
    """Context manager for httpx client"""
    client = httpx.AsyncClient(timeout=timeout)
    try:
        yield client
    finally:
        await client.aclose()


class SpeechRecognizer:
    def __init__(self):
        """Initialize the Fish Audio ASR client"""
        self.api_key = FISH_AUDIO_API_KEY
        load_dotenv()  # Make sure environment variables are loaded

    def transcribe_audio(self, audio_file_path, language=None):
        """
        Transcribe audio file using Fish Audio's Speech-to-Text API

        Args:
            audio_file_path (str): Path to the audio file
            language (str, optional): Language code (e.g., 'en' for English)

        Returns:
            str: Transcribed text
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.transcribe_audio_async(audio_file_path, language))
        finally:
            loop.close()

    async def transcribe_audio_async(self, audio_file_path, language=None):
        """
        Asynchronously transcribe audio using Fish Audio's Speech-to-Text API

        Args:
            audio_file_path (str): Path to the audio file
            language (str, optional): Language code (e.g., 'en' for English)

        Returns:
            str: Transcribed text
        """
        # Read audio file
        with open(audio_file_path, 'rb') as f:
            audio_data = f.read()

        # Create request
        request = ASRRequest(
            audio=audio_data,
            language=language,
            ignore_timestamps=True  # Set to False for precise timestamps
        )

        # Set headers
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/msgpack'
        }

        try:
            # Use httpx to make the API request
            logger.info(
                f"Making Fish Audio ASR API request for file: {audio_file_path}")

            import ormsgpack  # Import here to avoid issues if not installed

            async with get_httpx_client() as client:
                response = await client.post(
                    ASR_API_URL,
                    headers=headers,
                    content=ormsgpack.packb(request.model_dump(
                        exclude={'audio'}) | {'audio': audio_data}),
                )

                # Check response status
                response.raise_for_status()

                # Parse response
                result = response.json()
                logger.info(
                    f"Successfully transcribed audio, duration: {result.get('duration', 0)} seconds")

                # Return just the transcribed text
                return result.get('text', '')

        except Exception as e:
            logger.error(
                f"Error transcribing audio with Fish Audio API: {str(e)}")
            # If we failed to transcribe, return an empty string
            return ""

    def get_segments(self, audio_file_path, language=None):
        """
        Get detailed segments with timestamps from the audio

        Args:
            audio_file_path (str): Path to the audio file
            language (str, optional): Language code (e.g., 'en' for English)

        Returns:
            List[TextSegment]: List of text segments with timestamps
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.get_segments_async(audio_file_path, language))
        finally:
            loop.close()

    async def get_segments_async(self, audio_file_path, language=None):
        """
        Asynchronously get detailed segments with timestamps from the audio

        Args:
            audio_file_path (str): Path to the audio file
            language (str, optional): Language code (e.g., 'en' for English)

        Returns:
            List[TextSegment]: List of text segments with timestamps
        """
        # Read audio file
        with open(audio_file_path, 'rb') as f:
            audio_data = f.read()

        # Create request with ignore_timestamps=False for detailed segments
        request = ASRRequest(
            audio=audio_data,
            language=language,
            ignore_timestamps=False  # Get precise timestamps
        )

        # Set headers
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/msgpack'
        }

        try:
            # Use httpx to make the API request
            logger.info(
                f"Making Fish Audio ASR API request for segments: {audio_file_path}")

            import ormsgpack  # Import here to avoid issues if not installed

            async with get_httpx_client() as client:
                response = await client.post(
                    ASR_API_URL,
                    headers=headers,
                    content=ormsgpack.packb(request.model_dump(
                        exclude={'audio'}) | {'audio': audio_data}),
                )

                # Check response status
                response.raise_for_status()

                # Parse response
                result = response.json()
                segments = [TextSegment(**segment)
                            for segment in result.get('segments', [])]

                logger.info(f"Successfully retrieved {len(segments)} segments")
                return segments

        except Exception as e:
            logger.error(
                f"Error getting segments with Fish Audio API: {str(e)}")
            # If we failed, return an empty list
            return []
