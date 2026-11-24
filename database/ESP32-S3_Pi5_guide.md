# ESP32-S3 + Raspberry Pi 5 sensor monitor

*Update guide for the ESP32-S3-N16R8 board*

---

> ✅ **You're right.** The ESP32-S3 and the Pi 5 are both **3.3V logic**, so TX/RX connect directly with **no resistors**. The divider I gave earlier was only for the 5V Arduino Uno.

This board is an **ESP32-S3-N16R8**, not an Arduino, so a few other things change. Here is the full update.

---

## 1. Pin changes

Avoid GPIO 35–37 (used by the N16R8's PSRAM) and 19–20 (USB). The pins below are safe.

| Module | Connection | ESP32-S3 |
|---|---|---|
| KY-015 (DHT11) | S / middle / − | GPIO6 / 3V3 / GND |
| KY-018 (light) | S / middle / − | GPIO5 / 3V3 / GND |
| MQ135 | VCC, GND, AO | 5V, GND, **GPIO4 via divider** |
| HY-SRF05 | VCC, TRIG, ECHO, GND (OUT empty) | 5V, GPIO7, **GPIO15 via divider**, GND |

> ⚠️ **ESP32 pins are not 5V tolerant.** These two lines need a divider:
>
> - **MQ135 AO** (up to 5V): `AO → 10kΩ → GPIO4 → 15kΩ → GND`
> - **HY-SRF05 ECHO** (5V): `ECHO → 1kΩ → GPIO15 → 2kΩ → GND`

Find the **5V** pin on the board's silkscreen. When powered by USB-C, it carries 5V for the MQ135 and HY-SRF05.

---

## 2. UART to the Pi 5 (direct, no resistors)

| ESP32-S3 | Pi 5 |
|---|---|
| GPIO17 (TX) | GPIO15 / RXD (pin 10) |
| GPIO18 (RX) | GPIO14 / TXD (pin 8) |
| GND | GND (pin 6) |

I avoid the board's labeled TX/RX pins (GPIO43/44) because they are shared with the USB-serial console.

Buzzer on the Pi is unchanged: S → GPIO18 (pin 12), − → GND.

---

## 3. ESP32-S3 code

In Arduino IDE, install **"esp32 by Espressif"** in Boards Manager and the Adafruit **DHT sensor library**. Settings:

| Setting | Value |
|---|---|
| Board | **ESP32S3 Dev Module** |
| PSRAM | **OPI PSRAM** |
| Flash Size | **16MB** |
| USB CDC On Boot | **Disabled** |
| Upload port | USB-C port labeled **UART** (the other is native USB) |

```cpp
#include <DHT.h>

#define DHTPIN   6
#define DHTTYPE  DHT11
#define TRIG     7
#define ECHO     15
#define GAS_PIN  4
#define LDR_PIN  5

DHT dht(DHTPIN, DHTTYPE);
HardwareSerial piSerial(1);   // UART1

float readDistanceCm() {
  digitalWrite(TRIG, LOW);  delayMicroseconds(2);
  digitalWrite(TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(TRIG, LOW);
  long t = pulseIn(ECHO, HIGH, 30000);
  return t ? t * 0.0343 / 2 : -1;
}

void setup() {
  Serial.begin(115200);                       // debug over USB
  piSerial.begin(9600, SERIAL_8N1, 18, 17);   // RX=18, TX=17
  dht.begin();
  pinMode(TRIG, OUTPUT);
  pinMode(ECHO, INPUT);
  analogReadResolution(12);                   // 0-4095
}

void loop() {
  float t   = dht.readTemperature();
  float h   = dht.readHumidity();
  int gas   = analogRead(GAS_PIN);
  int light = analogRead(LDR_PIN);
  float d   = readDistanceCm();

  String msg = "{\"temp\":"  + String(isnan(t) ? -1 : t, 1) +
               ",\"hum\":"   + String(isnan(h) ? -1 : h, 1) +
               ",\"gas\":"   + gas +
               ",\"light\":" + light +
               ",\"dist\":"  + String(d, 1) + "}";

  piSerial.println(msg);
  Serial.println(msg);
  delay(2000);
}
```

---

## 4. Pi 5 side

```bash
sudo raspi-config
# Interface Options → Serial Port
#   Login shell over serial?  → No
#   Serial hardware enabled?  → Yes
sudo reboot
pip install pyserial
```

`monitor.py` is **the same as before**, with two changes:

- The ADC is now **12-bit (0–4095)**, so retune `GAS_LIMIT` from your own readings (the old 400 was for 0–1023).
- If `/dev/serial0` doesn't exist, use `/dev/ttyAMA0`.

> ℹ️ **Pi 5 note:** `gpiozero` works, but the old `RPi.GPIO` library does not.

---

## 5. Test order

1. Upload the ESP32 code and check the JSON in Serial Monitor (**115200 baud**).
2. Wire the UART and run `python3 monitor.py`.
3. Warm up the MQ135 for 3–5 min, then set `GAS_LIMIT`.
4. Move a hand toward the HY-SRF05 to trigger the buzzer and the photo.

> 📷 **Camera warning:** the Pi 5 has smaller 22-pin camera connectors. An older camera cable needs a Pi 5 adapter cable.
