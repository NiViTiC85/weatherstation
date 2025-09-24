/*
  Vindhastighetsmätning med CG-FS / QS-FS sensor
  ------------------------------------------------
  - Sensorutgång: 0.4 V (vid 0 m/s) till 2.0 V (vid 32.4 m/s)
  - Matning: 7–24 V (separat från Arduino, men GND måste kopplas ihop!)
  - Utgången (blå kabel) kopplas till Arduino A0

  Formeln enligt datablad (laskakit.cz):
      wind_speed [m/s] = (Vout - 0.4) / 1.6 * 32.4

  Där:
    Vout = mätt spänning (Volt)
    0.4  = offset (Volt, motsvarar 0 m/s)
    1.6  = spänningsspann (Volt, dvs 2.0 - 0.4)
    32.4 = max vindhastighet (m/s)

  Programmet:
  - Läser analog ingång A0
  - Omvandlar ADC-värde till Volt
  - Räknar ut vindhastighet i m/s med formeln ovan
  - Medelvärdesfiltrerar de senaste 10 mätningarna (för att minska brus)
  - Skickar resultatet till datorn via Serial som JSON varje sekund
*/

const int PIN_WS = A0;      // Vindhastighetssensorns utgång ansluten till A0
const float VREF = 5.0;     // Referensspänning för Arduino (5V om USB/extern 5V)
const int ADC_MAX = 1023;   // 10-bitars ADC ger värden 0–1023

// Parametrar från datablad
const float V_OFFSET = 0.4; // Spänning vid 0 m/s
const float V_RANGE  = 1.6; // Skillnad (2.0 - 0.4 V)
const float WS_MAX   = 32.4;// Max vindhastighet (m/s)

// Buffert för att beräkna glidande medelvärde
const int N = 10;           // Antal prover i medelvärdet
float buffer[N];            // Array med senaste N värden
int idx = 0;                // Position i arrayen
int count = 0;              // Räknare hur många värden vi hunnit fylla

void setup() {
  Serial.begin(115200);     // Starta seriell kommunikation (115200 baud)
  analogReference(DEFAULT); // Använd standardreferens = 5V på Arduino Uno/Nano
  // Initiera bufferten till noll
  for (int i = 0; i < N; i++) {
    buffer[i] = 0.0;
  }
}

/*
  Funktion: readWind_ms
  ----------------------
  Läser en rå ADC-signal från A0, omvandlar till Volt
  och räknar ut vindhastighet (m/s) enligt databladet.
*/
float readWind_ms() {
  int raw = analogRead(PIN_WS);          // Läs analogt värde (0–1023)
  float v = (raw * VREF) / ADC_MAX;      // Omvandla till Volt (0–5 V)

  // Använd databladets formel
  float ws = (v - V_OFFSET) / V_RANGE * WS_MAX;

  // Säkerhetsklamp: om resultatet blir negativt, sätt till 0
  if (ws < 0) {
    ws = 0;
  }
  return ws;
}

void loop() {
  // 1. Läs en ny vindhastighet
  float ws = readWind_ms();

  // 2. Lägg in värdet i bufferten
  buffer[idx] = ws;
  idx = (idx + 1) % N;   // Cirkulär indexering (0 → N-1, sedan börja om)
  if (count < N) {
    count++;             // Räkna upp tills bufferten är full
  }

  // 3. Beräkna medelvärdet
  float sum = 0.0;
  for (int i = 0; i < count; i++) {
    sum += buffer[i];
  }
  float ws_avg = sum / count;

  // 4. Skriv ut resultatet via seriell port i JSON-format
  //    Exempel: {"ws_ms": 3.45}
  Serial.print("{\"ws_ms\":");
  Serial.print(ws_avg, 2); // två decimaler
  Serial.println("}");

  // 5. Vänta en sekund innan nästa utskrift (≈ 1 Hz uppdatering)
  delay(1000);
}
