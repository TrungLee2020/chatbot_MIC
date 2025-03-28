import aiohttp

from config import LLM_URL, CHATBOT_MODEL, CHATBOT_TEMPERATURE, CHATBOT_MAX_TOKENS
from src.utils import logger
from src.core.Prompts import CHAT_PROMPT, CHROMADB_PROMPT_TEMPLATE


async def generate_answer(
        question: str,
        context: str = "",
        db_data: str = "",
        chroma_data: str = "",
        prompt_template: str = "default"
) -> str:
    """
    Generate answer using LLM API
    """
    try:
        # Kết hợp nguồn dữ liệu cho context
        knowledge_parts = []
        if db_data:
            knowledge_parts.append(f"Thông tin từ cơ sở dữ liệu:\n{db_data}")

        if chroma_data:
            knowledge_parts.append(f"Thông tin từ tài liệu:\n{chroma_data}")

        knowledge_context = "\n\n".join(knowledge_parts)

        # Log ngắn gọn hơn
        if knowledge_context:
            logger.info(f"Knowledge context length: {len(knowledge_context)} chars")
            logger.debug(f"Knowledge context: {knowledge_context}")
        # Chuẩn bị prompt dựa trên template được chọn
        if prompt_template == "chromadb_based":
            formatted_prompt = CHROMADB_PROMPT_TEMPLATE.format(
                question=question,
                knowledge_context=knowledge_context,
                context=context
            )
        else:
            # Sử dụng prompt mặc định
            formatted_prompt = CHAT_PROMPT.format(
                context=context,
                question=question,
                table=knowledge_context
            )

        # Chuẩn bị payload cho LLM API
        payload = {
            "model": CHATBOT_MODEL,
            "prompt": formatted_prompt,
            "stream": False,
            "options": {
                "temperature": CHATBOT_TEMPERATURE,
                "num_predict": CHATBOT_MAX_TOKENS,
            }
        }

        # Xác định API endpoint
        base_url = LLM_URL.rstrip('/')
        api_url = f"{base_url}/api/generate"
        if base_url.endswith('/v1'):
            api_url = f"{base_url[:-3]}/api/generate"  # Loại bỏ '/v1' và thêm path

        logger.info(f"Calling LLM API at {api_url}")

        # Gọi LLM API với timeout hợp lý
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, timeout=30) as response:
                if response.status == 200:
                    result = await response.json()
                    answer = result.get("response")
                    if answer:
                        return answer
                    else:
                        logger.error(f"Unexpected response structure: {result}")
                        return "Xin lỗi, tôi không thể xử lý câu trả lời từ hệ thống AI."
                else:
                    error_text = await response.text()
                    logger.error(f"LLM API error {response.status}: {error_text[:200]}")
                    return f"Xin lỗi, tôi không thể trả lời câu hỏi của bạn lúc này (Mã lỗi: {response.status})."



    except aiohttp.ClientError as e:
        logger.error(f"API connection error: {str(e)}")
        return "Xin lỗi, tôi không thể kết nối tới dịch vụ AI. Vui lòng thử lại sau."

    except Exception as e:
        logger.error(f"Error generating answer: {str(e)}")
        return "Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi của bạn. Vui lòng thử lại sau."