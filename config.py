import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database config
DB_NAME = os.getenv("DB_NAME", "data/database/data.db")
CHAT_HISTORY_DB = os.getenv("CHAT_HISTORY_DB", "data/database/chat_history.db")

# Telegram config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

# API endpoints
LLM_URL = os.getenv("LLM_URL")
STT_API_URL = os.getenv("STT_API_URL", "http://127.0.0.1:5001/api/speech-to-text")
TTS_API_URL = os.getenv("TTS_API_URL", "http://127.0.0.1:5002/api/text-to-speech")

# LLM config
CHATBOT_MODEL = os.getenv("CHATBOT_MODEL")
CHATBOT_TEMPERATURE = float(os.getenv("CHATBOT_TEMPERATURE", "0.5"))
CHATBOT_MAX_TOKENS = int(os.getenv("CHATBOT_MAX_TOKENS", "500"))

# ChromaDB config
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "data/chroma_db")
EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# TTS voice config
TTS_VOICE = os.getenv("TTS_VOICE", "vi-VN-NamMinhNeural")

# Logging config
LOG_FILE = os.getenv("LOG_FILE", "logs/chatbot.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Chat history config
MAX_HISTORY_ENTRIES = int(os.getenv("MAX_HISTORY_ENTRIES", "5"))
RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", "0.7"))