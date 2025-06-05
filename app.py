from flask import Flask, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv
from telegram import Bot
import uuid
from datetime import datetime
import asyncio

load_dotenv()

app = Flask(__name__)

# Конфигурация
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

bot = Bot(token=TELEGRAM_TOKEN)

async def send_to_telegram(filepath, user_info):
    try:
        caption = (
            f"Новый посетитель:\n"
            f"IP: {user_info['ip']}\n"
            f"User-Agent: {user_info['user_agent']}\n"
            f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        await bot.send_photo(
            chat_id=TELEGRAM_CHAT_ID,
            photo=open(filepath, 'rb'),
            caption=caption
        )
        return True
    except Exception as e:
        print(f"Ошибка при отправке в Telegram: {e}")
        return False

def get_client_info():
    return {
        'ip': request.headers.get('X-Forwarded-For', request.remote_addr),
        'user_agent': request.headers.get('User-Agent', 'Неизвестно'),
        'referrer': request.headers.get('Referer', 'Прямой заход')
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'photo' not in request.files:
        return jsonify({'error': 'Фото не получено'}), 400
    
    photo = request.files['photo']
    if photo.filename == '':
        return jsonify({'error': 'Пустой файл'}), 400
    
    try:
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        photo.save(filepath)
        
        user_info = get_client_info()
        
        # Запускаем асинхронную задачу в отдельном потоке
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(send_to_telegram(filepath, user_info))
        loop.close()
        
        if not success:
            return jsonify({'error': 'Ошибка отправки в Telegram'}), 500
        
        return jsonify({
            'success': True,
            'photo_url': f'/static/uploads/{filename}'
        })
    except Exception as e:
        return jsonify({'error': f'Внутренняя ошибка сервера: {str(e)}'}), 500

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except FileNotFoundError:
        return jsonify({'error': 'Файл не найден'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
