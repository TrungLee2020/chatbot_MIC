# Chatbot Trợ lý Thông minh

Chatbot Telegram sử dụng các API xử lý ngôn ngữ tự nhiên, nhận dạng giọng nói và tổng hợp giọng nói để tạo trải nghiệm tương tác tự nhiên.

## Tính năng

- Phân tích và trả lời từ file PDF
- Nhận dạng và phản hồi tin nhắn thoại
- Hỗ trợ gửi câu trả lời bằng giọng nói
- Lưu trữ và truy vấn lịch sử hội thoại

## Cấu trúc dự án

```
📦 project-root
 ┣ 📂 data
 ┃ ┣ 📂 chroma_db        # Dữ liệu ChromaDB
 ┃ ┣ 📂 database         # Dữ liệu cơ sở dữ liệu
 ┃ ┣ 📂 documents        # Tài liệu đầu vào
 ┃ ┗ 📂 logs             # File logs
 ┣ 📂 src
 ┃ ┣ 📂 api              # Các API bên ngoài
 ┃ ┣ 📂 bot              # Logic bot Telegram
 ┃ ┣ 📂 core             # Các chức năng cốt lõi
 ┃ ┣ 📂 db               # Xử lý cơ sở dữ liệu
 ┃ ┣ 📂 document_processing # Xử lý tài liệu
 ┃ ┣ 📂 manager          # Các lớp quản lý
 ┃ ┣ 📄 __init__.py      # File khởi tạo package
 ┃ ┗ 📄 utils.py         # Các tiện ích
 ┣ 📄 1.pdf              # File PDF mẫu
 ┣ 📄 app.py             # Điểm khởi chạy ứng dụng
 ┣ 📄 config.py          # Cấu hình ứng dụng
 ┣ 📄 main_rag.py        # Script chính cho RAG
 ┣ 📄 README.md          # Tài liệu hướng dẫn
 ┣ 📄 requirements.txt   # Danh sách thư viện
 ┣ 📄 stt_api.py         # API chuyển đổi giọng nói sang văn bản
 ┗ 📄 tts_api.py         # API chuyển đổi văn bản sang giọng nói
```

## Cài đặt

### Yêu cầu

- Python 3.10
- Telegram Bot Token (từ BotFather)
- API STT và TTS (đã được cài đặt và chạy)

### Các bước cài đặt

1. Clone repository:
```bash
git clone https://github.com/TrungLee2020/chatbot_MIC.git
cd chatbot_MIC
```

2. Cài đặt các thư viện cần thiết:
```bash
pip install -r requirements.txt
```

3. Tạo file `.env` từ template `.env-example`:
```bash
cp .env-example .env
```

4. Chỉnh sửa file `.env` với thông tin của bạn:
```
TELEGRAM_TOKEN=your_telegram_bot_token_here
...
```

5. Khởi động bot:
```bash
python main_rag.py
python stt_api.py
python tts_api.py
python app.py
```

## Sử dụng

### Lệnh Telegram

- `/start` - Khởi động bot
- `/help` - Hiển thị trợ giúp
- `/history` - Xem lịch sử hội thoại gần đây

### Chức năng

- **Gửi tin nhắn văn bản**: Bot sẽ trả lời dựa trên cơ sở dữ liệu và kiến thức của nó
- **Gửi tin nhắn giọng nói**: Bot sẽ chuyển đổi giọng nói thành văn bản và trả lời
- **Gửi file PDF**: Bot sẽ phân tích và lưu trữ nội dung, sau đó bạn có thể hỏi về nội dung file
- **Nhận phản hồi bằng giọng nói**: Thêm `/voice` vào cuối câu hỏi để nhận phản hồi bằng giọng nói

## Tích hợp API

Bot sử dụng hai API chính:

1. **API STT** (Speech-to-Text):
   - Endpoint: `http://127.0.0.1:5001/api/speech-to-text`
   - Method: POST
   - Input: File âm thanh (ogg, mp3, wav)
   - Output: Văn bản nhận dạng

2. **API TTS** (Text-to-Speech):
   - Endpoint: `http://127.0.0.1:5002/api/text-to-speech`
   - Method: POST
   - Input: Văn bản cần chuyển đổi
   - Output: File âm thanh (mp3)

## Khắc phục sự cố

Nếu gặp vấn đề, hãy kiểm tra:

1. File log tại `logs/chatbot.log`
2. Kết nối đến các API STT và TTS
3. Token Telegram Bot có đúng không
4. Quyền truy cập của ứng dụng vào thư mục `database` và `chroma_db`
