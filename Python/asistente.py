from pydoc import ispackage
import wificomm
import subprocess as subp
import speech_recognition as sr
import tkinter as tk
import unicodedata
import pyjokes
import time
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio
from flask import Flask, Response                                                       
import threading
import socket
import queue
# obtain audio from the microphone
r = sr.Recognizer()
r.pause_threshold = 1
newCommandReceived = [False, ""]
isBusy = False
alarm_file = "I_remixed_a_bunch_of_EAS_alarms.mp3"
"""  DEFINITIONS  """
# speech
def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    only_ascii = nfkd_form.encode('ASCII', 'ignore')
    only_ascii = only_ascii.decode("utf-8")
    return only_ascii
def recognizeVoice():
    global isBusy
    if isBusy:
        return
    isBusy = True
    with sr.Microphone() as source:
        audio = r.listen(source, timeout=1)
    #root.update()
    #sendToConsole("Tiempo de escuchado terminado.")
    # recognize speech using Google Speech Recognition
    try:
        # for testing purposes, we're just using the default API key
        # to use another API key, use `r.recognize_google(audio, key="GOOGLE_SPEECH_RECOGNITION_API_KEY")`
        # instead of `r.recognize_google(audio)`
        recognized = r.recognize_google(audio, language="es-AR")
        newCommandReceived[0] = True
        newCommandReceived[1] = str(recognized)
        isBusy = False
        return str(recognized)
    except sr.UnknownValueError:
        sendToConsole("No se pudo entender audio")
    except sr.RequestError as e:
        sendToConsole("No se pudieron solicitar los resultados del servicio de reconocimiento de voz de Google; {0}".format(e))
    isBusy = False

currEspeakCall = None
def sayText(text, isblocking=True, speed = 160, pitch=50):
    global currEspeakCall
    if currEspeakCall != None:
        currEspeakCall.kill()
    cmd_beg= f'espeak -g 5 -s {speed} -p {pitch} -a 200 -v es+m1 "'
    cmd_end= '"' # To play back the stored .wav file and to dump the std errors to /dev/null
    sendToConsole(text)
    #Calls the Espeak TTS Engine to read aloud a Text
    if isblocking:
        subp.call(cmd_beg+text+cmd_end, shell=True)
        return
    currEspeakCall = subp.Popen(cmd_beg+text+cmd_end)

def calibrateSpeech():
    global isBusy
    if isBusy:
        return
    isBusy = True
    sayText("Calibrando sistema de reconocimiento de vos, por favor mantener silencio", True)
    with sr.Microphone() as source:
        sendToConsole("Calibrando microfono...")
        r.adjust_for_ambient_noise(source)  # listen for 1 second to calibrate the energy threshold for ambient noise levels
    sendToConsole("Calibracion terminada")
    sayText("Calibracion terminada", False)
    isBusy = False
# console
def sendToConsole(text):
    console_box.configure(state='normal')
    console_box.insert('end', "\n" + text)
    console_box.see("end")
    console_box.configure(state='disabled')
    root.update()

# lights
def specificRoomLight(dir):
    splitMsg = str(newCommandReceived[1]).split(" ")
    lightFloor = -1
    lightRoom = '1'
    for i in splitMsg:
        if i.isnumeric() and lightFloor == -1:
            lightFloor = int(i)
        elif len(i) == 1 and lightRoom == '1' and i.isnumeric() == False:
            lightRoom = i
    print(f'piso {lightFloor} sector {lightRoom}')
    if lightFloor <= 2 and lightFloor >= 0:
        listOfRoomsF1 = ["a", "b", "c", "d", "e", "v"]
        listOfRoomsF2 = ["a", "b", "c", "d", "e", "v"]

        if lightFloor == 1 or lightFloor == 0:
            if lightRoom in listOfRoomsF1:
                wificomm.SwitchLight(dir, lightRoom, lightFloor)
                if dir:
                    sayText(f"encendiendo luz en piso {lightFloor}, sector {lightRoom}", False)
                else:
                    sayText(f"apagando luz en piso {lightFloor}, sector {lightRoom}", False)
        else:
            if lightRoom in listOfRoomsF2:
                wificomm.SwitchLight(dir, lightRoom, lightFloor)
                if dir:
                    sayText(f"encendiendo luz en piso {lightFloor}, sector {lightRoom}", False)
                else:
                    sayText(f"apagando luz en piso {lightFloor}, sector {lightRoom}", False)
def allRoomLight(dir):
    wificomm.allLights(dir)
    if dir:
        sayText(f"encendiendo todas las luces", False)
        return
    sayText(f"apagando todas las luces", False)
# alerts
curr_playing = ""
alarmAudio = None
alarmPlayback = None
def co2Alert():
    killAlarm()
    global alarmPlayback, alarmPlaying, curr_playing
    sayText("ATENCION, ATENCION. SE A DETECTADO NIVELES", True)
    sayText("LETALES O PELIGROSOS", True, pitch=0)
    sayText("DE DIOXIDO DE CARBONO. POR FAVOR, EVACUE EL AREA Y BUSQUE ATENCION MEDICA INMEDIATA. ACTIVANDO SISTEMA DE VENTILACION.", True)
    alarmAudio = AudioSegment.from_file(alarm_file)
    alarmPlayback = None
    alarmPlayback = _play_with_simpleaudio(alarmAudio)
    alarmPlaying = True
    curr_playing = alarm_file

alarmPlayback = None
alarmPlaying = False
coolSong = None
def securityAlert():
    killAlarm()
    global alarmPlayback, alarmPlaying, curr_playing
    sayText("ATENCION, ATENCION. SE A DETECTADO MOVIMIENTO EN PISO X SENSOR X", True)
    sayText("ACTIVANDO MEDIDAS DE SEGURIDAD", True, pitch=0)
    sayText("PELIGRO DE SEGURIDAD NIVEL: X", True)
    alarmAudio = AudioSegment.from_file(alarm_file)
    alarmPlayback = None
    alarmPlayback = _play_with_simpleaudio(alarmAudio)
    alarmPlaying = True
    curr_playing = alarm_file

def killAlarm():
    global alarmPlaying, alarmPlayback, curr_playing
    if alarmPlayback != None:
        alarmPlayback.stop()
    alarmPlaying = False
    alarmPlayback = None
    curr_playing = ""
"""  DEFINITIONS  """

root = tk.Tk()
root.title('Asistente')
root.geometry('800x480')

console_box = tk.Text(
    root,
    height=12,
    width=40
)
console_box.place(x=800*0.5-200, y=480-200, width=400, height=200)
console_box.insert('1.0', "Consola iniciada")
console_box.configure(state='disabled')

calibrate_button = tk.Button(root, text ="Calibrar\nMic", command =calibrateSpeech, width=10, height=5)
calibrate_button.place(width=60, height=50, x=10, y = 0)

talk_button = tk.Button(root, text ="Hablar", command = recognizeVoice, width=10, height=5)
talk_button.place(width=60, height=50, x=20 + 60, y = 0)

c02_test_button = tk.Button(root, text ="Test alarma\nC02", command = co2Alert, width=10, height=5)
c02_test_button.place(width=70, height=50, x=60*2+30, y = 0)

securityAlert_test_button = tk.Button(root, text ="Test alarma\nSeguridad", command =securityAlert, width=10, height=5)
securityAlert_test_button.place(width=70, height=50, x=60*3+50, y = 0)

kill_alarm_button = tk.Button(root, text ="Parar\nalarma", command = killAlarm, width=10, height=5)
kill_alarm_button.place(width=70, height=50, x=60*5+10, y = 0)
answersDir = {
    "quien eres": "soy un asistente llamado David creado el 14 del 4 de 2022, por santino dominguez",
    "que eres": "soy un asistente llamado David creado el 14 del 4 de 2022, por santino dominguez",
    "hola": "Hola, quien sea que seas",
    "que haces": "nada, solo contemplando estar atrapado en una PC",
    "dime una broma": lambda: sayText(pyjokes.get_joke(language="es", category="neutral"), True),
    "di una broma": lambda: sayText(pyjokes.get_joke(language="es", category="neutral"), True),
    "encender luz": lambda: specificRoomLight(True),
    "encendiende luz": lambda: specificRoomLight(True),
    # apagar lus individiual
    "apagar luz": lambda: specificRoomLight(False),
    "apaga luz": lambda: specificRoomLight(False),
    # apagar luces
    "apagar luces": lambda: allRoomLight(False),
    "apaga luces": lambda: allRoomLight(False),
    "apaga todas las luces": lambda: allRoomLight(False),
    "apagar todas las luces": lambda: allRoomLight(False),
    # encender luces
    "encender luces": lambda: allRoomLight(True),
    "enciende luces": lambda: allRoomLight(True),
    "enciende todas las luces": lambda: allRoomLight(True),
    "encender todas las luces": lambda: allRoomLight(True),
    "ja": "de que te ries? ojala que no sea yo, porque no sabes de lo que soy capas"
}
# flask
app = Flask(__name__)
# 128kb compressed mp3 audio
@app.route("/mp3_128")
def streamMP3():
    global curr_playing
    if curr_playing == "":
        return ""
    def generate():
        with open(curr_playing, "rb") as fmp3:
            data = fmp3.read(1024)
            while data:
                yield data
                data = fmp3.read(1024)
    return Response(generate(), mimetype="audio/mp3")
@app.route("/audio_status")
def checkAudioStatus():
    global curr_playing
    if curr_playing == "":
        return "0"
    else:
        return "1"

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

if __name__ == "__main__":
    
    web = threading.Thread(target=lambda: app.run(host=str(get_ip()), port=5000, debug=True, use_reloader=False))
    web.start()
    while True:
        if newCommandReceived[0] == True:
            msg = str(newCommandReceived[1])
            msg = msg.lower()
            msg = str(remove_accents(msg))
            newCommandReceived[1] = msg
            sendToConsole("Dijiste: " + newCommandReceived[1])
            for answer in answersDir:
                if msg.startswith(answer):
                    if(isinstance(answersDir[answer], str)):
                        sayText(answersDir[answer], False)
                    elif(isinstance(answersDir[answer], list)):
                        for i in answersDir[answer]:
                            if isinstance(i, str):
                                sayText(i, False)
                            else:
                                i()
                    elif(callable(answersDir[answer])):
                        answersDir[answer]()
                    break
            newCommandReceived[0] = False
        
        if alarmPlaying == False and alarmPlayback != None:
            alarmPlayback.stop()
            alarmPlayback = None
            curr_playing = ""
        
        root.update()