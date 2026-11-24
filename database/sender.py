#!/usr/bin/env python3
"""Simulated IoT device: sends fake temperature/humidity readings.

Usage:
  python3 sender.py questdb  http://localhost:9000
  python3 sender.py greptime http://localhost:4000
  python3 sender.py timescale "postgresql://postgres:PASSWORD@localhost:5432/pilot"   (needs: pip install psycopg[binary])

Optional env: DEVICE_ID (default sim-01), DEVICE_TOKEN (sent as Bearer token, for use behind a proxy),
              INTERVAL seconds (default 2), COUNT (default 30)
"""
import os, random, sys, time, urllib.request

device = os.environ.get("DEVICE_ID", "sim-01")
token = os.environ.get("DEVICE_TOKEN")
interval = float(os.environ.get("INTERVAL", "2"))
count = int(os.environ.get("COUNT", "30"))


def reading():
    return round(random.uniform(24, 34), 2), round(random.uniform(40, 80), 2)


def post_line(url, line):
    req = urllib.request.Request(url, data=line.encode(), method="POST")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    target, endpoint = sys.argv[1], sys.argv[2].rstrip("/")
    conn = None
    if target == "timescale":
        import psycopg
        conn = psycopg.connect(endpoint, autocommit=True)
    for i in range(count):
        t, h = reading()
        # InfluxDB line protocol; timestamp omitted -> server time
        line = f"sensor_readings,device_id={device} temperature={t},humidity={h}\n"
        if target == "questdb":
            status = post_line(f"{endpoint}/write", line)
        elif target == "greptime":
            status = post_line(f"{endpoint}/v1/influxdb/write?db=public", line)
        elif target == "timescale":
            conn.execute(
                "INSERT INTO sensor_readings (time, device_id, temperature, humidity) VALUES (now(), %s, %s, %s)",
                (device, t, h),
            )
            status = "ok"
        else:
            sys.exit("target must be questdb, greptime or timescale")
        print(f"{i + 1}/{count} {device} t={t} h={h} -> {status}")
        time.sleep(interval)


if __name__ == "__main__":
    main()
