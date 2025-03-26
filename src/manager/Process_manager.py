import os
import tempfile
from typing import List, Dict, Optional, Tuple
import aiohttp
from functools import partial
from langchain.document_loaders import PyPDFLoader, TextLoader, CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

from src.utils import setup_logger

logger = setup_logger("modules", "logs/modules.log")

DOCUMENT_LOADERS = {
    'pdf': PyPDFLoader,
    'txt': TextLoader,
    'csv': CSVLoader
}

TEXT_SPLITTER = partial(
    RecursiveCharacterTextSplitter,
    chunk_size=1000,
    chunk_overlap=100
)


async def download_file(url: str, file_extension: str = '.pdf', source: str = 'url', **kwargs) -> Optional[str]:
    """Generic file download function that handles URLs and Telegram files"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            file_path = temp_file.name

        if source == 'url':
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download, status: {response.status}")
                        return None
                    with open(file_path, 'wb') as f:
                        f.write(await response.read())
        elif source == 'telegram':
            bot, file_id = kwargs.get('bot'), kwargs.get('file_id')
            if not bot or not file_id:
                logger.error("Missing bot or file_id for Telegram download")
                return None
            file = await bot.get_file(file_id)
            await file.download_to_drive(file_path)
        else:
            logger.error(f"Unsupported source: {source}")
            return None

        return file_path
    except Exception as e:
        logger.error(f"Error downloading file from {source}: {str(e)}")
        return None


async def process_document(document_path: str, document_type: str = 'pdf', extract_full: bool = False) -> Tuple[
    List[str], List[Dict]]:
    """Process document - returns either chunks or full text based on extract_full flag"""
    try:
        document_type = document_type.lower()
        if document_type not in DOCUMENT_LOADERS:
            logger.error(f"Unsupported document type: {document_type}")
            return [], []

        # Load document
        loader = DOCUMENT_LOADERS[document_type](document_path)
        pages = loader.load()

        if extract_full and document_type == 'pdf':
            return ["\n\n".join([page.page_content for page in pages])], [{"source": os.path.basename(document_path)}]

        # Split text into chunks
        text_splitter = TEXT_SPLITTER()
        chunks = text_splitter.split_documents(pages)

        # Extract text and metadata
        text_chunks = [chunk.page_content for chunk in chunks]
        metadata_chunks = [
            {
                "source": os.path.basename(document_path),
                "page": chunk.metadata.get("page", i + 1)
            }
            for i, chunk in enumerate(chunks)
        ]

        return text_chunks, metadata_chunks
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        return [], []