import os
import logging
import tempfile
import time

from typing import Optional, List, Dict, Any
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from config import MAX_HISTORY_ENTRIES, RELEVANCE_THRESHOLD
from src.api.api_stt_tts import speech_to_text, text_to_speech
from src.core.chroma_handler import process_pdf, search_documents
from src.core.llm_generate import generate_answer
from src.core.core_shop import rag_query, execute_query
from src.manager.Chat_History_Manager import ChatHistoryManager
from src.utils import setup_logger


logger = setup_logger("modules", "logs/modules.log")

# Import chat hítory
chat_history_manager = ChatHistoryManager()

class TelegramBotHandler:
    """
    Class to handle Telegram bot functionality and message document_processing
    """

    def __init__(self, max_history: int = MAX_HISTORY_ENTRIES):
        """
        Initialize the TelegramBotHandler
        """
        # Initialize logger
        self.logger = logging.getLogger(__name__)

        # Initialize chat history manager
        self.chat_history_manager = ChatHistoryManager(max_history=max_history)

        # Threshold for ChromaDB relevance
        self.chroma_relevance_threshold = RELEVANCE_THRESHOLD

    async def process_and_respond(
            self,
            chat_id: int,
            query_text: str,
            context: ContextTypes.DEFAULT_TYPE,
            update: Optional[Update] = None,
            voice_response: bool = False
    ) -> None:
        """
        Process user query and send appropriate response
        """
        try:
            start_time = time.time()
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

            # Đăng ký log để debug
            self.logger.info(f"Processing query: '{query_text}'")

            # Step 1: Search ChromaDB for relevant information and get scores
            # Không lọc trong hàm search_documents (threshold=0.0), để lấy tất cả kết quả
            chroma_results, relevance_scores = await search_documents(query_text, return_scores=True)
            self.logger.info(f"ChromaDB search completed in {time.time() - start_time:.2f} seconds")

            # Step 2: Determine which data source to use based on ChromaDB scores
            query_result = ""
            use_sql = self._determine_data_source(relevance_scores)

            # Get chat history for context in either case
            chat_history = self.chat_history_manager.get_chat_history(chat_id, limit=1)
            # check history và câu hỏi mới co tuong quan voi nhau khong
            relevant_history = self.chat_history_manager.filter_relevant_history(query_text, chat_history)

            context_str = self._format_chat_history(relevant_history)

            # Execute SQL query if needed
            if use_sql:
                self.logger.info("Generating SQL RAG query")
                sql_query = rag_query(query_text, chat_history)

                if sql_query:
                    from config import DB_NAME
                    query_result = execute_query(DB_NAME, sql_query)
                    self.logger.info(f"SQL query executed, result size: {len(query_result)}")

            # Step 3: Format conversation context
            if chat_history:
                history_entries = list(reversed(chat_history))
                context_str = self._format_chat_history(history_entries)

            # Thêm log để gỡ lỗi
            self.logger.info(f"Using {'SQL' if use_sql else 'ChromaDB'} as data source")
            if chroma_results:
                self.logger.info(f"ChromaDB results length: {len(chroma_results.strip())}")

            # Step 4: Generate the final answer with the appropriate prompt template
            prompt_template = "sql_based" if use_sql else "chromadb_based"
            answer = await generate_answer(
                query_text,
                context_str,
                query_result,
                chroma_results,
                prompt_template=prompt_template
            )

            # Step 5: Save to chat history
            self.chat_history_manager.add_conversation(chat_id, query_text, answer)

            # Step 6: Send voice response if requested
            if voice_response:
                await self._send_voice_response(answer, update, context, chat_id)

            # Step 7: Send text response
            await self._send_text_response(answer, update, context, chat_id)

            self.logger.info(f"Total document_processing time: {time.time() - start_time:.2f} seconds")

        except Exception as e:
            await self._handle_processing_error(e, chat_id, query_text, update, context)

    def _determine_data_source(self, relevance_scores: List[float]) -> bool:
        """
        Determine whether to use SQL or ChromaDB based on relevance scores
        """
        if relevance_scores:
            avg_score = sum(relevance_scores) / len(relevance_scores)
            dynamic_threshold = max(0.15, avg_score * 0.8)  # Adjust based on data
            return max(relevance_scores) < dynamic_threshold
        else:
            self.logger.info("No ChromaDB results, using SQL")
            return True

    def _format_chat_history(self, history_entries: List[Dict[str, Any]]) -> str:
        """
        Format chat history into a string
        """
        return "\n".join([
            f"User: {entry['user_question']}\nBot: {entry['bot_response']}"
            for entry in reversed(history_entries)
        ])

    async def _send_voice_response(
            self,
            answer: str,
            update: Optional[Update],
            context: ContextTypes.DEFAULT_TYPE,
            chat_id: int
    ) -> None:
        """
        Send voice response to the user
        """
        audio_file = await text_to_speech(answer)
        if audio_file:
            if update:
                await update.message.reply_voice(voice=open(audio_file, 'rb'))
            else:
                await context.bot.send_voice(chat_id=chat_id, voice=open(audio_file, 'rb'))
            os.remove(audio_file)
        else:
            self.logger.error("Failed to generate voice response")

    async def _send_text_response(
            self,
            answer: str,
            update: Optional[Update],
            context: ContextTypes.DEFAULT_TYPE,
            chat_id: int
    ) -> None:
        """
        Send text response to the user
        """
        if update:
            await update.message.reply_text(answer)
        else:
            await context.bot.send_message(chat_id=chat_id, text=answer)

    async def _handle_processing_error(
            self,
            error: Exception,
            chat_id: int,
            query_text: str,
            update: Optional[Update],
            context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle document_processing errors
        """
        self.logger.error(f"Error document_processing message: {str(error)}")
        error_message = f"Xin lỗi, đã xảy ra lỗi trong quá trình xử lý tin nhắn của bạn."

        # Try to save conversation with error
        try:
            self.chat_history_manager.add_conversation(chat_id, query_text, error_message)
        except Exception as history_err:
            self.logger.error(f"Failed to save error message to history: {str(history_err)}")

        if update:
            await update.message.reply_text(error_message)
        else:
            await context.bot.send_message(chat_id=chat_id, text=error_message)

    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle voice messages from users
        """
        chat_id = update.effective_chat.id
        voice = update.message.voice

        # Show typing indicator
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        # Download voice file
        voice_file = await context.bot.get_file(voice.file_id)

        # Use temp file to store voice
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_file:
            voice_bytes = await voice_file.download_as_bytearray()
            temp_file.write(voice_bytes)
            temp_file_path = temp_file.name

        try:
            # Convert speech to text using API
            text = await speech_to_text(temp_file_path)

            if text:
                # Inform user of recognized question
                await update.message.reply_text(f"Câu hỏi của bạn là: {text}")

                # Process the question and respond with voice
                await self.process_and_respond(chat_id, text, context, update, voice_response=True)
            else:
                await update.message.reply_text("Xin lỗi, tôi không thể nhận dạng giọng nói của bạn.")
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    async def handle_pdf_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle PDF documents uploaded by users
        """
        chat_id = update.effective_chat.id
        document = update.message.document

        # Check if it's a PDF
        if not document.file_name.lower().endswith('.pdf'):
            await update.message.reply_text("Vui lòng gửi file PDF.")
            return

        # Notify user we're document_processing
        await update.message.reply_text("Đang xử lý file PDF của bạn...")
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        try:
            # Download PDF
            pdf_file = await context.bot.get_file(document.file_id)

            # Use temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                pdf_bytes = await pdf_file.download_as_bytearray()
                temp_file.write(pdf_bytes)
                pdf_path = temp_file.name

            # Process PDF and add to ChromaDB
            result = await process_pdf(pdf_path, document.file_name)

            # Send response
            await update.message.reply_text(result)
        except Exception as e:
            self.logger.error(f"Error document_processing PDF: {str(e)}")
            await update.message.reply_text(f"Lỗi khi xử lý file PDF: {str(e)}")
        finally:
            # Clean up temp file
            if 'pdf_path' in locals() and os.path.exists(pdf_path):
                os.remove(pdf_path)

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle text messages from users
        """
        chat_id = update.effective_chat.id
        query_text = update.message.text

        # Check if user wants voice response
        voice_response = False
        if query_text.strip().endswith('/voice'):
            voice_response = True
            query_text = query_text.replace('/voice', '').strip()

        self.logger.info(f"Processing text message: '{query_text}' with voice_response={voice_response}")

        # Process the query and respond
        await self.process_and_respond(chat_id, query_text, context, update, voice_response)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Send a message when the command /start is issued
        """
        user = update.effective_user
        welcome_message = (
            f"Xin chào {user.first_name}! Tôi là chatbot trợ giúp."
            f"\nBạn có thể gửi tin nhắn văn bản, tin nhắn thoại, hoặc tài liệu PDF để tôi xử lý."
            f"\nGõ /help để xem các lệnh và chức năng của tôi."
        )
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Send a message when the command /help is issued
        """
        help_text = (
            "👋 Xin chào! Tôi là trợ lý trả lời câu hỏi cho bạn. Tôi có thể:\n\n"
            "🔍 Trả lời câu hỏi từ cơ sở dữ liệu\n"
            "📄 Trích xuất thông tin từ file PDF bạn gửi\n"
            "🔊 Hiểu và trả lời tin nhắn thoại\n\n"
            "Các lệnh hỗ trợ:\n"
            "/start - Khởi động bot\n"
            "/help - Hiển thị trợ giúp này\n"
            "/history - Xem lịch sử hội thoại gần đây\n\n"
            "💡 Mẹo:\n"
            "- Gửi tin nhắn thoại để hỏi bằng giọng nói\n"
            "- Thêm '/voice' vào cuối câu hỏi để nhận trả lời bằng giọng nói\n"
            "- Gửi file PDF để tôi có thể tìm hiểu và trả lời về nội dung file\n"
        )
        await update.message.reply_text(help_text)

    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Display recent chat history."""
        chat_id = update.effective_chat.id

        # Get formatted history text
        history_text = chat_history_manager.get_conversation_text_history(chat_id, limit=5)

        await update.message.reply_text(history_text)

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log errors and send a message to the user."""
        logger.error(f"Exception while handling an update: {context.error}")

        # Send message to the user
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Xin lỗi, đã xảy ra lỗi trong quá trình xử lý yêu cầu của bạn. Xin vui lòng đặt lại câu hỏi."
            )