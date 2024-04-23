from threading import Lock
from flask import Flask, render_template, session, request, jsonify, url_for
from flask_socketio import SocketIO, emit, disconnect    
import MySQLdb       
import math
import time
import configparser as ConfigParser
import random
import re
import serial

## serial communication
ser = serial.Serial("/dev/ttyACM0", 9600)
ser.baudrate = 9600

async_mode = None

app = Flask(__name__)

## drop table poit.graph;
## create table poit.graph ( id int, hodnoty varchar(16000) );

config = ConfigParser.ConfigParser()
config.read('config.cfg')
myhost = config.get('mysqlDB', 'host')
myuser = config.get('mysqlDB', 'user')
mypasswd = config.get('mysqlDB', 'passwd')
mydb = config.get('mysqlDB', 'db')

dataFile = './data_file'

app.config['SECRET_KEY'] = 'not_for_production_use!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock() 

run = None

def background_thread(args):
    count = 0
    dataList = []
    db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)          
    while True:
        socketio.sleep(0.1)
        if not run:
          if len(dataList)>0:
            print('Data list:')
            print(str(dataList))
            fuj = str(dataList).replace("'", "\"")
            cursor = db.cursor()
            cursor.execute("SELECT MAX(id) FROM graph")
            maxid = cursor.fetchone()[0]
            print(f"MAXID is {maxid}")
            if maxid is None:
              maxid = 0
            cursor.execute("INSERT INTO graph (id, hodnoty) VALUES (%s, %s)", (int(maxid) + 1, fuj))
            db.commit()
            print(f"Data list stored to the database with index {int(maxid) + 1}.")
            socketio.emit('my_response',
                        {'data': f"DB index at {int(maxid) + 1}", 'count': count},
                        namespace='/test')
            with open(dataFile, "a+") as f:
            	f.write(f"{fuj}\n")
            	print(f"Data list stored to the file.")
            dataList = []
          continue
        ser_line = ser.readline()
        numbers = re.findall(r'\d+', str(ser_line))
        if len(numbers) > 0:
          light = numbers[0]
          if args:
            A = dict(args).get('A')
          else:
            A = 1
          print(f"A: {A}, run: {run}, light: {light}")
          count += 1
          t = time.time()
          x = count*0.1
          y1 = float(A)*math.sin(x)
          y2 = float(A)*math.cos(x)
          dataDict = {
            "count": count,
            "t": t,
            "x": x,
            "y1": y1,
            "y2": y2,
            "light": light
          }
          dataList.append(dataDict)
          if len(dataList)>0:
            socketio.emit('my_response',
                        {'data': light, 'count': count, 'x': x, 'y1': y1, 'y2': y2, 'light': light},
                        namespace='/test')

@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)

@app.route('/graph', methods=['GET', 'POST'])
def graph():
    return render_template('graph.html', async_mode=socketio.async_mode)

@app.route('/db/<string:num>')
def dbdata(num):
  db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)
  cursor = db.cursor()
  print(num)
  cursor.execute("SELECT hodnoty FROM  graph WHERE id=%s", (int(num),))
  rv = cursor.fetchone()
  return str(rv[0])

@app.route('/file/<string:num>')
def readmyfile(num):
    fo = open(dataFile, "r")
    rows = fo.readlines()
    return rows[int(num)-1]

@socketio.on('my_event', namespace='/test')
def test_message(message):   
    session['receive_count'] = session.get('receive_count', 0) + 1 
    session['A'] = message['value']    
    emit('my_response',
         {'data': message['value'], 'count': session['receive_count']})
 
@socketio.on('start', namespace='/test')
def test_start():
    global run
    run = True
    emit('my_response',
         {'data': 'Start', 'count': session['receive_count']})

@socketio.on('stop', namespace='/test')
def test_stop():
    global run
    run = False
    print("Message emitting is currently stopped.")
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
