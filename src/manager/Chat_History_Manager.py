import os
import sqlite3
import logging
from typing import List, Dict

from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

logger = logging.getLogger(__name__)

# Dictionary lưu trữ lịch sử hội thoại theo chat_id
conversation_history = {}

class ChatHistoryManager:
    def __init__(self, db_path: str = "database/chat_history.db", max_history: int = 5):
        self.db_path = db_path
        self.max_history = max_history
        
        # Ensure database directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize database
        self._init_db()
        logger.info(f"Initialized ChatHistoryManager with database at {self.db_path}")
    
    def _init_db(self):
        """Initialize the database schema with the specific structure required."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chat_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        user_question TEXT,
                        bot_response TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # Create an index on user_id for faster queries
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON chat_history(user_id)")
                
                conn.commit()
                logger.info("Database schema initialized successfully")
        except Exception as e:
            error_msg = f"Không thể khởi tạo cơ sở dữ liệu: {str(e)}"
            logger.error(error_msg)
            print(error_msg)
    
    def get_conversation_history(self, chat_id):
        """
        Lấy lịch sử hội thoại cho chat_id từ dictionary
        """
        return conversation_history.get(chat_id, [])
    
    def save_conversation_history(self, chat_id, user_question, bot_response):
        """
        Lưu lịch sử hội thoại vào dictionary theo định dạng trong app.py
        """
        if chat_id not in conversation_history:
            conversation_history[chat_id] = []
            
        conversation_history[chat_id].append({"user": user_question, "bot": bot_response})
        
        # Giới hạn lịch sử để tránh quá dài (10 tin nhắn gần nhất)
        if len(conversation_history[chat_id]) > self.max_history:
            conversation_history[chat_id] = conversation_history[chat_id][-self.max_history:]
        
        # Đồng thời vẫn lưu vào database để có log dài hạn
        self.add_conversation(chat_id, user_question, bot_response)
    
    def add_conversation(self, user_id: int, user_question: str, bot_response: str) -> bool:
        """
        Add a conversation entry to the chat history in database
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Add the new conversation entry
                cursor.execute(
                    "INSERT INTO chat_history (user_id, user_question, bot_response) VALUES (?, ?, ?)",
                    (user_id, user_question, bot_response)
                )
                
                conn.commit()
                logger.info(f"Added conversation for user {user_id}")
                return True
        except Exception as e:
            logger.error(f"Error adding conversation: {str(e)}")
            return False
    
    def get_chat_history(self, user_id: int, limit: int = 5) -> List[Dict]:
        """
        Get chat history for a specific user_id from database
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    SELECT * FROM chat_history 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC LIMIT ?
                    """,
                    (user_id, limit)
                )
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error retrieving chat history: {str(e)}")
            return []
    
    def get_conversation_text_history(self, user_id: int, limit: int = 5) -> str:
        """
        Get formatted chat history text for a user
        """
        # Sử dụng conversation_history dictionary thay vì database
        history = self.get_conversation_history(user_id)
        
        if not history:
            return "Không có lịch sử hội thoại."
        
        text = "Lịch sử hội thoại gần đây:\n\n"
        # Giới hạn số lượng tin nhắn hiển thị
        displayed_history = history[-limit:] if len(history) > limit else history
        
        for i, entry in enumerate(displayed_history):
            text += f"{i+1}. Người dùng: {entry['user']}\n"
            text += f"   Bot: {entry['bot']}\n\n"
        
        return text

    def filter_relevant_history(self, query_text, chat_history):
        """
        Filters the chat history to find entries relevant to a given query.
        """
        query_embedding = model.encode(query_text)
        relevant_entries = []
        for entry in chat_history:
            entry_text = entry['user_question'] + " " + entry['bot_response']
            entry_embedding = model.encode(entry_text)
            similarity = cosine_similarity([query_embedding], [entry_embedding])[0][0]
            if similarity > 0.7:  # Adjustable threshold
                relevant_entries.append(entry)
        return relevant_entries

    def clear_user_history(self, user_id: int) -> bool:
        """
        Clear all chat history for a specific user
        """
        try:
            # Xóa từ dictionary
            if user_id in conversation_history:
                conversation_history.pop(user_id)
            
            # Xóa từ database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    "DELETE FROM chat_history WHERE user_id = ?",
                    (user_id,)
                )
                
                conn.commit()
                logger.info(f"Cleared chat history for user {user_id}")
                return True
        except Exception as e:
            logger.error(f"Error clearing chat history: {str(e)}")
            return False
        
# if __name__ == '__main__':
#     chat_history_manager = ChatHistoryManager()
#     # Thử nghiệm lưu lịch sử hội thoại
#     chat_history_manager.save_conversation_history(
#         chat_id=123456789,
#         user_question="Giá cà phê là bao nhiêu?",
#         bot_response="Giá cà phê hiện tại là 95,000 VND/kg."
#     )