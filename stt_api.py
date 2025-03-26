import os
import tempfile
import asyncio
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
import speech_recognition as sr
from pydub import AudioSegment
import uvicorn
import logging
from typing import Optional

# Cấu hình logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Speech-to-Text API", description="API để chuyển đổi giọng nói thành văn bản")

# Đường dẫn lưu file tạm thời
TEMP_DIR = "temp_audio"
os.makedirs(TEMP_DIR, exist_ok=True)


# Hàm chuyển đổi OGG sang WAV
def convert_audio_to_wav(file_path: str, original_format: str) -> str:
    """Chuyển đổi file âm thanh sang định dạng WAV"""
    try:
        wav_path = os.path.splitext(file_path)[0] + ".wav"

        if original_format.lower() == "ogg":
            audio = AudioSegment.from_ogg(file_path)
        elif original_format.lower() == "mp3":
            audio = AudioSegment.from_mp3(file_path)
        else:
            audio = AudioSegment.from_file(file_path, format=original_format)

        audio.export(wav_path, format="wav")
        logger.info(f"Đã chuyển đổi từ {original_format} sang WAV: {wav_path}")
        return wav_path
    except Exception as e:
        logger.error(f"Lỗi khi chuyển đổi âm thanh: {str(e)}")
        raise


# Hàm xử lý speech-to-text
async def process_speech_to_text(file_path: str, file_format: str, language: str = "vi-VN") -> str:
    """Xử lý file âm thanh và chuyển thành văn bản"""
    try:
        # Chuyển đổi sang WAV nếu chưa phải
        if not file_path.lower().endswith(".wav"):
            wav_path = convert_audio_to_wav(file_path, file_format)
        else:
            wav_path = file_path

        # Xử lý nhận dạng giọng nói
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language=language)

        # Dọn dẹp file
        try:
            if wav_path != file_path:
                os.remove(wav_path)
        except Exception as e:
            logger.warning(f"Không thể xóa file tạm: {str(e)}")

        return text
    except Exception as e:
        logger.error(f"Lỗi khi xử lý speech-to-text: {str(e)}")
        raise


# Hàm xóa file tạm sau khi xử lý
def cleanup_temp_file(file_path: str):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Đã xóa file tạm: {file_path}")
    except Exception as e:
        logger.warning(f"Không thể xóa file tạm {file_path}: {str(e)}")


@app.post("/api/speech-to-text")
async def speech_to_text(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        language: str = "vi-VN"
):
    """
    Chuyển đổi file âm thanh thành văn bản.
    - **file**: File âm thanh (ogg, mp3, wav,...)
    - **language**: Mã ngôn ngữ (mặc định: vi-VN)
    """
    try:
        # Lưu file tạm
        file_format = os.path.splitext(file.filename)[1][1:] if "." in file.filename else "ogg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_format}", dir=TEMP_DIR) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        logger.info(f"Đã lưu file tạm: {temp_file_path}, định dạng: {file_format}")

        # Xử lý bất đồng bộ
        text = await process_speech_to_text(temp_file_path, file_format, language)

        # Thêm tác vụ nền để xóa file tạm
        background_tasks.add_task(cleanup_temp_file, temp_file_path)

        return JSONResponse(
            status_code=200,
            content={"success": True, "text": text}
        )
    except Exception as e:
        logger.error(f"Lỗi API: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/health")
async def health_check():
    """Kiểm tra trạng thái hoạt động của API"""
    return {"status": "ok"}

# main xử lý chính
if __name__ == "__main__":
    uvicorn.run("stt_api:app", host="127.0.0.1", port=5001, reload=True)