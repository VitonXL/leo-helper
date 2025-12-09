from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

VIRUSTOTAL_API_KEY = "9526a722e91c39d4110eeb29faf75be42f489cd3428a8dcae01fea4485de95b1"

@app.route('/scan/url', methods=['POST'])
def scan_url():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    headers = {
        "Authorization": f"Bearer {VIRUSTOTAL_API_KEY}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = requests.post(
        "https://www.virustotal.com/api/v3/urls",
        headers=headers,
        data={"url": url}
    )

    if response.status_code != 200:
        return jsonify({"error": "Failed to send to VirusTotal"}), 500

    scan_id = response.json()["data"]["id"]
    return jsonify({"scan_id": scan_id})

@app.route('/scan/result', methods=['GET'])
def scan_result():
    scan_id = request.args.get('id')
    if not scan_id:
        return jsonify({"error": "No scan ID provided"}), 400

    headers = {"Authorization": f"Bearer {VIRUSTOTAL_API_KEY}"}
    response = requests.get(
        f"https://www.virustotal.com/api/v3/analyses/{scan_id}",
        headers=headers
    )

    if response.status_code != 200:
        return jsonify({"error": "Failed to get result"}), 500

    result = response.json()["data"]["attributes"]["stats"]
    malicious = result.get("malicious", 0)
    total = sum(result.values())

    return jsonify({
        "malicious": malicious,
        "total": total,
        "safe": malicious == 0
    })

@app.route('/')
def home():
    return jsonify({"status": "VirusTotal Proxy is running"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

