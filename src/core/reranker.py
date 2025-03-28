import logging
from typing import List, Dict, Any

from sentence_transformers import SentenceTransformer, util

from src.utils import setup_logger

logger = setup_logger("src", "logs/src.log")


class DocumentReranker:
    """Lớp xử lý reranking cho các kết quả tìm kiếm từ ChromaDB"""

    def __init__(self, model_name: str = "Alibaba-NLP/gte-multilingual-reranker-base"):
        """
        Khởi tạo reranker
        """
        self.model_name = model_name
        self.reranker = None
        self.initialize()

    def initialize(self) -> bool:
        """
        Khởi tạo model reranker với SentenceTransformer
        """
        try:
            logger.info(f"Khởi tạo reranker với model {self.model_name}")

            self.model = SentenceTransformer(self.model_name, trust_remote_code=True)
            logger.info("SentenceTransformer khởi tạo thành công")

            # Kiểm tra model đã tải thành công chưa
            test_embedding = self.model.encode("Test sentence")
            logger.info(f"Kiểm tra model OK, embedding shape: {test_embedding.shape}")

            return True
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo reranker: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def is_initialized(self) -> bool:
        """
        Kiểm tra xem reranker đã được khởi tạo thành công chưa
        """
        return hasattr(self, 'model') and self.model is not None

    def rerank(self, query: str, documents: List[Dict[str, Any]],
               top_n: int = None) -> List[Dict[str, Any]]:
        """
        Sắp xếp lại các kết quả dựa trên reranker
        """
        if not self.is_initialized():
            logger.warning("Reranker chưa được khởi tạo, trả về kết quả gốc")
            return documents[:top_n] if top_n is not None else documents

        if not documents:
            logger.warning("Không có tài liệu để rerank")
            return []

        try:
            # Mã hóa query
            query_embedding = self.model.encode(query, convert_to_tensor=True)

            # Mã hóa documents
            docs_text = [doc['document'] for doc in documents]
            docs_embeddings = self.model.encode(docs_text, convert_to_tensor=True)

            # Tính toán điểm tương đồng
            similarity_scores = util.cos_sim(query_embedding, docs_embeddings)[0].tolist()

            # Thêm điểm vào documents
            for i, doc in enumerate(documents):
                doc['rerank_score'] = similarity_scores[i]

            # Sắp xếp kết quả theo điểm rerank
            reranked_docs = sorted(documents, key=lambda x: x['rerank_score'], reverse=True)

            # Giới hạn số lượng kết quả
            if top_n is not None:
                reranked_docs = reranked_docs[:top_n]

            logger.info(f"Rerank thành công {len(reranked_docs)} tài liệu")
            return reranked_docs

        except Exception as e:
            logger.error(f"Lỗi khi thực hiện reranking: {str(e)}")
            # Trả về kết quả gốc nếu có lỗi
            return documents[:top_n] if top_n is not None else documents