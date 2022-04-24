from flask import Flask, Response, request, render_template
from flask_sock import Sock
import socket, time, threading
from numpy import average
from pydub import AudioSegment
import pyaudio, json, audio_processing
# flask
app = Flask(__name__)
sock = Sock(app)
curr_secs = 0
start_time = time.time()
fileEnded = False
p = pyaudio.PyAudio()
for i in range(p.get_device_count()):
    print(p.get_device_info_by_index(i))
rate = 44100
chunk = 1024
# index: 3
#https://stackoverflow.com/questions/51079338/audio-livestreaming-with-python-flask
# 128kb compressed mp3 audio
first_run = True
@app.route("/mp3_128")
def streamMP3():
    if fileEnded:
        return ""
    audioPath = r"C:\Users\Santy\Desktop\AsistentePython\bad_EAS_alarms.mp3"
    def generate():
        wav_header = genHeader(rate, 16, 2)
        stream = p.open(format=pyaudio.paInt16, channels=2, rate=rate, input=True, input_device_index=2, frames_per_buffer=chunk)
        global first_run
        while True:
            if first_run:
                data = wav_header + stream.read(chunk)
                first_run = False
            else:
                data = stream.read(chunk)
            yield data
        """
        with open("bad_EAS_alarms.mp3", "rb") as fmp3:
            data = fmp3.read(1024)
            while data:
                yield data
                data = fmp3.read(1024)"""
    return Response(generate(), mimetype="audio/x-wav;codec=pcm")

def genHeader(sampleRate, bitsPerSample, channels):
    datasize = 2000*10**6
    o = bytes("RIFF",'ascii')                                               # (4byte) Marks file as RIFF
    o += (datasize + 36).to_bytes(4,'little')                               # (4byte) File size in bytes excluding this and RIFF marker
    o += bytes("WAVE",'ascii')                                              # (4byte) File type
    o += bytes("fmt ",'ascii')                                              # (4byte) Format Chunk Marker
    o += (16).to_bytes(4,'little')                                          # (4byte) Length of above format data
    o += (1).to_bytes(2,'little')                                           # (2byte) Format type (1 - PCM)
    o += (channels).to_bytes(2,'little')                                    # (2byte)
    o += (sampleRate).to_bytes(4,'little')                                  # (4byte)
    o += (sampleRate * channels * bitsPerSample // 8).to_bytes(4,'little')  # (4byte)
    o += (channels * bitsPerSample // 8).to_bytes(2,'little')               # (2byte)
    o += (bitsPerSample).to_bytes(2,'little')                               # (2byte)
    o += bytes("data",'ascii')                                              # (4byte) Data Chunk Marker
    o += (datasize).to_bytes(4,'little')                                    # (4byte) Data size in bytes
    return o
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
        while True:
            data = ws.receive()
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

app.run(host=str(get_ip()), port=5000, debug=True, use_reloader=False)