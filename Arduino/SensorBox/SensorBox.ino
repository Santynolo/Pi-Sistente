/**
 *  Sensor box
 *
 *  Created on: 18.4.2022
 *
 */
#include <FS.h> //this needs to be first, or it all crashes and burns...
#include "SPIFFS.h"
#include <Arduino.h>
#include <DHT.h>
#define DHT_TYPE DHT11
#define DHT_PIN 4
#define MOTION_PIN 2
DHT dht(DHT_PIN, DHT_TYPE);
// gas sensor
const int RL = 11;  //The value of resistor RL is 5K
const float m = -0.47616; //Enter calculated Slope 
const float b = 3.14147; //Enter calculated intercept
const int Ro = 13;//Enter found Ro value
const int MQ_sensor = 35; //Sensor is connected to A4

#include <WiFi.h>
#include <WiFiMulti.h>
#include <WiFiManager.h> // https://github.com/tzapu/WiFiManager
#include <ArduinoJson.h>          // https://github.com/bblanchon/ArduinoJson
#include <WebSocketsClient.h>

#define USE_SERIAL Serial
WebSocketsClient webSocket; // websocket client class instance
WiFiMulti wifiMulti;
WiFiManager wm;
String server_ip = "";
String server_port = "";
String server_send = "";
//flag for saving data
bool shouldSaveConfig = false;
bool isConnected = false;
//callback notifying us of the need to save config
void saveConfigCallback () {
  USE_SERIAL.println("Should save config");
  shouldSaveConfig = true;
}

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    switch(type) {
        case WStype_DISCONNECTED:
            USE_SERIAL.printf("[WSc] Disconnected!\n");
            isConnected = false;
            break;
        case WStype_CONNECTED: {
            USE_SERIAL.printf("[WSc] Connected to url: %s\n", payload);
            isConnected = true;
        }
            break;
        case WStype_TEXT:
            USE_SERIAL.printf("[WSc] RESPONSE: %s\n", payload);
            break;
        case WStype_BIN:
            break;
                case WStype_PING:
                        // pong will be send automatically
                        USE_SERIAL.printf("[WSc] get ping\n");
                        break;
                case WStype_PONG:
                        // answer to a ping we send
                        USE_SERIAL.printf("[WSc] get pong\n");
                        break;
    }
 
}
float smokeRead()
{
  // put your main code here, to run repeatedly:
  float VRL; //Voltage drop across the MQ sensor
  float Rs; //Sensor resistance at gas concentration 
  float ratio; //Define variable for ratio

  VRL = analogRead(MQ_sensor)*(5.0/4095.0); //Measure the voltage drop and convert to 0-5V
  Rs = ((5.0*RL)/VRL)-RL; //Use formula to get Rs value
  ratio = Rs/Ro;  // find ratio Rs/Ro
 
  float ppm = pow(10, ((log10(ratio)-b)/m)); //use formula to calculate ppm
  Serial.println(ppm*0.01);
  return ppm*0.01;
}
void setup() {
  WiFi.mode(WIFI_STA); // explicitly set mode, esp defaults to STA+AP
  // it is a good practice to make sure your code sets wifi mode how you want it.
  
  // put your setup code here, to run once:
  USE_SERIAL.begin(115200);

  //read configuration from FS json
  Serial.println("mounting FS...");

  if (SPIFFS.begin()) {
    Serial.println("mounted file system");
    if (SPIFFS.exists("/config.json")) {
      //file exists, reading and loading
      Serial.println("reading config file");
      File configFile = SPIFFS.open("/config.json", "r");
      if (configFile) {
        Serial.println("opened config file");
        size_t size = configFile.size();
        // Allocate a buffer to store contents of the file.
        std::unique_ptr<char[]> buf(new char[size]);

        configFile.readBytes(buf.get(), size);
        DynamicJsonDocument json(1024);
        auto error = deserializeJson(json, buf.get());
        if (error) {
          Serial.println("failed to load json config");
        }
        Serial.println("\nparsed json");
        server_ip = (const char*)json["server_ip"];
        server_port = (const char*)json["server_port"];
        
      }
    }
  } else {
    Serial.println("failed to mount FS");
  }
  //end read
  
  WiFiManagerParameter serverIP_field("ipserver", "Server IP", server_ip.c_str(), 18);
  WiFiManagerParameter serverPort_field("portserver", "Server Port", server_port.c_str(), 8);
  
  //set config save notify callback
  wm.setSaveConfigCallback(saveConfigCallback);

  //add all your parameters here
  wm.addParameter(&serverIP_field);
  wm.addParameter(&serverPort_field);
  // reset settings - wipe stored credentials for testing
  // these are stored by the esp library
  //wm.resetSettings();

  // Automatically connect using saved credentials,
  // if connection fails, it starts an access point with the specified name ( "AutoConnectAP"),
  // if empty will auto generate SSID, if password is blank it will be anonymous AP (wm.autoConnect())
  // then goes into a blocking loop awaiting configuration and will return success result

  bool res;
  // res = wm.autoConnect(); // auto generated AP name from chipid
  // res = wm.autoConnect("AutoConnectAP"); // anonymous ap
  res = wm.autoConnect("Sensor Box","password"); // password protected ap

  // if you get here you have connected to the WiFi
  Serial.println("Connected.");
  Serial.println(serverPort_field.getValue());
  server_ip = String(serverIP_field.getValue());
  server_port = String(serverPort_field.getValue());

  //save the custom parameters to FS
  if (shouldSaveConfig) {
    Serial.println("saving config");
    DynamicJsonDocument json(1024);
    json["server_ip"] = server_ip;
    json["server_port"] = server_port;

    File configFile = SPIFFS.open("/config.json", "w");
    if (!configFile) {
      Serial.println("failed to open config file for writing");
    }

    serializeJson(json, configFile);
    configFile.close();
    //end save
  }
  USE_SERIAL.println(server_ip);
  USE_SERIAL.println(server_port);
  //address, port, and URL path
  webSocket.begin(server_ip, server_port.toInt(), "/update/sensor_box");
  // WebSocket event handler
  webSocket.onEvent(webSocketEvent);
  // if connection failed retry every 5s
  webSocket.setReconnectInterval(5000);
  dht.begin();
  pinMode(MOTION_PIN, INPUT);
}
bool motion_status = true;
bool temp_status = true;
bool hum_status = true;
bool c02_status = false;
float tempVal = 0;
float humVal = 0;
float c02Val = 0;
int motion = LOW;
int prevMotion = LOW;

bool waitForSmoke = true;
unsigned long time_now = 5000;
void loop() {
  if(millis() > 60000 * 3 && waitForSmoke)
  {
    c02_status = true;
    waitForSmoke = false;
  }
  prevMotion = motion;
  motion = digitalRead(MOTION_PIN);
  if (prevMotion != motion && motion_status && isConnected)
  {
    DynamicJsonDocument jsonSend(1024);
    jsonSend["name"] = "hab_b";
    jsonSend["motion"]["status"] = "online";
    if(motion == HIGH)
    {
      jsonSend["motion"]["detected"] = "yes";
    }
    else
    {
      jsonSend["motion"]["detected"] = "no";
    }
    jsonSend["DHT"]["temp_status"] = temp_status ? "online" : "offline";
    jsonSend["DHT"]["temp"] = tempVal;
    jsonSend["DHT"]["hum_status"] = hum_status ? "online" : "offline";
    jsonSend["DHT"]["hum"] = humVal;
    // Gas Sensor
    jsonSend["c02"]["status"] = c02_status ? "online" : "offline";
    jsonSend["c02"]["val"] = c02Val;
    server_send = String("");
    serializeJson(jsonSend, server_send);
    webSocket.sendTXT(server_send);
  }
  if (millis() - time_now > 5000 && isConnected){
        DynamicJsonDocument jsonSend(1024);
        jsonSend["name"] = "hab_b";
        // Motion Sensor
        if(motion_status)
        {
          jsonSend["motion"]["status"] = "online";
          if(motion == HIGH)
          {
            jsonSend["motion"]["detected"] = "yes";
          }
          else
          {
            jsonSend["motion"]["detected"] = "no";
          }
        }
        else
        {
          jsonSend["motion"]["status"] = "offline";
          jsonSend["motion"]["detected"] = "no";
        }
        // DHT Sensor
        tempVal = dht.readTemperature();
        humVal = dht.readHumidity();
        if(isnan(tempVal))
        {
          temp_status = false;
          tempVal = 0;
        }
        else
        {
          temp_status = true;
        }
        
        if(isnan(humVal))
        {
          hum_status = false;
          humVal = 0;
        }
        else
        {
          hum_status = true;
        }
        jsonSend["DHT"]["temp_status"] = temp_status ? "online" : "offline";
        jsonSend["DHT"]["temp"] = tempVal;
        
        jsonSend["DHT"]["hum_status"] = hum_status ? "online" : "offline";
        jsonSend["DHT"]["hum"] = humVal;
        // Gas Sensor
        c02Val = smokeRead();
        jsonSend["c02"]["status"] = c02_status ? "online" : "offline";
        jsonSend["c02"]["val"] = c02Val;
        server_send = String("");
        serializeJson(jsonSend, server_send);
        webSocket.sendTXT(server_send);
        time_now = millis();
  }

  if(USE_SERIAL.available() > 1)
  {
    wm.resetSettings();
    ESP.restart();
  }
  webSocket.loop();
}
