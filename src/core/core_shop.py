import sqlite3
import os
from dotenv import load_dotenv
import logging
import requests
import time
from typing import Optional, Dict, Any

from src.bot.Prompts import QUERY_PROMPT_TEMPLATE
from src.manager.Chat_History_Manager import ChatHistoryManager

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("GENERAL_LOG_LEVEL", "INFO"))

load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:5000") 
API_KEY = os.getenv("API_KEY") 

chat_history_manager = ChatHistoryManager()
# call api to query model
def rag_query(user_prompt, chat_history=None):
    headers = {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        # Log chat_history for debugging
        if chat_history:
            logger.info(f"Received chat_history with {len(chat_history)} entries")
        else:
            logger.info("No chat_history provided")
            
        # Format chat history for the prompt
        context_str = ""
        if chat_history:
            # Format the chat history (oldest first)
            history_entries = list(reversed(chat_history))
            context_str = "\n".join([
                f"User: {entry['user_question']}\nBot: {entry['bot_response']}" 
                for entry in history_entries
            ])
        
        # Format the prompt template with proper parameters
        full_prompt = QUERY_PROMPT_TEMPLATE.format(query=user_prompt, context=context_str)
        logger.info(f"Full prompt sent to API (first 200 chars): {full_prompt[:500]}...")
    except Exception as e:
        logger.error(f"Error in rag_query preprocessing: {str(e)}")
        context_str = ""
        full_prompt = QUERY_PROMPT_TEMPLATE.format(query=user_prompt, context=context_str)

    try:
        response = requests.post(
            f"{API_URL}/api/generate",
            headers=headers,
            json={'prompt': full_prompt},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"API response: {result}")
            if result.get('success'):
                sql_query = extract_sql_query(result['response'])
                if sql_query:
                    logger.info(f"Generated SQL Query: {sql_query}")
                    return sql_query
                else:
                    logger.error("No SQL query extracted from the response.")
                    return None
            else:
                logger.error(f"API error: {result.get('error')}")
                return None
        else:
            logger.error(f"API request failed with status code: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        return None

def is_price_query(query):
    """Check if the query is asking about price"""
    price_keywords = ['giá', 'bao nhiêu tiền', 'giá cả', 'giá bao nhiêu', 'giá tiền', 'cost', 'price']
    query_lower = query.lower()
    is_price = any(keyword in query_lower for keyword in price_keywords)
    
    if is_price:
        logger.info(f"Query '{query}' identified as a price query")
    
    return is_price

# def extract_product_from_history(chat_history):
#     """Extract product name from chat history"""
#     if not chat_history:
#         return None
    
#     # Log the structure of chat_history for debugging
#     logger.info(f"Chat history structure: {type(chat_history)}, length: {len(chat_history)}")
#     if chat_history:
#         logger.info(f"First entry structure: {chat_history[0].keys() if isinstance(chat_history, list) and chat_history else 'No entries'}")
    
#     # Look for product names in bot responses
#     for entry in chat_history:
#         if not isinstance(entry, dict):
#             logger.warning(f"Unexpected entry type in chat history: {type(entry)}")
#             continue
            
#         bot_response = entry.get('bot_response', '')
#         logger.info(f"Processing bot response: {bot_response[:100]}...")
        
#         # Look for patterns like "Thông tin về [product]" or "[product] có giá"
#         product_patterns = [
#             r"thông tin về\s+(.+?)(?:\.|,|\s+là|\s+có|\s+giá|\s+được|\s+\-|\s+của|\s+do|$)",
#             r"sản phẩm\s+(.+?)(?:\.|,|\s+là|\s+có|\s+giá|\s+được|\s+\-|\s+của|\s+do|$)",
#             r"([^.,:]+)(?:có giá|giá là|giá)"
#         ]
        
#         for pattern in product_patterns:
#             matches = re.search(pattern, bot_response, re.IGNORECASE)
#             if matches:
#                 product = matches.group(1).strip()
#                 if product and len(product) > 3:  # Ensure we have a meaningful product name
#                     logger.info(f"Found product in history: {product}")
#                     return product
                    
#         # Also check for product names in database table format
#         if '|' in bot_response and 'good_name' in bot_response:
#             # This looks like a markdown table with product info
#             lines = bot_response.split('\n')
#             for i, line in enumerate(lines):
#                 if 'good_name' in line:
#                     # Found the header row, the next row might have the product name
#                     if i+2 < len(lines) and '|' in lines[i+2]:
#                         cells = [cell.strip() for cell in lines[i+2].split('|')]
#                         header_cells = [cell.strip() for cell in line.split('|')]
                        
#                         # Find the index of good_name in the header
#                         try:
#                             name_index = header_cells.index('good_name')
#                             if 1 <= name_index < len(cells):
#                                 product = cells[name_index].strip()
#                                 if product:
#                                     return product
#                         except ValueError:
#                             continue
    
#     return None

def extract_sql_query(response_text):
    if "```sql" in response_text:
        sql = response_text.split("```sql")[1].split("```")[0].strip()
    else:
        sql = response_text.strip()
    logger.info(f"SQL: {sql}")
    return sql


def execute_query(DB_NAME, query):
    """
    Execute the SQL query on the database.
    
    Args:
        DB_NAME (str): The path to the SQLite database file
        query (str): The SQL query to execute
        
    Returns:
        str: The query results formatted as a markdown table or an error message
    """
    attempts = 5  # Maximum retry attempts
    
    for attempt in range(attempts):
        try:
            if not os.path.exists(DB_NAME):
                raise FileNotFoundError(f"Database file not found: {DB_NAME}")
            
            conn = sqlite3.connect(DB_NAME, timeout=5)
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            if not results:
                return "Không có dữ liệu trả về."
            
            # Get column names from cursor description
            columns = [column[0] for column in cursor.description]
            
            return format_markdown_table(columns, results)
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < attempts - 1:
                time.sleep(2)
                continue
            logger.error(f"Database error: {e}")
            return f"Lỗi thực thi truy vấn: {e}"
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")    
            return f"Lỗi thực thi truy vấn: {e}"
        finally:
            if 'conn' in locals():
                conn.close()        
    
    return "Không thể truy cập cơ sở dữ liệu sau nhiều lần thử."
# This function should be added to your RAG/core_shop.py file

def extract_product_from_history(chat_id: int, query_text: str, db_path: str = "database/chat_history.db") -> Optional[Dict[str, Any]]:
    """
    Extract product name and price from chat history or current query
    
    Args:
        chat_id: The Telegram chat ID
        query_text: The current query text
        db_path: Path to the chat history database
    
    Returns:
        Dictionary with product_name and price if found, None otherwise
    """
    try:
        # First step: Check the database schema to identify the correct column names
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table schema
        cursor.execute("PRAGMA table_info(chat_history)")
        columns = cursor.fetchall()
        
        # Log the available columns for debugging
        column_names = [col[1] for col in columns]
        logger.info(f"Available columns in chat_history table: {column_names}")
        
        # Determine which columns to use based on schema
        chat_id_column = None
        bot_response_column = None
        
        # Look for chat_id or similar column
        if 'chat_id' in column_names:
            chat_id_column = 'chat_id'
        elif 'user_id' in column_names:
            chat_id_column = 'user_id'
        
        # Look for bot_response or similar column
        if 'bot_response' in column_names:
            bot_response_column = 'bot_response'
        elif 'response' in column_names:
            bot_response_column = 'response'
        elif 'answer' in column_names:
            bot_response_column = 'answer'
        
        # If we can't find appropriate columns, use a more generic approach
        if not chat_id_column or not bot_response_column:
            # Get the latest responses without filtering by chat_id
            cursor.execute(f"SELECT * FROM chat_history LIMIT 10")
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                logger.warning("No records found in chat history")
                return None
            
            # Try to extract a product from any response text
            for row in rows:
                for cell in row:
                    if isinstance(cell, str) and len(cell) > 10:  # Look for text fields
                        product_info = extract_product_info_from_text(cell)
                        if product_info:
                            logger.info(f"Extracted product info from chat history: {product_info}")
                            return product_info
        else:
            # Use the identified columns to query chat history
            cursor.execute(
                f"SELECT {bot_response_column} FROM chat_history WHERE {chat_id_column} = ? ORDER BY timestamp DESC LIMIT 5",
                (chat_id,)
            )
            
            responses = cursor.fetchall()
            conn.close()
            
            # Check each response for product information
            for response in responses:
                if response and response[0]:
                    product_info = extract_product_info_from_text(response[0])
                    if product_info:
                        logger.info(f"Extracted product info from chat history: {product_info}")
                        return product_info
        
        # If nothing found in history, check the current query
        product_info = extract_product_info_from_text(query_text)
        if product_info:
            logger.info(f"Extracted product info from current query: {product_info}")
            return product_info
            
        # If we get here, return a default test product for development
        logger.warning("No product information found, returning test product")
        return {
            "product_name": "Sản phẩm mặc định",
            "price": 10000
        }
    
    except Exception as e:
        logger.error(f"Error extracting product from history: {str(e)}")
        # Return a default for testing
        return {
            "product_name": "Sản phẩm mặc định",
            "price": 10000
        }
def extract_product_info_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract product name and price from text using regex patterns
    
    Args:
        text: The text to extract information from
    
    Returns:
        Dictionary with product_name and price if found, None otherwise
    """
    # Simple pattern to match product name and price
    import re
    
    # Pattern to match Vietnamese prices with various formats
    price_patterns = [
        r'(\d{1,3}(?:[,.]\d{3})*)\s*(?:VND|đồng|vnđ|đ|k)',  # 50,000 VND, 50.000đ
        r'giá\s*(?:là|:)?\s*(\d{1,3}(?:[,.]\d{3})*)',  # giá là 50,000
        r'(?:giá|phí)\s*(\d{1,3}(?:[,.]\d{3})*)'  # giá 50,000
    ]
    
    product_name = None
    price = None
    
    # Try to find a price in the text
    for pattern in price_patterns:
        matches = re.search(pattern, text, re.IGNORECASE)
        if matches:
            price_str = matches.group(1).replace('.', '').replace(',', '')
            price = int(price_str)
            
            # Extract product name from context around the price
            sentence = next((s for s in text.split('.') if matches.group(0) in s), '')
            words = sentence.split()
            price_index = -1
            
            for i, word in enumerate(words):
                if price_str in word:
                    price_index = i
                    break
            
            if price_index > 0:
                # Simple approach: take a few words before the price as product name
                product_words = words[max(0, price_index-5):price_index]
                if product_words:
                    product_name = ' '.join(product_words)
            break
    
    # If we found both a product name and price, return them
    if product_name and price:
        return {
            'product_name': product_name,
            'price': price
        }
    
    # If we only found a price, use a generic product name
    if price:
        return {
            'product_name': 'Sản phẩm',
            'price': price
        }
    
    return None


def format_markdown_table(columns, results):
    if not columns or not results:
        return "Không có dữ liệu trả về."
    
    header = "| " + " | ".join(columns) + " |"
    separator = "|-" + "-|-".join(["-" * len(col) for col in columns]) + "-|"
    
    rows = []
    for row in results:
        formatted_row = []
        for value in row:
            if isinstance(value, bytes):
                formatted_value = "<BLOB>"
            elif value is None:
                formatted_value = "NULL"
            else:
                formatted_value = str(value)
            formatted_row.append(formatted_value)
        rows.append("| " + " | ".join(formatted_row) + " |")
    
    return "\n".join([header, separator] + rows)

def display_results(columns, results):
    if not columns or not results:
        print("Không có kết quả")
        return
        
    print("\nKết quả truy vấn:")
    print("=" * 50)
    print(" | ".join(columns))
    print("-" * 50)
    
    for row in results:
        formatted_row = [str(value) if not isinstance(value, bytes) else "<BLOB>" for value in row]
        print(" | ".join(formatted_row))

if __name__ == "__main__":
    DB_NAME = "../database/data.db"
    question = "giá của mít sấy giòn 200gr DaLaVi"
    
    # Generate SQL query using the API
    query = rag_query(question)
    if query:
        print(f"\nGenerated Query:\n{query}\n")
        table = execute_query(DB_NAME, query)
        print(table)
    else:
        print("Không thể tạo được câu query")