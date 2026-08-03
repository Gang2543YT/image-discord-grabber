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

WORLD_WIDTH = 150
WORLD_HEIGHT = 55

rooms_players = {}
rooms_worlds = {}
rooms_items = {}
rooms_mobs = {}
rooms_time = {}

def generate_server_world():
    world = [[0 for _ in range(WORLD_WIDTH)] for _ in range(WORLD_HEIGHT)]
    surface_height = 20
    
    # Flatter, smoother terrain profile
    for x in range(WORLD_WIDTH):
        surface_height += math.floor(math.sin(x * 0.06) * 0.5 + (random.random() * 0.2 - 0.1))
        surface_height = max(16, min(24, surface_height))

        for y in range(surface_height, WORLD_HEIGHT):
            if y == surface_height:
                world[y][x] = 3  # Grass
            elif y < surface_height + 4:
                world[y][x] = 1  # Dirt
            else:
                world[y][x] = 2  # Stone

    # Clumped Ore Veins generation
    for _ in range(25):
        ore_type = random.choices([6, 7, 8, 9], weights=[50, 30, 15, 5])[0]
        ox = random.randint(5, WORLD_WIDTH - 5)
        oy = random.randint(26, WORLD_HEIGHT - 6)
        for _ in range(5):
            ox += random.randint(-1, 1)
            oy += random.randint(-1, 1)
            if 0 < ox < WORLD_WIDTH - 1 and 24 < oy < WORLD_HEIGHT - 1:
                if world[oy][ox] == 2:
                    world[oy][ox] = ore_type

    # Smaller, tighter cave carvers underground
    for _ in range(16):
        cx = random.randint(10, WORLD_WIDTH - 10)
        cy = random.randint(26, WORLD_HEIGHT - 6)
        carve_radius = random.randint(2, 4)  # Smaller cave size
        for _ in range(25):
            cx += random.randint(-2, 2)
            cy += random.randint(-1, 1)
            for ky in range(cy - carve_radius, cy + carve_radius + 1):
                for kx in range(cx - carve_radius, cx + carve_radius + 1):
                    if 0 < kx < WORLD_WIDTH - 1 and 23 < ky < WORLD_HEIGHT - 1:
                        if math.hypot(kx - cx, ky - cy) <= carve_radius:
                            if world[ky][kx] != 3:  # Keep surface grass intact
                                world[ky][kx] = 0  # Cave Air

    # Trees on surface
    for x in range(6, WORLD_WIDTH - 6, 8):
        if random.random() < 0.75:
            sy = 0
            for y in range(WORLD_HEIGHT):
                if world[y][x] == 3:
                    sy = y
                    break
            if sy > 0:
                for ty in range(1, 5):
                    if sy - ty >= 0:
                        world[sy - ty][x] = 4  # Wood
                for lx in range(x - 2, x + 3):
                    for ly in range(sy - 7, sy - 4):
                        if 0 <= lx < WORLD_WIDTH and 0 <= ly < WORLD_HEIGHT and world[ly][lx] == 0:
                            world[ly][lx] = 5  # Leaves

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
        rooms_items[room] = []
        rooms_mobs[room] = []
        rooms_time[room] = 0
    
    player_data = {
        'id': request.sid,
        'name': name,
        'x': 100,
        'y': 100,
        'facing': 'right',
        'frame': 0,
        'room': room,
        'hp': 100
    }
    
    if room not in rooms_players:
        rooms_players[room] = {}
    rooms_players[room][request.sid] = player_data
    
    emit('init_world', {
        'world': rooms_worlds[room], 
        'players': rooms_players[room], 
        'items': rooms_items[room],
        'time': rooms_time[room]
    })
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

@socketio.on('spawn_item')
def handle_spawn_item(data):
    room = data.get('room')
    item = data.get('item')
    if room and item and room in rooms_items:
        rooms_items[room].append(item)
        emit('sync_items', rooms_items[room], to=room)

@socketio.on('collect_item')
def handle_collect_item(data):
    room = data.get('room')
    index = data.get('index')
    if room and room in rooms_items:
        if 0 <= index < len(rooms_items[room]):
            rooms_items[room].pop(index)
            emit('sync_items', rooms_items[room], to=room)

@socketio.on('disconnect')
def handle_disconnect():
    for room, players in list(rooms_players.items()):
        if request.sid in players:
            del players[request.sid]
            emit('player_left', {'id': request.sid}, to=room)
            if not players:
                rooms_players.pop(room, None)
                rooms_worlds.pop(room, None)
                rooms_items.pop(room, None)
                rooms_mobs.pop(room, None)
                rooms_time.pop(room, None)
            break

def background_world_ticker():
    while True:
        eventlet.sleep(1)
        for room in list(rooms_worlds.keys()):
            if room in rooms_time:
                rooms_time[room] = (rooms_time[room] + 1) % 1200
                is_night = rooms_time[room] >= 600
                
                mobs = rooms_mobs.get(room, [])
                if is_night:
                    if len(mobs) < 6 and random.random() < 0.25:
                        mx = random.randint(10, WORLD_WIDTH - 10)
                        my = random.randint(26, WORLD_HEIGHT - 5)
                        if rooms_worlds[room][my][mx] == 0:  # Cave air spawn
                            mobs.append({'id': random.randint(1000, 9999), 'x': mx * 32, 'y': my * 32, 'hp': 40})
                else:
                    mobs = []
                rooms_mobs[room] = mobs
                socketio.emit('world_tick', {'time': rooms_time[room], 'mobs': mobs}, to=room)

eventlet.spawn(background_world_ticker)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)