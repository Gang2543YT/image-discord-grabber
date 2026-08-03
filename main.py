import eventlet
eventlet.monkey_patch()

import os
import math
import random
from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, leave_room, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'terra-quest-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

WORLD_WIDTH = 120
WORLD_HEIGHT = 45

rooms_players = {}
rooms_worlds = {}

def generate_server_world():
    world = [[0 for _ in range(WORLD_WIDTH)] for _ in range(WORLD_HEIGHT)]
    surface_height = 18
    for x in range(WORLD_WIDTH):
        surface_height += math.floor(math.sin(x * 0.15) * 1.5 + (random.random() * 0.6 - 0.3))
        surface_height = max(12, min(28, surface_height))

        for y in range(surface_height, WORLD_HEIGHT):
            if y == surface_height:
                world[y][x] = 3  # Grass
            elif y < surface_height + 5:
                world[y][x] = 1  # Dirt
            else:
                world[y][x] = 2  # Stone
    return world

@app.route('/')
def home():
    return render_template('index.html')

@socketio.on('join_server')
def handle_join(data):
    room = data.get('room', 'main').lower()
    name = data.get('name', 'Hero')
    
    join_room(room)
    
    if room not in rooms_worlds:
        rooms_worlds[room] = generate_server_world()
    
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
    
    # Send the current world map and players to the newly connected user
    emit('init_world', {'world': rooms_worlds[room], 'players': rooms_players[room]})
    emit('player_joined', player_data, to=room, include_self=False)

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

@socketio.on('update_tile')
def handle_tile_update(data):
    room = data.get('room')
    x = data.get('x')
    y = data.get('y')
    tile = data.get('tile')
    
    if room and room in rooms_worlds:
        if 0 <= x < WORLD_WIDTH and 0 <= y < WORLD_HEIGHT:
            rooms_worlds[room][y][x] = tile
            emit('tile_updated', data, to=room, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    for room, players in list(rooms_players.items()):
        if request.sid in players:
            del players[request.sid]
            emit('player_left', {'id': request.sid}, to=room)
            if not players:
                if room in rooms_players:
                    del rooms_players[room]
                if room in rooms_worlds:
                    del rooms_worlds[room]
            break

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)