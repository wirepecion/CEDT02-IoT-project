#!/usr/bin/env python3
"""Raspberry Pi 5: read JSON lines from the ESP32 over UART and upload them to the gateway.

ESP32 line: {"temp":28.4,"hum":61.0,"gas":1200,"light":900,"dist":35.2}

Env:  DEVICE_TOKEN (required), UPLINK_URL (e.g. https://<machine>.<tailnet>.ts.net/write),
      DEVICE_ID (default pi5-01), SERIAL_PORT (default /dev/serial0, or /dev/ttyAMA0)
Needs: pip install pyserial requests
Merge send() into your monitor.py if you prefer one script.
"""
import json, os, sys, time

import requests
import serial

URL = os.environ.get("UPLINK_URL")
TOKEN = os.environ.get("DEVICE_TOKEN")
DEVICE = os.environ.get("DEVICE_ID", "pi5-01")
PORT = os.environ.get("SERIAL_PORT", "/dev/serial0")


def to_line(d):
    # The ESP32 sends -1 when a sensor read fails: skip those fields.
    parts = []
    if d.get("temp", -1) != -1:
        parts.append(f"temperature={float(d['temp'])}")
    if d.get("hum", -1) != -1:
        parts.append(f"humidity={float(d['hum'])}")
    if "gas" in d:
        parts.append(f"gas={int(d['gas'])}i")
    if "light" in d:
        parts.append(f"light={int(d['light'])}i")
    if d.get("dist", -1) != -1:
        parts.append(f"distance={float(d['dist'])}")
    if not parts:
        return None
    return f"sensor_readings,device_id={DEVICE} {','.join(parts)}\n"


def send(line):
    try:
        r = requests.post(URL, data=line, headers={"Authorization": f"Bearer {TOKEN}"}, timeout=5)
        return r.status_code
    except requests.RequestException as e:
        return f"error: {e}"


def main():
    if not URL or not TOKEN:
        sys.exit("set UPLINK_URL and DEVICE_TOKEN")
    with serial.Serial(PORT, 9600, timeout=2) as ser:
        while True:
            raw = ser.readline().decode(errors="ignore").strip()
            if not raw:
                continue
            try:
                line = to_line(json.loads(raw))
            except (ValueError, TypeError):
                continue  # garbled UART line
            if line:
                print(raw, "->", send(line), flush=True)  # a failed upload just drops this reading


if __name__ == "__main__":
    main()
