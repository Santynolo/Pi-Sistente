from numpy import floor
from tuya_connector import TuyaOpenAPI
from requests import get
import time
# online using tuya-connector-python and tuya-iot-py-sdk
ACCESS_ID = "mdgqqncqbicz4tjtjm7d" # your_access_id
ACCESS_KEY = "3f28c3c9aac94ea6a1a29d8eeaca628f" # your_access_key
USERNAME = "santyarduino2247@gmail.com"  #your_username
PASSWORD = "Arduino2247"  #your_password
ASSET_ID = "1515025591043215360" #your_asset_id

ENDPOINT = "https://openapi-ueaz.tuyaus.com"

# Init
openapi = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_KEY)

devices_id = {
    'b': ['657c08320f7d7a3521cadw', '']
}
def SwitchLight(value, name, floorName):
    if name == 'v':
        name = 'b'
    commands = {'commands': [{'code': 'switch_1', 'value': value}]}
    if floorName == 1 or floorName == 0:
        openapi.post('/v1.0/iot-03/devices/{}/commands'.format(devices_id[name][0]), commands)
    elif floorName == 2:
        openapi.post('/v1.0/iot-03/devices/{}/commands'.format(devices_id[name][1]), commands)
def allLights(value):
    commands = {'commands': [{'code': 'switch_1', 'value': value}]}
    #openapi.post('/v1.0/iot-03/devices/{}/commands'.format(devices_id['b'][0]), commands)
    for i in devices_id:
        if devices_id[i][0] == '':
            continue
        print(devices_id[i][0])
        openapi.post('/v1.0/iot-03/devices/{}/commands'.format(devices_id[i][0]), commands)
        time.sleep(1)
    for i in devices_id:
        if devices_id[i][1] == '':
            continue
        openapi.post('/v1.0/iot-03/devices/{}/commands'.format(devices_id[i][1]), commands)
        time.sleep(1)