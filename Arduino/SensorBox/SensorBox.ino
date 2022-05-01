/**
 *  Sensor box
 *
 *  Created on: 18.4.2022
 *
 */
//#include "SPIFFS.h"
//#include <Arduino.h>
#include <DHTesp.h>
#define DHT_PIN 14
#define MOTION_PIN 2
DHTesp dht;
// gas sensor
const int RL = 11;  //The value of resistor RL is 5K
const float m = -0.47616; //Enter calculated Slope 
const float b = 3.14147; //Enter calculated intercept
const int Ro = 13;//Enter found Ro value
const int MQ_sensor = 0; //Sensor is connected to A0

#include <ESP8266WiFi.h>
#include <ArduinoJson.h>          // https://github.com/bblanchon/ArduinoJson
#include <WebSocketsClient.h>

WebSocketsClient webSocket; // websocket client class instance

String server_ip = "";
String server_port = "";
String server_send = "";
//flag for saving data
bool shouldSaveConfig = false;
bool wifiIsConnected = false;

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    switch(type) {
        case WStype_DISCONNECTED:
            Serial.printf("[WSc] Disconnected!\n");
            wifiIsConnected = false;
            break;
        case WStype_CONNECTED: {
            Serial.printf("[WSc] Connected to url: %s\n", payload);
            wifiIsConnected = true;
        }
            break;
        case WStype_TEXT:
            Serial.printf("[WSc] RESPONSE: %s\n", payload);
            break;
        case WStype_BIN:
            break;
                case WStype_PING:
                        // pong will be send automatically
                        Serial.printf("[WSc] get ping\n");
                        break;
                case WStype_PONG:
                        // answer to a ping we send
                        Serial.printf("[WSc] get pong\n");
                        break;
    }
 
}
float smokeRead()
{
  // put your main code here, to run repeatedly:
  float VRL; //Voltage drop across the MQ sensor
  float Rs; //Sensor resistance at gas concentration 
  float ratio; //Define variable for ratio

  VRL = analogRead(MQ_sensor)*(5.0/1023.0); //Measure the voltage drop and convert to 0-5V
  Rs = ((5.0*RL)/VRL)-RL; //Use formula to get Rs value
  ratio = Rs/Ro;  // find ratio Rs/Ro
 
  float ppm = pow(10, ((log10(ratio)-b)/m)); //use formula to calculate ppm
  Serial.println(ppm*0.01);
  return ppm*0.01;
}
void setup() {
  delay(500);
  //WiFi.mode(WIFI_STA); // explicitly set mode, esp defaults to STA+AP
  // it is a good practice to make sure your code sets wifi mode how you want it.
  WiFi.begin("aef782", "235055626");
  // put your setup code here, to run once:
  Serial.begin(115200);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println(".");
  }
  // if you get here you have connected to the WiFi
  Serial.println("Connected.");
  //Serial.println(serverPort_field.getValue());
  server_ip = "192.168.0.12";//String(serverIP_field.getValue());
  server_port = "5000";//String(serverPort_field.getValue());
  
  Serial.println(server_ip);
  Serial.println(server_port);
  //address, port, and URL path
  webSocket.begin(server_ip, server_port.toInt(), "/update/sensor_box");
  // WebSocket event handler
  webSocket.onEvent(webSocketEvent);
  // if connection failed retry every 5s
  webSocket.setReconnectInterval(5000);
  //pinMode(DHT_PIN, INPUT);
  dht.setup(DHT_PIN, DHTesp::DHT11);
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
  if (prevMotion != motion && motion_status && wifiIsConnected)
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
    server_send =  "";
    serializeJson(jsonSend, server_send);
    webSocket.sendTXT(server_send);
  }
  if (millis() - time_now > 5000 && wifiIsConnected && millis() - time_now > dht.getMinimumSamplingPeriod()){
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
        tempVal = dht.getTemperature();
        humVal = dht.getHumidity();
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
        server_send = "";
        serializeJson(jsonSend, server_send);
        webSocket.sendTXT(server_send);
        time_now = millis();
  }
  webSocket.loop();
}
