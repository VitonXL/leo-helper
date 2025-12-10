# vt-server/server.py
# Прокси для VirusTotal API
# Запускается на Render как Web Service

from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Получаем API-ключ из переменных окружения
VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")

if not VIRUSTOTAL_API_KEY:
    raise RuntimeError("Не задан VIRUSTOTAL_API_KEY в переменных окружения")

# --- Маршрут: проверка ссылки ---
@app.route('/scan/url', methods=['POST'])
def scan_url():
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL не указан"}), 400

    # Отправляем URL на VirusTotal
    vt_url = "https://www.virustotal.com/api/v3/urls"
    headers = {
        "Authorization": f"Bearer {VIRUSTOTAL_API_KEY}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = requests.post(vt_url, headers=headers, data={"url": url})

    if response.status_code != 200:
        return jsonify({"error": "Ошибка при отправке на VirusTotal", "details": response.text}), 500

    # Возвращаем scan_id
    scan_id = response.json()["data"]["id"]
    return jsonify({"scan_id": scan_id})

# --- Маршрут: получение результата ---
@app.route('/scan/result', methods=['GET'])
def scan_result():
    scan_id = request.args.get('id')
    if not scan_id:
        return jsonify({"error": "scan_id не указан"}), 400

    vt_url = f"https://www.virustotal.com/api/v3/analyses/{scan_id}"
    headers = {"Authorization": f"Bearer {VIRUSTOTAL_API_KEY}"}
    response = requests.get(vt_url, headers=headers)

    if response.status_code != 200:
        return jsonify({"error": "Не удалось получить результат", "details": response.text}), 500

    data = response.json()
    stats = data["data"]["attributes"]["stats"]
    malicious = stats.get("malicious", 0)
    total = sum(stats.values())

    return jsonify({
        "malicious": malicious,
        "total": total,
        "safe": malicious == 0,
        "stats": stats
    })

# --- Главная страница (статус) ---
@app.route('/')
def home():
    return jsonify({
        "status": "VirusTotal Proxy API is running",
        "endpoints": {
            "POST /scan/url": "Отправить ссылку на проверку",
            "GET /scan/result?id=...": "Получить результат"
        }
    }), 200

# Запуск сервера (для Render)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
