import chromadb
from chromadb.utils import embedding_functions
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Dict, Any, Tuple, Union

from src.utils import setup_logger
from config import EMBEDDINGS_MODEL

logger = setup_logger("modules", "logs/modules.log")

class ChromaDBManager:
    """Quản lý ChromaDB và các thao tác liên quan"""

    def __init__(self, db_path: str, collection_name: str = "knowledge_base"):
        """
        Khởi tạo ChromaDB Manager
        """
        self.db_path = db_path
        self.collection_name = collection_name
        self.chroma_client = None
        self.knowledge_collection = None
        self.embedding_function = None

        self.initialize()

    def initialize(self) -> bool:
        """
        Khởi tạo ChromaDB và embedding function
        """
        try:
            logger.info(f"Khởi tạo ChromaDB tại {self.db_path}")
            self.chroma_client = chromadb.PersistentClient(path=self.db_path)
            logger.info("ChromaDB khởi tạo thành công")

            # Khởi tạo embedding function
            try:
                self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=EMBEDDINGS_MODEL
                )
                logger.info("Embedding function khởi tạo thành công")
            except Exception as e:
                logger.error(f"Lỗi khởi tạo embedding model: {str(e)}")
                raise

            # Tạo hoặc lấy collection
            try:
                self.knowledge_collection = self.chroma_client.get_or_create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(
                    f"Collection '{self.collection_name}' đã được tạo hoặc lấy thành công với {self.knowledge_collection.count()} tài liệu")
                return True
            except Exception as e:
                logger.error(f"Lỗi khi tạo collection '{self.collection_name}': {str(e)}")
                self.knowledge_collection = None
                return False

        except Exception as e:
            logger.error(f"Lỗi khởi tạo ChromaDB: {str(e)}")
            self.chroma_client = None
            self.knowledge_collection = None
            return False

    def is_initialized(self) -> bool:
        """Kiểm tra xem ChromaDB đã được khởi tạo thành công chưa"""
        return self.knowledge_collection is not None

    async def search_documents(self, query: str, limit: int = 3, return_scores: bool = False,
                               threshold: float = 0.5) -> Union[str, Tuple[str, List[float]]]:
        """
        Tìm kiếm tài liệu trong ChromaDB
        """
        if not self.is_initialized():
            logger.warning("ChromaDB chưa được khởi tạo, bỏ qua tìm kiếm")
            return ("", []) if return_scores else ""

        logger.info(f"Tìm kiếm cho câu truy vấn: '{query}'")
        logger.info(f"Collection chứa {self.knowledge_collection.count()} tài liệu")

        # Nếu collection trống, trả về sớm
        if self.knowledge_collection.count() == 0:
            logger.warning("Collection trống, không có tài liệu để tìm kiếm")
            return ("Collection trống. Vui lòng thêm tài liệu trước.",
                    []) if return_scores else "Collection trống. Vui lòng thêm tài liệu trước."

        try:
            # Thực hiện tìm kiếm
            results = self.knowledge_collection.query(
                query_texts=[query],
                n_results=limit,
                include=['documents', 'metadatas', 'distances']
            )

            # Kiểm tra kết quả trống
            if not results or not results.get('documents') or not results['documents'][0]:
                logger.info("Không tìm thấy tài liệu phù hợp trong ChromaDB")
                return ("Không tìm thấy tài liệu phù hợp.", []) if return_scores else "Không tìm thấy tài liệu phù hợp."

            docs = results['documents'][0]
            metadatas = results['metadatas'][0]
            distances = results['distances'][0]

            # Chuyển đổi khoảng cách thành điểm tương đồng
            relevance_scores = [1 - dist for dist in distances]

            logger.info(f"Tìm thấy {len(docs)} kết quả với điểm: {relevance_scores}")

            # Lọc kết quả dựa trên ngưỡng
            filtered_results = [
                                   (doc, meta, score)
                                   for doc, meta, score in zip(docs, metadatas, relevance_scores)
                                   if score >= threshold
                               ][:limit]

            if not filtered_results:
                logger.info(f"Không tìm thấy tài liệu trên ngưỡng {threshold}")
                return (f"Không tìm thấy tài liệu phù hợp với ngưỡng {threshold}.",
                        []) if return_scores else f"Không tìm thấy tài liệu phù hợp với ngưỡng {threshold}."

            # Định dạng kết quả
            formatted_results = self._format_search_results(filtered_results)
            final_scores = [score for _, _, score in filtered_results]

            avg_score = sum(final_scores) / len(final_scores) if final_scores else 0
            logger.info(f"Tìm thấy {len(filtered_results)} tài liệu với điểm trung bình: {avg_score:.4f}")

            return (formatted_results, final_scores) if return_scores else formatted_results

        except Exception as e:
            logger.error(f"Lỗi khi tìm kiếm ChromaDB: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return (f"Lỗi khi tìm kiếm: {str(e)}", []) if return_scores else f"Lỗi khi tìm kiếm: {str(e)}"

    def _format_search_results(self, results: List[Tuple[str, Dict[str, Any], float]]) -> str:
        """
        Định dạng kết quả tìm kiếm
        """
        formatted_results = ""
        for i, (doc, meta, score) in enumerate(results):
            source = meta.get('source', 'Unknown')
            page = meta.get('page', meta.get('part', 'N/A'))
            formatted_results += f"### Document {i + 1}: {source} (Page {page}) [Score: {score:.4f}]\n{doc}\n\n"
        return formatted_results

    async def process_pdf(self, pdf_path: str, file_name: str,
                          chunk_size: int = 1000, chunk_overlap: int = 100) -> str:
        """
        Xử lý PDF và thêm vào ChromaDB
        """
        if not self.is_initialized():
            logger.error("ChromaDB chưa được khởi tạo. Không thể xử lý PDF.")
            return "ChromaDB không sẵn sàng. Không thể xử lý PDF lúc này."

        try:
            # Đọc file PDF
            loader = PyPDFLoader(pdf_path)
            pages = loader.load()

            # Chia tài liệu thành các chunk
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            chunks = text_splitter.split_documents(pages)

            # Thêm vào ChromaDB
            documents = []
            metadatas = []
            ids = []

            for i, chunk in enumerate(chunks):
                document_id = f"{file_name.replace('.pdf', '')}-chunk-{i}"
                documents.append(chunk.page_content)
                metadatas.append({"source": file_name, "page": chunk.metadata.get("page", i + 1)})
                ids.append(document_id)

            # Thêm tất cả các chunk cùng một lúc để tăng hiệu suất
            if documents:
                self.knowledge_collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )

            logger.info(f"Đã xử lý và lưu trữ {len(chunks)} chunk từ {file_name}")
            return f"Đã xử lý {len(chunks)} đoạn văn bản từ file {file_name}. Bạn có thể đặt câu hỏi về nội dung của tài liệu này."

        except Exception as e:
            logger.error(f"Lỗi khi xử lý PDF: {str(e)}")
            return f"Lỗi khi xử lý file PDF: {str(e)}"

    def delete_documents(self, source: str = None) -> str:
        """
        Xóa tài liệu từ ChromaDB
        """
        if not self.is_initialized():
            return "ChromaDB không sẵn sàng."

        try:
            if source:
                # Lấy ID cần xóa
                results = self.knowledge_collection.get(
                    where={"source": source}
                )
                if results and results.get('ids'):
                    self.knowledge_collection.delete(
                        ids=results['ids']
                    )
                    return f"Đã xóa {len(results['ids'])} chunk từ nguồn {source}."
                return f"Không tìm thấy tài liệu từ nguồn {source}."
            else:
                # Xóa tất cả
                self.knowledge_collection.delete()
                return "Đã xóa tất cả tài liệu từ cơ sở dữ liệu."

        except Exception as e:
            logger.error(f"Lỗi khi xóa tài liệu: {str(e)}")
            return f"Lỗi khi xóa tài liệu: {str(e)}"