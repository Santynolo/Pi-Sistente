from flask import Flask, send_file, request, render_template
from flask_sock import Sock
import socket, time, threading
from numpy import average
from pydub import AudioSegment
import json, os
# flask
app = Flask(__name__)
sock = Sock(app)

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


sensor_boxes = {
    "hab_b": {
        "motion":{
            "status": "offline",
            "detected": "no"
        },
        "DHT":{
            "temp_status": "offline",
            "temp": 0,
            "hum_status": "offline",
            "hum": 0,  
        },
        "c02":{
            "status": "offline",
            "val": 0
        }
    }
}

@sock.route("/update/sensor_box")
def update_motion(ws):
    try:
        bef_data = ""
        while True:
            data = ws.receive()
            if(str(data) == bef_data):
                return
            bef_data = str(data)
            print(data)
            ws.send("Data received")
            dataRecv = json.loads(data)
            print(sensor_boxes)
            sens_info = [dataRecv["name"], dataRecv["motion"], dataRecv["DHT"], dataRecv["c02"]]
            for i in sens_info:
                if i == None:
                    return "failure to get arguments"
            print(f"A motion sensor ({sens_info[0]}) has been updated!")
            # check if sensor name is valid
            if sens_info[0] in sensor_boxes.keys():
                # set sensor data
                json_fix = dataRecv
                json_fix.pop("name")
                sensor_boxes[sens_info[0]].update(json_fix)

            else:
                print("sensor name not found")
    except:
        print("detect?")

@app.route("/")
def index():
    # average temperature
    temp_list = []
    for i in sensor_boxes:
        if sensor_boxes[i]["DHT"]["temp_status"] == "online":
            temp_list.append(sensor_boxes[i]["DHT"]["temp"])
    average_temp = "Offline"
    if len(temp_list) > 0:
        average_temp = sum(temp_list) / len(temp_list)

    # average humidity
    hum_list = []
    for i in sensor_boxes:
        if sensor_boxes[i]["DHT"]["hum_status"] == "online":
            hum_list.append(sensor_boxes[i]["DHT"]["hum"])
    average_hum = "Offline"
    if len(hum_list) > 0:
        average_hum = sum(hum_list) / len(hum_list)

    # average gas
    gas_list = []
    for i in sensor_boxes:
        if sensor_boxes[i]["c02"]["status"] == "online":
            gas_list.append(sensor_boxes[i]["c02"]["val"])
    average_gas = "Offline"
    if len(gas_list) > 0:
        average_gas = sum(gas_list) / len(gas_list)
    
    # if movement
    movementDetected = "No"
    movement_online = False
    for i in sensor_boxes:
        if sensor_boxes[i]["motion"]["status"] == "online":
            movement_online = True
            if sensor_boxes[i]["motion"]["detected"] == "yes":
                movementDetected = "Si"
                break
    if movement_online == False:
        movementDetected = "Offline"
    json_data = {"temp": average_temp, "hum": average_hum, "gas": average_gas, "mov": movementDetected}
    return render_template('index.html', json_data=json_data)
@app.route("/get_sensorboxes")
def sensorbox_get():
    return str(sensor_boxes)

"""@sock.route("/sensorbox")
def sensorbox_get():
    """
@app.route('/downloadapp')
def downloadapp ():
    #For windows you need to use drive name [ex: F:/Example.pdf]
    path = os.path.join(os.getcwd(),"piSistente.apk")
    return send_file(path, as_attachment=True)

def beginServer():
    threading.Thread(target=lambda:app.run(host=str(get_ip()), port=5000, debug=True, use_reloader=False)).start()