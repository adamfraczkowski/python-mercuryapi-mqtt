#!/usr/bin/env python3
import os
import json
import time
import sys
import paho.mqtt.client as mqtt
import mercury

MQTT_BROKER    = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT      = int(os.getenv("MQTT_PORT", "1883"))
TOPIC_START    = os.getenv("MQTT_TOPIC_START", "rfid-reader/start")
TOPIC_STOP     = os.getenv("MQTT_TOPIC_STOP", "rfid-reader/stop")
TOPIC_OUTPUT   = os.getenv("MQTT_TOPIC_OUTPUT", "rfid-reader/output")
TOPIC_ERROR   = os.getenv("MQTT_TOPIC_ERROR", "rfid-reader/error")
RFID_DEVICE    = os.getenv("RFID_DEVICE", "tmr:///dev/ttyUSB-RFID")
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
        "epc":str(tagData.epc),
        "antenna":tagData.antenna,
        "read_count":tagData.read_count,
        "rssi":tagData.rssi

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
            filter_epc = None
            filter_offset = None
            params = json.loads(payload)
            power     = int(params.get("power", 25))
            region    = params.get("region", "EU3")
            antennas  = params.get("antennas", [1])
            filter = params.get("filter", None)
            bank = params.get("bank", ["epc"])
            power = power *100
            if filter is not None:
                filter_epc = filter.get("epc",None)
                filter_offset = filter.get("offset",None)
            if readActive is True:            
                reader.stop_reading()
                readActive = False
            if filter is None or filter_offset is None:
                filter_offset = 32
            else:
                filter_offset =  int(filter_offset)*4 + 32
            if filter_epc is not None:
                filter_epc_hex = filter_epc.encode('utf-8')
            if filter is not None:
                reader.set_read_plan(antennas,"GEN2",bank=bank, read_power=power, epc_target={'epc':filter_epc_hex,'bit':filter_offset,'len':len(filter_epc)*4})
            else:
                reader.set_read_plan(antennas,"GEN2",bank=bank, read_power=power)
            reader.set_region(region)
            reader.enable_exception_handler(exception_handler)
            reader.start_reading(readingCallback)
            readActive = True
        except Exception as e:
            readActive = False
            print("Error during start read:", e)
            client.publish(TOPIC_ERROR,str(e))
        
    elif topic == TOPIC_STOP:
        print("Stopping read...")
        reader.stop_reading()
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