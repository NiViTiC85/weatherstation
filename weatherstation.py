#!/usr/bin/env python3
import glob, time, json, serial, paho.mqtt.client as mqtt

# ======================================================
# KONFIGURATION
# ------------------------------------------------------
# - SER_PORT   : Hitta första Arduino-port (ex. /dev/ttyACM0)
# - SER_BAUD   : Baudrate, måste matcha Arduino-koden
# - TEMP_FILE  : Fil för DS18B20 (1-Wire), första hittade sensor
# - MQTT_*     : Broker-inställningar
# - TOPIC_*    : MQTT topics för vindhastighet & temperatur
# ======================================================
SER_PORT = glob.glob("/dev/ttyACM*")[0]
SER_BAUD = 115200
TEMP_FILE = glob.glob('/sys/bus/w1/devices/28-*/w1_slave')[0]
MQTT_HOST, MQTT_PORT = "100.82.0.4", 1883
TOPIC_WIND, TOPIC_TEMP = "pi9/sensor/1", "pi9/sensor/2"


# ======================================================
# FUNKTION: Läs temperatur från DS18B20
# ------------------------------------------------------
# - Öppnar sensorfilen (två rader text).
# - Kontroll: rad 1 måste innehålla "YES" (CRC OK).
# - Rad 2 innehåller temperatur i milligrader efter "t=".
# - Returnerar temperatur i °C (float) eller None om fel.
# ======================================================
def read_temp():
    with open(TEMP_FILE) as f:
        lines = f.readlines()
    if "YES" in lines[0]:
        return int(lines[1].split("t=")[1]) / 1000
    return None


# ======================================================
# INITIERA SERIEPORT & MQTT
# ------------------------------------------------------
# - Serieport: öppna kommunikation mot Arduino.
# - MQTT: anslut klient till broker och starta loop.
# ======================================================
ser = serial.Serial(SER_PORT, SER_BAUD, timeout=0.2)
client = mqtt.Client()
client.username_pw_set("elektronik", "elektronik")
client.connect(MQTT_HOST, MQTT_PORT, 60)
client.loop_start()


# ======================================================
# HUVUDLOOP
# ------------------------------------------------------
# - Vinddata: läses kontinuerligt från Arduino (JSON).
# - Temperatur: läses från DS18B20 en gång per sekund.
# - MQTT: båda värdena skickas till respektive topic.
# - Debug: skriver ut kombinerad JSON till terminalen.
# ======================================================
while True:
    wind, temp = None, None

    # --- Vind från Arduino ---
    try:
        ser.reset_input_buffer()   # rensa gammal buffrad data
        line = ser.readline().decode().strip()
        if line:
            wind = json.loads(line).get("ws_ms")
    except:
        pass

    # --- Temperatur (1 ggr/s) ---
    if int(time.time()) % 1 == 0:
        temp = read_temp()

    # --- Publicera till MQTT ---
    if wind is not None:
        client.publish(TOPIC_WIND, round(wind, 2))
    if temp is not None:
        client.publish(TOPIC_TEMP, round(temp, 2))

    # --- Debug till terminal ---
    if wind is not None and temp is not None:
        print(json.dumps({"ws_ms": round(wind,2), "temp_c": round(temp,2)}))

    time.sleep(0.1)  # kort paus → hinner läsa nytt
