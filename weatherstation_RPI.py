#!/usr/bin/env python3
import os, glob, time, json, serial
import paho.mqtt.client as mqtt

"""
  Väderstation: Vindhastighet (Arduino) + Temperatur (DS18B20) → MQTT
  -------------------------------------------------------------------
  - Arduino skickar vindhastighet i JSON-format via USB/seriell:
      {"ws_ms": 1.57}
  - Raspberry Pi läser DS18B20 via 1-Wire (filbaserad åtkomst).
  - Båda värden publiceras till MQTT-broker.

  MQTT-konfiguration (exempel):
    Host: 100.82.0.4
    Port: 1883
    User: elektronik
    Pass: elektronik
    Topics:
      pi11/sensor/1   → Vindhastighet (m/s)
      pi11/sensor/2   → Temperatur (°C)

  Programmet:
  1. Initierar 1-Wire för DS18B20.
  2. Hittar Arduinons serieport (/dev/ttyACM* eller /dev/ttyUSB*).
  3. Läser kontinuerligt:
       - Vindhastighet (JSON från Arduino).
       - Temperatur (från DS18B20, en gång per sekund).
  4. Publicerar båda värdena till MQTT.
  5. Skriver även ut en kombinerad JSON-rad för debug:
       {"ws_ms": 1.57, "temp_c": 22.88}
"""

# ================== KONFIG ==================
SER_BAUD = 115200        # Baudrate måste matcha Serial.begin() i Arduino
SER_TIMEOUT = 0.2        # Timeout (sek) vid serieläsning

TEMP_PERIOD = 1.0        # Sekunder mellan temp-avläsningar

# MQTT-inställningar för broker
MQTT_HOST = "100.82.0.4"
MQTT_PORT = 1883
MQTT_USER = "elektronik"
MQTT_PASS = "elektronik"

# MQTT-topics (byt "pi11" till ditt RPi-ID)
TOPIC_WS   = "pi11/sensor/1"   # Vindhastighet (m/s)
TOPIC_TEMP = "pi11/sensor/2"   # Temperatur (°C)
# ============================================

def find_serial_port():
    """
    Försök hitta Arduino-porten på Linux.
    Vanliga namn: /dev/ttyACM0 eller /dev/ttyUSB0.
    Returnerar portnamn (sträng) eller None om inget hittas.
    """
    candidates = glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*")
    return candidates[0] if candidates else None

# --- DS18B20 (temperatur) ---
def init_1wire():
    """
    Ladda kernelmoduler för 1-Wire om de inte redan är laddade.
    Gör att DS18B20 exponeras i /sys/bus/w1/devices/28-xxxx/w1_slave.
    """
    os.system('modprobe w1-gpio')
    os.system('modprobe w1-therm')

def read_temp_c():
    """
    Läs temperatur i °C från DS18B20.
    Returnerar float (t.ex. 22.81) eller None om läsningen misslyckas.
    """
    base_dir = '/sys/bus/w1/devices/'
    devices = glob.glob(base_dir + '28-*')   # alla DS18B20 börjar med "28-"
    if not devices:
        return None
    device_file = devices[0] + '/w1_slave'
    try:
        with open(device_file, 'r') as f:
            lines = f.readlines()
        # Första raden måste sluta på "YES" (CRC OK)
        if lines[0].strip()[-3:] != 'YES':
            return None
        # Andra raden innehåller "t=<milligrader>"
        pos = lines[1].find('t=')
        if pos != -1:
            t_mC = int(lines[1][pos+2:])   # milligrader Celsius
            return t_mC / 1000.0
    except Exception:
        return None
    return None


def main():
    # 1. Initiera 1-Wire
    init_1wire()

    # 2. Hitta Arduino-port
    port = find_serial_port()
    if not port:
        print("Hittade ingen serieport (/dev/ttyACM* eller /dev/ttyUSB*).")
        return
    print(f"Öppnar serieport: {port}")
    ser = serial.Serial(port, SER_BAUD, timeout=SER_TIMEOUT)

    # 3. Initiera MQTT-klient och anslut
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()

    last_temp_pub = 0.0   # Tidpunkt för senaste temp-uppdatering
    temp_c = None         # Senaste kända temperatur

    try:
        while True:
            ws = None  # Vindhastighet (m/s)

            # --- Läs vind från Arduino (JSON-rad) ---
            try:
                line = ser.readline().decode(errors="ignore").strip()
                if line:
                    try:
                        payload = json.loads(line)      # {"ws_ms":...}
                        ws = float(payload.get("ws_ms", 0.0))
                    except Exception:
                        pass  # ogiltig rad → hoppa
            except Exception:
                pass  # problem med serial → hoppa

            # --- Läs temperatur en gång per sekund ---
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

            # --- Debugutskrift till terminal ---
            if ws is not None and temp_c is not None:
                combined = {"ws_ms": round(ws, 2), "temp_c": round(temp_c, 2)}
                print(json.dumps(combined))

            time.sleep(0.05)  # vila lite för att inte belasta CPU onödigt mycket

    except KeyboardInterrupt:
        # Avsluta snyggt med Ctrl+C
        pass
    finally:
        ser.close()
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
