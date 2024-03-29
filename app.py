from threading import Lock
from flask import Flask, render_template, session, request, jsonify, url_for
from flask_socketio import SocketIO, emit, disconnect    
import time
import random
import math

async_mode = None

app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock() 


def background_thread(args):
    count = 0
    dataList = []
    while True:
        if args:
          A = dict(args).get('A')
          print(f"A is set to {A}")
        else:
          A = 1 
        #print A
        #print args
        socketio.sleep(1)
        if not dict(args).get("run"):
          print("Message emitting is currently stopped.")
          continue
        count += 1
        t = time.time()
        x = count*0.1
        y1 = float(A)*math.sin(x)
        y2 = float(A)*math.cos(x)
        dataDict = {
          "t": t,
          "x": x,
          "y1": y1,
          "y2": y2}
        dataList.append(dataDict)
        if len(dataList)>0:
          print('Data list:')
          print(str(dataList))
          print(str(dataList).replace("'", "\""))
        socketio.emit('my_response',
                      {'data': y1, 'count': count, 'x': x, 'y1': y1, 'y2': y2},
                      namespace='/test')

@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)
  
@socketio.on('my_event', namespace='/test')
def test_message(message):   
    session['receive_count'] = session.get('receive_count', 0) + 1 
    session['A'] = message['value']    
    emit('my_response',
         {'data': message['value'], 'count': session['receive_count']})
 
@socketio.on('start', namespace='/test')
def test_start():   
    print("RECEIVED START SIGNAL")
    session['run'] = True
    emit('my_response',
         {'data': 'Start', 'count': session['receive_count']})
  
@socketio.on('stop', namespace='/test')
def test_stop():   
    print("RECEIVED STOP SIGNAL")
    session['run'] = False
    emit('my_response',
         {'data': 'Stop', 'count': session['receive_count']})
 
@socketio.on('disconnect_request', namespace='/test')
def disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()

@socketio.on('connect', namespace='/test')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread, args=session._get_current_object())
    emit('my_response', {'data': 'Connected', 'count': 0})

@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected', request.sid)

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80, debug=True)
