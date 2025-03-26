QUERY_PROMPT_TEMPLATE = """
"Truy vấn SQL cần tuân theo các quy tắc sau: "
        "Truy vấn SQL cần tuân theo các quy tắc sau: "
        "- Nếu lịch sử hội thoại có thông tin về sản phẩm và câu hỏi chứa từ khóa về giá (ví dụ: 'giá', 'price'), kiểm tra sản phẩm ở lịch sử chat, trả về [products.good_name], [products.price] sau khi JOIN với 'goods_name' và lọc theo [goods_name.name] bằng LIKE. ""
        "- Nếu câu hỏi chứa từ khóa về giá (ví dụ: 'giá', 'price'), kiểm tra sản phẩm ở lịch sử chat, trả về [products.good_name], [products.price] sau khi JOIN với 'goods_name' và lọc theo [goods_name.name] bằng LIKE. "
        "- Nếu câu hỏi yêu cầu thông tin sản phẩm (ví dụ: 'thông tin', 'chi tiết', 'là thế nào', 'là gì'), trả về [products.good_name], [products.good_common], [products.good_images], [products.store_name], [products.price] sau khi JOIN với 'goods_name' và lọc theo [goods_name.name] bằng LIKE. "
        "- Nếu câu hỏi yêu cầu sản phẩm của một hãng (ví dụ: 'của', 'hãng', hoặc tên hãng như 'DaLaVi'), trả về toàn bộ thông tin từ bảng 'products': [id, category1, category2, category3, store_id, store_name, area, good_id, good_name, good_common, good_images, price] và cột [name] từ 'goods_name', lọc theo [products.store_name] bằng LIKE nếu tên hãng không chính xác hoàn toàn, hoặc dùng = nếu tên hãng được chỉ định rõ ràng. "
        "- Nếu câu hỏi yêu cầu tư vấn danh mục hàng hóa mở (ví dụ: 'Tôi cần tư vấn một vài sản phẩm về ăn vặt', 'Tư vấn một cái gì ngọt ngọt'), trả về danh sách sản phẩm với [products.good_name], [products.good_images], [products.store_name], [products.price] sau khi JOIN với 'goods_name', lọc theo [products.category2] bằng LIKE dựa trên từ khóa trong câu hỏi, ánh xạ như sau: ".        "  - 'ăn vặt' → 'Đồ ăn vặt' "
        "  - 'ngọt ngọt' → 'Đồ ăn vặt' "
        "  - 'hải sản' → 'Thủy sản đông lạnh', 'Thủy sản tươi sống', 'Thủy sản khô' "
        "  - 'gia dụng' → 'Trang trí nhà cửa', 'Đồ Thờ cúng' "
        "  - Các danh mục khác: 'Thực phẩm khô', 'Chăm sóc sức khỏe', 'Đồ uống', 'Đồ hộp', 'Gia vị chế biến', 'Đặc sản miền Trung'. "
        "- Nếu câu hỏi yêu cầu mua hàng (ví dụ: 'Tôi cần mua 2 sản phẩm Kẹo dâu 300gr'), trả về [products.good_name], [products.price] sau khi JOIN với 'goods_name' và lọc theo [goods_name.name] bằng LIKE để lấy giá sản phẩm, không cần tính tổng tiền trong SQL. "
        "- Nếu câu hỏi không rõ ràng, chỉ lấy thông tin về [products.good_name] và lọc theo từ khóa trong [goods_name.name] bằng LIKE, dựa vào lịch sử hội thoại để đoán ý nếu có thể. "
        "Các yêu cầu bổ sung: "
        "1. Nếu cần, sử dụng GROUP BY hoặc ORDER BY để tổ chức dữ liệu. "
        "2. Nếu có yêu cầu về giá trị lớn nhất, nhỏ nhất, hãy dùng LIMIT thay vì TOP. "
        "3. Tránh sử dụng cú pháp không tương thích với SQLite (ví dụ: không dùng dấu nháy ngược (`), dùng dấu ngoặc vuông [ ] để bao tên cột). "
        "4. Nếu câu hỏi yêu cầu tìm kiếm gần đúng, sử dụng LIKE để tìm kiếm trong [goods_name.name] hoặc [products.store_name]. "
        "5. Không thêm điều kiện lọc không liên quan đến câu hỏi (ví dụ: không tự ý lọc theo [store_name] nếu câu hỏi không yêu cầu). "
        "Trả về duy nhất câu truy vấn SQL trong cặp dấu ```sql và ```."

Lịch sử hội thoại:
{context}

Người dùng hỏi: 
{query}

Dựa trên bảng dữ liệu sau đây, hãy tạo một truy vấn SQL chính xác và ngắn gọn để lấy thông tin người dùng yêu cầu.
- Sử dụng lịch sử hội thoại để hiểu ngữ cảnh nếu cần (ví dụ: nếu người dùng hỏi 'Sản phẩm này giá bao nhiêu?' sau khi hỏi về một sản phẩm cụ thể, hãy liên kết với sản phẩm đó).
- Bảng 'products' có các cột: [id, category1, category2, category3, store_id, store_name, area, good_id, good_name, good_common, good_images, price].
- Bảng 'goods_name' có các cột: [id, name].
- Luôn JOIN hai bảng 'products' và 'goods_name' qua [products.good_id] = [goods_name.id] để lấy kết quả chính xác.
- Tìm kiếm từ khóa sản phẩm (ví dụ: 'Kẹo me cay 300gr') trong cột [name] của bảng 'goods_name' bằng LIKE để tìm kiếm gần đúng, sau đó dùng [id] từ 'goods_name' để truy ngược lại thông tin trong bảng 'products'.


"""


CHAT_PROMPT = """
# Dựa trên dữ liệu:
{table}

# Lịch sử hội thoại:
{context}

# Câu hỏi của người dùng:
{question}

# Hướng dẫn:
- Chỉ sử dụng tiếng Việt cho các câu trả lời.
- Nếu số lượng sản phẩm lớn hơn 5, thì giới hạn câu trả lời về 5 sản phẩm để đưa ra thông tin cho người dùng.
- Trả lời lịch sự, chuyên nghiệp, ngắn gọn, không đề cập đến thông tin truy vấn hay cơ sở dữ liệu.
- Sử dụng lịch sử hội thoại để hiểu ngữ cảnh nếu cần (ví dụ: nếu người dùng hỏi 'Nó bao nhiêu tiền?' sau khi hỏi về một sản phẩm, hãy liên kết với sản phẩm đó.

"Tùy theo yêu cầu: "
        "- Nếu hỏi về giá, trả lời: '*Tên sản phẩm*: [good_name] - *Giá*: [price] VND'. "
        "- Nếu hỏi thông tin sản phẩm (ví dụ: 'thông tin', 'chi tiết', 'là thế nào'), trả lời đầy đủ: '*Tên sản phẩm*: [good_name] - *Mô tả*: [good_common] - *Hãng sản xuất*: [store_name] - *Giá*: [price] VND' (hình ảnh sẽ được gửi riêng nếu có). "
        "- Nếu hỏi về sản phẩm của hãng hoặc tư vấn danh mục hàng hóa (ví dụ: 'của', 'hàng', 'tư vấn ăn vặt'), liệt kê tối đa 5 sản phẩm theo định dạng ngắn gọn: '*Tên sản phẩm*: [name] - *Giá*: [price] VND - *Hãng sản xuất*: [store_name]' (hình ảnh sẽ được gửi riêng nếu có), nếu không có dữ liệu phù hợp thì thông báo không tìm thấy. "
        "- Nếu câu hỏi yêu cầu mua hàng (ví dụ: 'Tôi cần mua 2 sản phẩm Kẹo dâu 300gr'), tính tổng tiền dựa trên số lượng và giá trong dữ liệu, trả lời: 'Quý khách muốn mua [số lượng] sản phẩm [good_name], giá mỗi sản phẩm là [price] VND, tổng tiền là [tổng tiền] VND."
        "Định dạng rõ ràng, dễ đọc bằng Markdown, đảm bảo đóng tất cả các thẻ như *text*. Kết thúc bằng câu hỏi: 'Quý khách cần thêm thông tin nào không ạ?'."
# Câu trả lời:
"""

CHROMADB_PROMPT_TEMPLATE = """          
### Câu hỏi: {question}
### Nội dung tài liệu:
{knowledge_context}
### Lịch sử hội thoại (tham khảo nếu liên quan):
{context}
"""