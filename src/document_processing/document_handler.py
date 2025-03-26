import os
import logging
from typing import List, Dict, Any, Optional, Tuple

from src.manager.Process_manager import process_document, download_file

# Get logger
logger = logging.getLogger(__name__)


async def download_document_from_url(url: str, file_extension: str = '.pdf') -> Optional[str]:
    """Download document from URL - maintained for backward compatibility"""
    return await download_file(url, file_extension, source='url')

async def download_pdf_from_telegram(file_id: str, bot: Any) -> Optional[str]:
    """Download PDF from Telegram - maintained for backward compatibility"""
    return await download_file('', '.pdf', source='telegram', bot=bot, file_id=file_id)

async def process_document_text(document_path: str, document_type: str = 'pdf') -> Tuple[List[str], List[Dict]]:
    """Legacy function for document_processing document text"""
    return await process_document(document_path, document_type)

async def extract_text_from_pdf(pdf_path: str) -> str:
    """Legacy function for extracting text from PDF"""
    text_chunks, _ = await process_document(pdf_path, 'pdf', extract_full=True)
    return text_chunks[0] if text_chunks else ""

def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return os.path.splitext(filename)[1].lower()
