import asyncio
import edge_tts
import os
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import uuid
import logging
import hashlib
import time
from functools import lru_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/tts_api.log")
    ]
)
logger = logging.getLogger(__name__)

# Create directories
OUTPUT_DIR = "output/output_audio"
CACHE_DIR = "output/cache"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# Initialize FastAPI app
app = FastAPI(title="Edge TTS API for Telegram Bot")

# Semaphore to limit concurrent TTS operations
# Adjust the value based on your server's capability
TTS_SEMAPHORE = asyncio.Semaphore(5)

# Cache for voices to avoid repeated API calls
VOICE_CACHE: Optional[List[Dict]] = None
VOICE_CACHE_EXPIRY = 3600  # 1 hour in seconds
VOICE_CACHE_TIMESTAMP = 0


# Define request models
class TTSRequest(BaseModel):
    text: str
    voice: str = "vi-VN-NamMinhNeural"
    file_name: Optional[str] = None
    force_new: bool = False  # Whether to force regeneration even if cached


class VoiceInfo(BaseModel):
    name: str
    gender: str
    display_name: str
    locale: str


# Function to generate a cache key for a TTS request
def get_cache_key(text: str, voice: str) -> str:
    """Generate a unique cache key for a text+voice combination"""
    hash_input = f"{text}|{voice}"
    return hashlib.md5(hash_input.encode()).hexdigest()


# Function to check if a cached file exists
def get_cached_file(cache_key: str) -> Optional[str]:
    """Check if a cached file exists and return its path if it does"""
    cache_path = os.path.join(CACHE_DIR, f"{cache_key}.mp3")
    if os.path.exists(cache_path):
        return cache_path
    return None


# Function to convert text to speech with semaphore for concurrency control
async def text_to_speech(text: str, voice: str, output_file: str, force_new: bool = False) -> str:
    """Convert text to speech and return the path to the output file"""
    # Check cache first if not forcing new generation
    if not force_new:
        cache_key = get_cache_key(text, voice)
        cached_file = get_cached_file(cache_key)
        if cached_file:
            logger.info(f"Using cached audio file: {cached_file}")
            return cached_file

    # Acquire semaphore before performing TTS operation
    async with TTS_SEMAPHORE:
        try:
            start_time = time.time()

            # Create Communicate object
            communicate = edge_tts.Communicate(text, voice)

            # For caching - save to cache directory if not forcing new
            if not force_new:
                cache_key = get_cache_key(text, voice)
                cache_path = os.path.join(CACHE_DIR, f"{cache_key}.mp3")
                await communicate.save(cache_path)

                # Copy to output file
                import shutil
                shutil.copy2(cache_path, output_file)

                end_time = time.time()
                logger.info(f"TTS operation completed in {end_time - start_time:.2f} seconds")
                return output_file
            else:
                # Save directly to output file
                await communicate.save(output_file)

                end_time = time.time()
                logger.info(f"TTS operation completed in {end_time - start_time:.2f} seconds")
                return output_file

        except Exception as e:
            logger.error(f"Error creating speech: {str(e)}")
            raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")


# Background task to clean up old files
async def cleanup_old_files(file_path: str, delay: int = 300):
    """Delete file after specified delay (default: 5 minutes)"""
    await asyncio.sleep(delay)
    try:
        if os.path.exists(file_path) and file_path.startswith(OUTPUT_DIR):  # Safety check
            os.remove(file_path)
            logger.info(f"Deleted temporary file: {file_path}")
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {str(e)}")


# Cache cleanup task
async def cleanup_cache():
    """Periodically clean up cache files older than 24 hours"""
    while True:
        await asyncio.sleep(3600)  # Run every hour
        try:
            current_time = time.time()
            count = 0
            for filename in os.listdir(CACHE_DIR):
                file_path = os.path.join(CACHE_DIR, filename)
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > 86400:  # 24 hours in seconds
                        os.remove(file_path)
                        count += 1
            if count > 0:
                logger.info(f"Cleaned up {count} old cache files")
        except Exception as e:
            logger.error(f"Error during cache cleanup: {str(e)}")


# Start background cache cleanup task
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_cache())


# API endpoints
@app.get("/")
async def root():
    return {"message": "Edge TTS API is running. Use /api/text-to-speech endpoint to convert text to speech."}


@app.post("/api/text-to-speech")
async def create_tts(tts_request: TTSRequest, background_tasks: BackgroundTasks):
    """
    Convert text to speech and return the audio file.

    - **text**: Text to convert to speech
    - **voice**: Voice to use (default: vi-VN-NamMinhNeural)
    - **file_name**: Optional custom filename (without extension)
    - **force_new**: Force regeneration even if cached (default: false)
    """
    # Validate input
    if not tts_request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    # Generate a unique filename if not provided
    file_name = tts_request.file_name or f"tts_{uuid.uuid4().hex}"
    file_path = os.path.join(OUTPUT_DIR, f"{file_name}.mp3")

    try:
        # Perform text to speech conversion
        result_path = await text_to_speech(
            tts_request.text,
            tts_request.voice,
            file_path,
            tts_request.force_new
        )

        # Schedule file cleanup for the output file (not the cached version)
        if os.path.normpath(result_path) == os.path.normpath(file_path):
            background_tasks.add_task(cleanup_old_files, file_path)

        # Return the audio file
        return FileResponse(
            path=result_path,
            media_type="audio/mpeg",
            filename=f"{file_name}.mp3"
        )
    except Exception as e:
        logger.error(f"Error in TTS endpoint: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Failed to generate speech: {str(e)}")


# Get voice list with caching
async def get_voice_list() -> List[Dict]:
    """Get list of available voices with caching"""
    global VOICE_CACHE, VOICE_CACHE_TIMESTAMP

    current_time = time.time()

    # Check if cache has expired
    if VOICE_CACHE is None or (current_time - VOICE_CACHE_TIMESTAMP) > VOICE_CACHE_EXPIRY:
        try:
            voices = await edge_tts.list_voices()
            VOICE_CACHE = voices
            VOICE_CACHE_TIMESTAMP = current_time
            return voices
        except Exception as e:
            logger.error(f"Error getting voice list: {str(e)}")
            if VOICE_CACHE is not None:
                logger.info("Using expired voice cache due to error")
                return VOICE_CACHE
            raise HTTPException(status_code=500, detail=f"Failed to retrieve voices: {str(e)}")
    else:
        return VOICE_CACHE


@app.get("/voices")
async def get_voices() -> List[VoiceInfo]:
    """Get list of available voices"""
    voices = await get_voice_list()

    # Convert to response model
    voice_info_list = [
        VoiceInfo(
            name=voice["ShortName"],
            gender=voice["Gender"],
            display_name=voice["DisplayName"],
            locale=voice["Locale"]
        )
        for voice in voices
    ]

    return voice_info_list


@app.get("/voices/vietnamese")
async def get_vietnamese_voices() -> List[VoiceInfo]:
    """Get list of Vietnamese voices only"""
    voices = await get_voices()
    return [voice for voice in voices if voice.locale == "vi-VN"]


# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": time.time(),
        "cache_info": {
            "voice_cache_size": len(VOICE_CACHE) if VOICE_CACHE else 0,
            "voice_cache_age": time.time() - VOICE_CACHE_TIMESTAMP if VOICE_CACHE else None,
        }
    }


if __name__ == "__main__":
    uvicorn.run("tts_api:app", host="127.0.0.1", port=5002, reload=True)