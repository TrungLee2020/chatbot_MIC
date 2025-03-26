from typing import List, Tuple, Union

from config import CHROMA_DB_PATH
from src.manager.Chroma_Manager import ChromaDBManager

# Tạo instance của ChromaDBManager
db_manager = ChromaDBManager(CHROMA_DB_PATH)

# Các hàm export để tương thích với mã nguồn cũ
def is_initialized() -> bool:
    """Kiểm tra xem ChromaDB đã được khởi tạo thành công chưa"""
    return db_manager.is_initialized()

async def search_documents(query: str, limit: int = 3, return_scores: bool = False) -> Union[
    str, Tuple[str, List[float]]]:
    """
    Tìm kiếm tài liệu trong ChromaDB
    """
    return await db_manager.search_documents(query, limit, return_scores)

async def process_pdf(pdf_path: str, file_name: str) -> str:
    """
    Xử lý PDF và thêm vào ChromaDB
    """
    return await db_manager.process_pdf(pdf_path, file_name)

def delete_documents(source: str = None) -> str:
    """
    Xóa tài liệu từ ChromaDB
    """
    return db_manager.delete_documents(source)