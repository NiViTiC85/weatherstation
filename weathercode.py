import os
import glob
import time

# Initiera 1-wire-gränssnittet
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

# Hitta device-fil (börjar med 28-)
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

# Funktion för att läsa rådata från sensorn
def read_temp_raw():
    with open(device_file, 'r') as f:
        return f.readlines()

# Funktion för att tolka temperatur
def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos + 2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c

# Exempel: skriv ut temperatur varannan sekund
while True:
    temp = read_temp()
    print(f"Temperatur: {temp:.2f} °C")
    time.sleep(2)
