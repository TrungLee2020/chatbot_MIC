import asyncio
import edge_tts
import os
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
import uuid
import logging

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

# Create directory for audio files
OUTPUT_DIR = "output/output_audio"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Initialize FastAPI app
app = FastAPI(title="Edge TTS API for Telegram Bot")


# Define request models
class TTSRequest(BaseModel):
    text: str
    voice: str = "vi-VN-NamMinhNeural"
    file_name: Optional[str] = None


class VoiceInfo(BaseModel):
    name: str
    gender: str
    display_name: str
    locale: str


# Function to convert text to speech
async def text_to_speech(text: str, voice: str, output_file: str) -> bool:
    try:
        # Create Communicate object
        communicate = edge_tts.Communicate(text, voice)

        # Save to file
        await communicate.save(output_file)

        logger.info(f"Created audio file: {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error creating speech: {str(e)}")
        return False


# Background task to clean up old files
async def cleanup_old_files(file_path: str, delay: int = 300):
    """Delete file after specified delay (default: 5 minutes)"""
    await asyncio.sleep(delay)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted temporary file: {file_path}")
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {str(e)}")


# API endpoints
@app.get("/")
async def root():
    return {"message": "Edge TTS API is running. Use /tts endpoint to convert text to speech."}


@app.post("/api/text-to-speech")
async def create_tts(tts_request: TTSRequest, background_tasks: BackgroundTasks):
    """
    Convert text to speech and return the audio file.

    - **text**: Text to convert to speech
    - **voice**: Voice to use (default: vi-VN-NamMinhNeural)
    - **file_name**: Optional custom filename (without extension)
    """
    # Generate a unique filename if not provided
    file_name = tts_request.file_name or f"tts_{uuid.uuid4().hex}"
    file_path = os.path.join(OUTPUT_DIR, f"{file_name}.mp3")

    # Convert text to speech
    success = await text_to_speech(tts_request.text, tts_request.voice, file_path)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to generate speech")

    # Schedule file cleanup
    background_tasks.add_task(cleanup_old_files, file_path)

    # Return the audio file
    return FileResponse(
        path=file_path,
        media_type="audio/mpeg",
        filename=f"{file_name}.mp3"
    )


@app.get("/voices")
async def get_voices() -> List[VoiceInfo]:
    """Get list of available voices"""
    try:
        voices = await edge_tts.list_voices()

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
    except Exception as e:
        logger.error(f"Error getting voice list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve voices: {str(e)}")


@app.get("/voices/vietnamese")
async def get_vietnamese_voices() -> List[VoiceInfo]:
    """Get list of Vietnamese voices only"""
    voices = await get_voices()
    return [voice for voice in voices if voice.locale == "vi-VN"]


if __name__ == "__main__":
    uvicorn.run("tts_api:app", host="127.0.0.1", port=5002, reload=True)