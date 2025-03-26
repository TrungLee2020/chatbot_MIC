from flask import Flask, request, jsonify
import google.generativeai as genai
from functools import wraps
import os
from dotenv import load_dotenv
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
app = Flask(__name__)

API_KEY = os.getenv("API_KEY")
CHAT_MODEL = os.getenv("CHAT_MODEL")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(CHAT_MODEL)
chat_sessions = {}


# def require_api_key(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         api_key = request.headers.get('X-API-Key')
#         logger.info(f"Received API Key: {api_key}")
#         logger.info(f"Expected API Key: {GOOGLE_API_KEY}")
#         if not api_key or api_key != GOOGLE_API_KEY:
#             return jsonify({'error': 'Invalid or missing API key'}), 401
#         return f(*args, **kwargs)
#     return decorated_function

@app.route('/api/generate', methods=['POST'])
# @require_api_key
def generate_text():
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({'error': 'Prompt is required'}), 400

        prompt = data['prompt']
        logger.info(f"Generating text for prompt: {prompt}")

        response = model.generate_content(prompt)
        return jsonify({
            'success': True,
            'response': response.text
        })
    except genai.GenerationError as e:
        logger.error(f"Generation error: {str(e)}")
        return jsonify({'success': False, 'error': f"Generation error: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error in generate_text: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Giữ nguyên phần code còn lại (chat endpoint, etc.)

if __name__ == "__main__":
    app.run(debug=True, host='127.0.0.1', port=5000)
