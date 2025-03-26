import os
import logging
import tempfile
from typing import List, Optional
import aiohttp
from telegram import Bot
from logging.handlers import RotatingFileHandler

# Initialize logger
logger = logging.getLogger(__name__)


def setup_logger(name: str, log_file: str, level=logging.INFO, max_bytes=5 * 1024 * 1024,
                 backup_count=1) -> logging.Logger:
    """
    Set up a logger with rotating file handler and console handler
    Args:
        name: Logger name
        log_file: Path to log file
        level: Logging level
        max_bytes: Maximum size of log file before rotation (default: 5MB)
        backup_count: Number of backup files to keep (default: 1)
    Returns:
        logging.Logger: Configured logger
    """
    # Create directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()

    # Create handlers
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    console_handler = logging.StreamHandler()

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Set formatter
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def extract_image_urls(text: str) -> List[str]:
    """
    Extract image URLs from text

    Args:
        text: Text to extract URLs from

    Returns:
        List[str]: List of image URLs
    """
    import re

    # Pattern to match URLs ending with image extensions
    pattern = r'https?://\S+\.(jpg|jpeg|png|gif|bmp|webp)'

    # Find all matches
    urls = re.findall(pattern, text, re.IGNORECASE)

    return urls


async def download_image(url: str) -> Optional[str]:
    """
    Download image from URL

    Args:
        url: Image URL

    Returns:
        Optional[str]: Path to downloaded image or None on failure
    """
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            image_path = temp_file.name

        # Download image
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    with open(image_path, 'wb') as f:
                        f.write(await response.read())
                    return image_path
                else:
                    logger.error(f"Failed to download image, status: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error downloading image: {str(e)}")
        return None


async def send_media_group(image_urls: List[str], chat_id: int, token: str) -> bool:
    """
    Send a group of images to a Telegram chat

    Args:
        image_urls: List of image URLs to send
        chat_id: Telegram chat ID
        token: Telegram bot token

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Download images
        local_images = []
        for url in image_urls:
            image_path = await download_image(url)
            if image_path:
                local_images.append(image_path)

        if not local_images:
            logger.error("No images downloaded successfully")
            return False

        # Initialize bot
        bot = Bot(token=token)

        # Send images
        from telegram import InputMediaPhoto

        media_group = [
            InputMediaPhoto(open(img_path, 'rb'))
            for img_path in local_images
        ]

        await bot.send_media_group(chat_id=chat_id, media=media_group)

        # Clean up
        for img_path in local_images:
            try:
                os.remove(img_path)
            except Exception as e:
                logger.warning(f"Error removing temporary image: {str(e)}")

        return True
    except Exception as e:
        logger.error(f"Error sending media group: {str(e)}")
        return False


def clean_temp_files(directory: str = None, max_age: int = 3600) -> int:
    """
    Clean up temporary files older than max_age seconds

    Args:
        directory: Directory to clean (default: system temp dir)
        max_age: Maximum age in seconds (default: 1 hour)

    Returns:
        int: Number of files removed
    """
    import time

    if not directory:
        directory = tempfile.gettempdir()

    count = 0
    current_time = time.time()

    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)

            # Check if it's a file
            if os.path.isfile(file_path):
                # Check if it's a temp file from our app (e.g., .mp3, .ogg, .pdf)
                if any(file_path.endswith(ext) for ext in ['.mp3', '.ogg', '.pdf', '.wav']):
                    # Check file age
                    file_age = current_time - os.path.getmtime(file_path)

                    if file_age > max_age:
                        os.remove(file_path)
                        count += 1
                        logger.debug(f"Removed old temp file: {file_path}")
    except Exception as e:
        logger.error(f"Error cleaning temp files: {str(e)}")

    return count