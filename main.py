import eventlet
eventlet.monkey_patch()

import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, leave_room, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'terra-quest-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

rooms_players = {}

@app.route('/')
def home():
    return render_template('index.html')

@socketio.on('join_server')
def handle_join(data):
    room = data.get('room', 'main').lower()
    name = data.get('name', 'Hero')
    
    join_room(room)
    
    player_data = {
        'id': request.sid,
        'name': name,
        'x': 100,
        'y': 100,
        'facing': 'right',
        'frame': 0,
        'room': room
    }
    
    if room not in rooms_players:
        rooms_players[room] = {}
    rooms_players[room][request.sid] = player_data
    
    emit('player_joined', player_data, to=room, include_self=False)
    emit('current_players', rooms_players[room])

@socketio.on('player_update')
def handle_update(data):
    room = data.get('room')
    if room and room in rooms_players and request.sid in rooms_players[room]:
        p = rooms_players[room][request.sid]
        p['x'] = data.get('x', p['x'])
        p['y'] = data.get('y', p['y'])
        p['facing'] = data.get('facing', p['facing'])
        p['frame'] = data.get('frame', p['frame'])
        
        emit('player_moved', p, to=room, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    for room, players in list(rooms_players.items()):
        if request.sid in players:
            del players[request.sid]
            emit('player_left', {'id': request.sid}, to=room)
            if not players:
                del rooms_players[room]
            break

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)