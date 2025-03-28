import os
import logging
from typing import List
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import chromadb
from chromadb.utils import embedding_functions

# Cấu hình logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Đường dẫn đến ChromaDB
CHROMA_DB_PATH = "data/chroma_db"

# Khởi tạo ChromaDB
try:
    logger.info(f"Initializing ChromaDB at {CHROMA_DB_PATH}")
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    logger.info("ChromaDB client initialized successfully")

    # Khởi tạo embedding function: sentence-transformers/all-MiniLM-L6-v2
    # Alibaba-NLP/gte-multilingual-base
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="Alibaba-NLP/gte-multilingual-base",
        trust_remote_code=True
    )
    logger.info("Embedding function initialized successfully")

    # Tạo hoặc lấy collection
    collection = chroma_client.get_or_create_collection(
        name="knowledge_base",
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"}  # Sử dụng cosine similarity
    )
    logger.info(f"Collection 'knowledge_base' created or retrieved with {collection.count()} documents")

except Exception as e:
    logger.error(f"Error initializing ChromaDB: {str(e)}")
    raise e


def process_and_store_md_file(file_path: str) -> None:
    """Xử lý và lưu một file .md vào ChromaDB."""
    try:
        # Kiểm tra xem file có tồn tại và là file .md không
        if not os.path.exists(file_path):
            logger.warning(f"Skipping {file_path}: File does not exist.")
            return

        if not file_path.endswith(".md"):
            logger.warning(f"Skipping {file_path}: Not a Markdown file.")
            return

        # Đọc file .md
        loader = TextLoader(file_path, encoding="utf-8")
        logger.info(f"Loading document from {file_path}.")
        pages = loader.load()
        logger.info(f"Loaded {len(pages)} pages from {file_path}.")

        # Chia nhỏ văn bản thành các đoạn
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,  # Kích thước mỗi đoạn
            chunk_overlap=100  # Độ chồng lấp giữa các đoạn
        )
        chunks = text_splitter.split_documents(pages)
        logger.info(f"Split document into {len(chunks)} chunks.")

        # Lưu các đoạn vào ChromaDB
        for i, chunk in enumerate(chunks):
            document_id = f"{os.path.basename(file_path)}_{i}"

            try:
                collection.add(
                    ids=[document_id],
                    documents=[chunk.page_content],
                    metadatas=[{
                        "source": os.path.basename(file_path),
                        "part": i + 1,
                        "total_parts": len(chunks)
                    }]
                )
                logger.info(f"Added chunk {i + 1}/{len(chunks)} with ID {document_id}")
            except Exception as chunk_error:
                logger.error(f"Error adding chunk {i + 1} from {file_path}: {str(chunk_error)}")

        logger.info(f"Stored {len(chunks)} chunks from {file_path} into ChromaDB.")

        # Xác nhận số lượng đoạn đã lưu
        current_count = collection.count()
        logger.info(f"Current total chunks in ChromaDB: {current_count}")
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


def process_directory(directory_path: str) -> None:
    """Trường hợp 1: Xử lý tất cả file .md trong một thư mục."""
    try:
        if not os.path.isdir(directory_path):
            logger.error(f"{directory_path} is not a valid directory.")
            return

        # Liệt kê tất cả các file .md trong thư mục
        md_files = [f for f in os.listdir(directory_path) if f.endswith(".md")]

        if not md_files:
            logger.warning(f"No .md files found in {directory_path}.")
            return

        logger.info(f"Found {len(md_files)} markdown files in directory.")

        # Xử lý từng file
        for i, md_file in enumerate(md_files):
            full_path = os.path.join(directory_path, md_file)
            logger.info(f"Processing file {i + 1}/{len(md_files)}: {md_file}")
            process_and_store_md_file(full_path)

        # Kiểm tra tổng số đoạn đã lưu
        stored_count = collection.count()
        logger.info(f"Total chunks stored in ChromaDB: {stored_count}")
    except Exception as e:
        logger.error(f"Error processing directory {directory_path}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


def process_file_list(file_list: List[str]) -> None:
    """Trường hợp 2: Xử lý danh sách các file .md được chỉ định."""
    try:
        if not file_list:
            logger.warning("No files provided to process.")
            return

        logger.info(f"Processing {len(file_list)} specified files.")

        # Xử lý từng file trong danh sách
        for i, file_path in enumerate(file_list):
            logger.info(f"Processing file {i + 1}/{len(file_list)}: {file_path}")
            process_and_store_md_file(file_path)

        # Kiểm tra tổng số đoạn đã lưu
        stored_count = collection.count()
        logger.info(f"Total chunks stored in ChromaDB: {stored_count}")
    except Exception as e:
        logger.error(f"Error processing file list: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


def verify_collection_contents() -> None:
    """Xác minh dữ liệu trong collection"""
    try:
        # Đếm số lượng đoạn
        doc_count = collection.count()
        logger.info(f"Collection contains {doc_count} documents")

        if doc_count == 0:
            logger.warning("Collection is empty. No documents have been added.")
            return

        # Lấy mẫu các tài liệu để kiểm tra
        sample = collection.get(limit=3)
        logger.info(f"Sample document IDs: {sample['ids']}")

        # Kiểm tra chức năng tìm kiếm
        results = collection.query(
            query_texts=["test query"],
            n_results=2,
            include=['documents', 'metadatas', 'distances']
        )
        logger.info(f"Test query returned {len(results['documents'][0])} results")

    except Exception as e:
        logger.error(f"Error verifying collection: {str(e)}")


def main():
    # Lựa chọn giữa hai trường hợp
    print("Chọn trường hợp xử lý:")
    print("1. Xử lý tất cả file .md trong một thư mục")
    print("2. Xử lý danh sách file .md do bạn cung cấp")
    print("3. Xác minh nội dung hiện có trong collection")

    choice = input("Nhập lựa chọn (1, 2 hoặc 3): ").strip()

    if choice == "1":
        # Trường hợp 1: Xử lý thư mục
        directory_path = input("Nhập đường dẫn thư mục chứa các file .md: ").strip()
        if directory_path:
            process_directory(directory_path)
        else:
            logger.error("Bạn chưa nhập đường dẫn thư mục.")

    elif choice == "2":
        # Trường hợp 2: Xử lý danh sách file
        print("Nhập danh sách đường dẫn file .md (nhập từng đường dẫn, để trống và nhấn Enter để kết thúc):")
        file_list = []
        while True:
            file_path = input("Đường dẫn file .md (để trống để kết thúc): ").strip()
            if not file_path:
                break
            file_list.append(file_path)

        if file_list:
            process_file_list(file_list)
        else:
            logger.warning("Không có file nào được cung cấp để xử lý.")

    elif choice == "3":
        # Xác minh nội dung hiện có
        verify_collection_contents()

    else:
        logger.error("Lựa chọn không hợp lệ. Vui lòng chọn 1, 2 hoặc 3.")


if __name__ == "__main__":
    main()