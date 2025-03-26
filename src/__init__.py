# This file makes the 'modules' directory a Python package
# It allows imports like 'from modules.api_client import speech_to_text'

from src.utils import setup_logger

# Setup a logger for the modules package
logger = setup_logger("modules", "logs/modules.log")