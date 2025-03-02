#!/usr/bin/env python3
import os
import json
import time
import sys
import paho.mqtt.client as mqtt
import mercury

MQTT_BROKER    = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT      = int(os.getenv("MQTT_PORT", "1883"))
TOPIC_START    = os.getenv("MQTT_TOPIC_START", "reader/start")
TOPIC_STOP     = os.getenv("MQTT_TOPIC_STOP", "reader/stop")
TOPIC_OUTPUT   = os.getenv("MQTT_TOPIC_OUTPUT", "reader/output")
RFID_DEVICE    = os.getenv("RFID_DEVICE", "tmr:///dev/ttyUSB0")
RFID_BAUDRATE  = int(os.getenv("RFID_BAUDRATE", "115200"))

readActive = False
reader = None
client = None
connectionActive = False

try:
    reader = mercury.Reader(RFID_DEVICE,baudrate=RFID_BAUDRATE)
except Exception as e:
    print(e)
    sys.exit()

def exception_handler(e):
    global readActive
    readActive = False
    print("READER EXCEPTION HANDLER")
    print(e)

def readingCallback(tagData):
    global client
    tag = {
        "timestamp":int(time.time()),
        "epc":tagData.epc,
        "antenna":tag.antenna,
        "read_count":tag.read_count,
        "rssi":tag.rssi

    }
    print(json.dumps(tag))
    client.publish(TOPIC_OUTPUT,json.dumps(tag))


def on_connect(client, userdata, flags, rc):
    print("MQTT Connected:", rc)
    connectionActive = True
    client.subscribe(TOPIC_START)
    client.subscribe(TOPIC_STOP)

def on_message(client, userdata, msg):
    global readActive
    global reader
    topic = msg.topic
    payload = msg.payload.decode("utf-8")
    print(f"Message received {topic}: {payload}")
    
    if topic == TOPIC_START:
        try:
            params = json.loads(payload)
            power     = params.get("power", 25)
            region    = params.get("region", "EU3")
            antennas  = params.get("antennas", [1])
            filter_val= params.get("filter", None)
            tid_enabled = params.get("tid", False)
            
            # Jeśli już działa odczyt, zatrzymaj go przed nowym uruchomieniem
            if readActive is True:            
                reader.stop_reading()
                readActive = False

            reader.set_region(region)
            reader.set_read_plan(antennas, "GEN2", power=power, filter=filter_val, use_tid=tid_enabled)
            reader.enable_exception_handler(exception_callback)
            # Uruchomienie wątku odczytu tagów
            
            print("Read start with params:", params)
        except Exception as e:
            print("Error during start read:", e)
    
    elif topic == TOPIC_STOP:
        print("Stopping read...")
        #TODO STOP READ
        readActive = False

def main():
    global client
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
    except Exception as e:
        print("Cannot connect to MQTT:", e)
        return
    
    client.loop_forever()

if __name__ == "__main__":
    main()