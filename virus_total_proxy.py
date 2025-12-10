from flask import Flask, request, jsonify, render_template_string
import requests
import threading
import os
import time

app = Flask(__name__)

VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")

if not VIRUSTOTAL_API_KEY:
    raise RuntimeError("Не задан VIRUSTOTAL_API_KEY в переменных окружения")

scan_results = {}

# Главная страница — Mini App
@app.route('/')
def index():
    html = '''
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🛡 Leo Aide — Проверка ссылок</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; background: #f7f7f7; }
            .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; text-align: center; }
            input[type="url"] { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; font-size: 16px; }
            button { background: #0088cc; color: white; border: none; padding: 12px 24px; font-size: 16px; border-radius: 8px; cursor: pointer; }
            button:hover { background: #0066aa; }
            #result { margin-top: 20px; padding: 15px; border-radius: 8px; display: none; }
            .malicious { background: #ffebee; color: #c62828; }
            .clean { background: #e8f5e9; color: #2e7d32; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛡 Проверка ссылки</h1>
            <input type="url" id="url" placeholder="Введите URL, например: https://example.com" required>
            <button onclick="scan()">Проверить</button>
            <div id="result"></div>
        </div>

        <script>
            async function scan() {
                const url = document.getElementById('url').value;
                const resultDiv = document.getElementById('result');
                if (!url) {
                    resultDiv.innerHTML = 'Введите корректный URL';
                    resultDiv.className = 'malicious';
                    resultDiv.style.display = 'block';
                    return;
                }

                resultDiv.innerHTML = 'Сканирование запущено...';
                resultDiv.className = 'clean';
                resultDiv.style.display = 'block';

                try {
                    const resp = await fetch('/scan/url', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ url: url })
                    });
                    const data = await resp.json();
                    if (data.scan_id) {
                        pollResult(data.scan_id);
                    } else {
                        resultDiv.innerHTML = 'Ошибка: ' + (data.error || 'Неизвестная ошибка');
                        resultDiv.className = 'malicious';
                    }
                } catch (e) {
                    resultDiv.innerHTML = 'Ошибка сети: ' + e.message;
                    resultDiv.className = 'malicious';
                }
            }

            function pollResult(scan_id) {
                const resultDiv = document.getElementById('result');
                const interval = setInterval(async () => {
                    const resp = await fetch(`/scan/result/${scan_id}`);
                    const data = await resp.json();
                    if (data.status === 'completed') {
                        clearInterval(interval);
                        if (data.is_malicious) {
                            resultDiv.innerHTML = `
                                ❌ Вредоносная ссылка!<br>
                                <b>Найдено угроз:</b> ${data.positives} из ${data.total}
                            `;
                            resultDiv.className = 'malicious';
                        } else {
                            resultDiv.innerHTML = `
                                ✅ Ссылка безопасна!<br>
                                <b>Проверено:</b> ${data.total} антивирусов
                            `;
                            resultDiv.className = 'clean';
                        }
                    } else if (data.status === 'timeout') {
                        clearInterval(interval);
                        resultDiv.innerHTML = 'Время ожидания истекло';
                        resultDiv.className = 'malicious';
                    }
                }, 3000);
            }
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/scan/url', methods=['POST'])
def scan_url():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL не указан"}), 400

    vt_url = 'https://www.virustotal.com/vtapi/v2/url/scan'
    params = {'apikey': VIRUSTOTAL_API_KEY, 'url': url}
    try:
        response = requests.post(vt_url, data=params)
        result = response.json()
        if result.get('response_code') != 1:
            return jsonify({"error": result.get('verbose_msg', 'Ошибка сканирования')}), 400

        scan_id = result['scan_id']
        threading.Thread(target=poll_result, args=(scan_id, url), daemon=True).start()

        return jsonify({"scan_id": scan_id, "message": "Сканирование запущено"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/scan/result/<scan_id>', methods=['GET'])
def get_result(scan_id):
    result = scan_results.get(scan_id)
    if result is None:
        return jsonify({"status": "processing"}), 202
    return jsonify(result), 200

def poll_result(scan_id, url):
    vt_url = 'https://www.virustotal.com/vtapi/v2/url/report'
    params = {'apikey': VIRUSTOTAL_API_KEY, 'resource': scan_id}
    for _ in range(20):
        try:
            response = requests.get(vt_url, params=params)
            result = response.json()
            if result.get('response_code') == 1:
                positives = result.get('positives', 0)
                total = result.get('total', 0)
                is_malicious = positives > 0

                scan_results[scan_id] = {
                    "status": "completed",
                    "is_malicious": is_malicious,
                    "positives": positives,
                    "total": total,
                    "url": url,
                    "scan_id": scan_id
                }
                return
        except:
            pass
        time.sleep(15)
    scan_results[scan_id] = {"status": "timeout"}

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
