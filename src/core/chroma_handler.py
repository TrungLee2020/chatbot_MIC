from typing import List, Tuple, Union

from config import CHROMA_DB_PATH, USE_RERANKER
from src.manager.Chroma_Manager import ChromaDBManager

from src.utils import setup_logger

logger = setup_logger("src", "logs/src.log")
# Tạo instance của ChromaDBManager
db_manager = ChromaDBManager(CHROMA_DB_PATH)


# Các hàm export để tương thích với mã nguồn cũ
def is_initialized() -> bool:
    """Kiểm tra xem ChromaDB đã được khởi tạo thành công chưa"""
    return db_manager.is_initialized()


async def search_documents(query: str, limit: int = 5, return_scores: bool = False,
                           threshold: float = 0.5, use_reranker: bool = USE_RERANKER) -> Union[
    str, Tuple[str, List[float]]]:
    """
    Tìm kiếm tài liệu trong ChromaDB
    """
    # Sử dụng ngưỡng tìm kiếm phù hợp
    from config import RERANKER_THRESHOLD
    actual_threshold = RERANKER_THRESHOLD if use_reranker else threshold

    # Kiểm tra xem db_manager có thuộc tính reranker không để tránh lỗi
    if use_reranker and not hasattr(db_manager, 'reranker') or db_manager.reranker is None:
        use_reranker = False
        logger.warning("Reranker không sẵn sàng, tắt tính năng reranker")

    return await db_manager.search_documents(
        query, limit, return_scores, actual_threshold, use_reranker)


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