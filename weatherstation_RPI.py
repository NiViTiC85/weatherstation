#!/usr/bin/env python3
import os, glob, time, json, serial
import paho.mqtt.client as mqtt

# ================== KONFIG ==================
SER_BAUD = 115200
SER_TIMEOUT = 0.2   # kort timeout
TEMP_PERIOD = 1.0   # sek mellan temp-uppdateringar
MQTT_HOST = "100.82.0.4"
MQTT_PORT = 1883
MQTT_USER = "elektronik"
MQTT_PASS = "elektronik"
TOPIC_WS   = "pi11/sensor/1"
TOPIC_TEMP = "pi11/sensor/2"
# ============================================

def find_serial_port():
    """Försök hitta Arduino-porten på Linux."""
    candidates = glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*")
    return candidates[0] if candidates else None

# --- DS18B20 ---
def init_1wire():
    os.system('modprobe w1-gpio')
    os.system('modprobe w1-therm')

def read_temp_c():
    base_dir = '/sys/bus/w1/devices/'
    devices = glob.glob(base_dir + '28-*')
    if not devices:
        return None
    device_file = devices[0] + '/w1_slave'
    try:
        with open(device_file, 'r') as f:
            lines = f.readlines()
        if lines[0].strip()[-3:] != 'YES':
            return None
        pos = lines[1].find('t=')
        if pos != -1:
            t_mC = int(lines[1][pos+2:])
            return t_mC / 1000.0
    except Exception:
        return None
    return None

def main():
    init_1wire()

    port = find_serial_port()
    if not port:
        print("Hittade ingen serieport (/dev/ttyACM* eller /dev/ttyUSB*).")
        return
    print(f"Öppnar serieport: {port}")
    ser = serial.Serial(port, SER_BAUD, timeout=SER_TIMEOUT)

    # --- Initiera MQTT ---
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()

    last_temp_pub = 0.0
    temp_c = None

    try:
        while True:
            ws = None

            # --- Läs en rad från Arduino ---
            try:
                line = ser.readline().decode(errors="ignore").strip()
                if line:
                    try:
                        payload = json.loads(line)      # {"ws_ms":...}
                        ws = float(payload.get("ws_ms", 0.0))
                    except Exception:
                        pass
            except Exception:
                pass

            # --- Läs temp varje sekund ---
            now = time.time()
            if now - last_temp_pub >= TEMP_PERIOD:
                tc = read_temp_c()
                if tc is not None:
                    temp_c = tc
                last_temp_pub = now

            # --- Publicera till MQTT ---
            if ws is not None:
                client.publish(TOPIC_WS, round(ws, 2))
            if temp_c is not None:
                client.publish(TOPIC_TEMP, round(temp_c, 2))

            # --- Debugutskrift ---
            if ws is not None and temp_c is not None:
                combined = {"ws_ms": round(ws, 2), "temp_c": round(temp_c, 2)}
                print(json.dumps(combined))

            time.sleep(0.05)

    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
