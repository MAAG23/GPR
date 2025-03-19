import os
import asyncio
import logging
import time
import random
import json
import httpx
import requests
from pydantic import BaseModel
from typing import Dict, Optional, Literal
from contextlib import asynccontextmanager

from config import FISH_AUDIO_API_KEY, FISH_AUDIO_API_URL, CELEBRITIES, OUTPUT_AUDIO_DIR
from utils import generate_unique_filename, ensure_directory_exists

# Configure logger
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("voice_synthesizer")


class TTSRequest(BaseModel):
    """Model for TTS request to Fish Audio API"""
    text: str
    reference_id: str  # This is the voice ID
    chunk_length: int = 200
    normalize: bool = True
    format: Literal["wav", "pcm", "mp3", "opus"] = "wav"
    mp3_bitrate: Literal[64, 128, 192] = 192
    latency: Literal["normal", "balanced"] = "normal"
    model: Literal["speech-1.6"] = "speech-1.6"
    prosody: Dict[str, float] = {
        "speed": 0.9,  # Slowed down for more natural pacing
    }


# Voice-specific speeds for better quality
VOICE_SPEEDS = {
    "cristiano_ronaldo": 0.95,
    "donald_trump": 0.85,  # Slower for Trump's distinctive pacing
    "default": 0.9  # Default speed
}


@asynccontextmanager
async def get_httpx_client(timeout=60.0):
    """Context manager for httpx client"""
    client = httpx.AsyncClient(timeout=timeout)
    try:
        yield client
    finally:
        await client.aclose()


class VoiceSynthesizer:
    def __init__(self):
        """Initialize the Fish Audio API client"""
        self.api_key = FISH_AUDIO_API_KEY
        self.api_url = FISH_AUDIO_API_URL
        ensure_directory_exists(OUTPUT_AUDIO_DIR)

    def synthesize_speech(self, text, celebrity_id):
        """
        Synchronous wrapper around async speech synthesis

        Args:
            text (str): The text to synthesize
            celebrity_id (str): The ID of the celebrity voice to use

        Returns:
            str: The path to the synthesized audio file
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.synthesize_speech_async(text, celebrity_id))
        finally:
            loop.close()

    async def synthesize_speech_async(self, text, celebrity_id, max_retries=3, timeout=60.0):
        """
        Use Fish Audio API to synthesize speech in a celebrity's voice (async version)

        Args:
            text (str): The text to synthesize
            celebrity_id (str): The ID of the celebrity voice to use
            max_retries (int): Maximum number of retry attempts
            timeout (float): Request timeout in seconds

        Returns:
            str: The path to the synthesized audio file
        """
        # Get celebrity info
        if celebrity_id not in CELEBRITIES:
            raise ValueError(f"Celebrity {celebrity_id} not found")

        celebrity = CELEBRITIES[celebrity_id]
        voice_id = celebrity["fish_audio_voice_id"]
        name = celebrity["name"]

        # Add context to logs
        log_prefix = f"[Voice:{name}]"
        logger.info(
            f"{log_prefix} Generating voice audio for text: {text[:50]}...")

        # Get voice-specific speed or use default
        speed = VOICE_SPEEDS.get(celebrity_id, VOICE_SPEEDS["default"])
        logger.info(f"{log_prefix} Using voice speed: {speed}")

        # Create output file path
        output_file = generate_unique_filename(OUTPUT_AUDIO_DIR, "wav")

        # Prepare request
        request = TTSRequest(
            text=text,
            reference_id=voice_id,  # Use reference_id instead of voice_id
            format="wav",
            chunk_length=200,
            mp3_bitrate=192,
            model="speech-1.6",
            prosody={
                "speed": speed,
            }
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "model": "speech-1.6"  # Also include in headers
        }

        # Retry logic
        retries = 0
        last_error = None

        while retries < max_retries:
            try:
                logger.info(
                    f"{log_prefix} Making API request to Fish Audio (attempt {retries+1}/{max_retries})")
                # Use context manager to ensure client is properly closed
                async with get_httpx_client(timeout=timeout) as client:
                    start_time = time.time()
                    try:
                        async with client.stream(
                            "POST",
                            self.api_url,
                            json=request.model_dump(),
                            headers=headers,
                            timeout=timeout
                        ) as response:
                            if response.status_code != 200:
                                error_text = await response.aread()
                                logger.error(
                                    f"{log_prefix} Fish Audio API Error: {response.status_code}")
                                logger.error(
                                    f"{log_prefix} Error details: {error_text.decode()}")
                                raise Exception(
                                    f"Fish Audio API error: {response.status_code}")

                            logger.info(
                                f"{log_prefix} Received successful response, writing to file")
                            with open(output_file, "wb") as f:
                                async for chunk in response.aiter_bytes():
                                    f.write(chunk)

                        duration = time.time() - start_time
                        logger.info(
                            f"{log_prefix} API request completed in {duration:.2f} seconds")
                        return output_file

                    except httpx.TimeoutException:
                        logger.warning(
                            f"{log_prefix} Request timed out after {timeout} seconds")
                        raise

            except Exception as e:
                last_error = e
                retries += 1
                logger.error(f"{log_prefix} Fish Audio API Error: {str(e)}")

                if retries < max_retries:
                    # Exponential backoff with jitter
                    wait_time = (2 ** retries) + random.uniform(0, 1)
                    logger.info(
                        f"{log_prefix} Retrying in {wait_time:.2f} seconds (attempt {retries+1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"{log_prefix} All {max_retries} attempts failed")
                    break

        # If we got here, all retries failed
        error_message = str(
            last_error) if last_error else "Failed to generate voice after multiple attempts"
        logger.error(f"{log_prefix} {error_message}")

        # Fallback to synchronous request as a last resort
        try:
            logger.info(
                f"{log_prefix} Attempting fallback to synchronous request")
            return self._synchronous_fallback(text, celebrity_id, output_file)
        except Exception as e:
            logger.error(
                f"{log_prefix} Synchronous fallback also failed: {str(e)}")
            raise Exception(f"Failed to synthesize speech: {error_message}")

    def _synchronous_fallback(self, text, celebrity_id, output_file):
        """Fallback to synchronous request if async fails"""
        voice_id = CELEBRITIES[celebrity_id]["fish_audio_voice_id"]
        name = CELEBRITIES[celebrity_id]["name"]
        log_prefix = f"[Voice:{name}]"

        # Prepare request for Fish Audio API
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "model": "speech-1.6"  # Include in headers
        }

        data = {
            "text": text,
            "reference_id": voice_id,  # Use reference_id instead of voice_id
            "format": "wav",
            "chunk_length": 200,
            "mp3_bitrate": 192,
            "model": "speech-1.6",
            "prosody": {
                "speed": VOICE_SPEEDS.get(celebrity_id, VOICE_SPEEDS["default"])
            }
        }

        # Make synchronous request
        logger.info(
            f"{log_prefix} Making synchronous API request to Fish Audio")
        response = requests.post(
            self.api_url,
            headers=headers,
            json=data,
            stream=True
        )

        # Check if request was successful
        response.raise_for_status()

        # Save audio to file
        with open(output_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"{log_prefix} Synchronous request successful")
        return output_file
