import os
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters
)

# Import configuration
from config import TELEGRAM_BOT_TOKEN, LOG_FILE

# Import handlers
from src.bot.Bot_Manager import TelegramBotHandler

# Import utility for logging
from src.utils import setup_logger

# Configure main logger
logger = setup_logger("main", LOG_FILE)


def check_environment() -> bool:
    """
    Check if required environment variables are set

    Returns:
        bool: True if all required variables are set, False otherwise
    """
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set! Please set it in your .env file.")
        return False

    return True


def setup_application() -> Application:
    """
    Set up the Telegram application

    Returns:
        Application: Configured Telegram application
    """
    # Create application
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    bot_handler = TelegramBotHandler()

    # Add command handlers
    application.add_handler(CommandHandler("start", bot_handler.start_command))
    application.add_handler(CommandHandler("help", bot_handler.help_command))
    application.add_handler(CommandHandler("history", bot_handler.history_command))

    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handler.handle_text_message))
    application.add_handler(MessageHandler(filters.VOICE, bot_handler.handle_voice_message))
    application.add_handler(MessageHandler(filters.Document.PDF, bot_handler.handle_pdf_document))

    # Add error handler
    application.add_error_handler(bot_handler.error_handler)

    return application


def main() -> None:
    """
    Main application entry point
    """
    logger.info("Starting Telegram chatbot...")

    # Check environment
    if not check_environment():
        return

    # Setup application
    application = setup_application()

    # Create required directories
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data/database", exist_ok=True)
    os.makedirs("data/chroma_db", exist_ok=True)

    # Start the application
    logger.info("Application setup complete, starting polling...")
    application.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()