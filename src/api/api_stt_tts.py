import os
import tempfile
import aiohttp
from typing import Optional

from config import STT_API_URL, TTS_API_URL, TTS_VOICE
from src.utils import setup_logger

# Get logger
logger = setup_logger("voices", "logs/voices.log")


async def speech_to_text(audio_path: str, language: str = "vi-VN") -> str:
    """
    Convert audio to text using STT API
    """
    try:
        # Create form data for file upload
        form_data = aiohttp.FormData()
        form_data.add_field(
            name='file',
            value=open(audio_path, 'rb'),
            filename=os.path.basename(audio_path),
            content_type='audio/ogg'  # Telegram voice format
        )
        form_data.add_field('language', language)

        # Call STT API
        async with aiohttp.ClientSession() as session:
            async with session.post(STT_API_URL, data=form_data, timeout=30) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('success'):
                        text = result.get('text', '')
                        logger.info(f"Recognized text: {text[:50]}...")
                        return text
                logger.error(f"STT API error: {response.status}")
                return ""
    except Exception as e:
        logger.error(f"Speech-to-text error: {e}")
        return ""


async def text_to_speech(text: str, voice: str = TTS_VOICE) -> Optional[str]:
    """Convert text to audio using TTS API"""
    try:
        # Call API with text payload
        async with aiohttp.ClientSession() as session:
            async with session.post(TTS_API_URL, json={'text': text, 'voice': voice}, timeout=30) as response:
                if response.status == 200:
                    # Save audio to temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                        temp_file.write(await response.read())
                        return temp_file.name
                logger.error(f"TTS API error: {response.status} - {await response.text()}")
                return None
    except Exception as e:
        logger.error(f"Text-to-speech error: {e}")
        return None

async def get_available_voices() -> list:
    """
    Get list of available TTS voices
    """
    try:
        # Call TTS API to get voices
        voice_url = f"{TTS_API_URL.rsplit('/', 1)[0]}/voices/vietnamese"
        async with aiohttp.ClientSession() as session:
            async with session.get(voice_url, timeout=10) as response:
                return await response.json() if response.status == 200 else []
    except Exception as e:
        logger.error(f"Error getting voices: {e}")
        return []