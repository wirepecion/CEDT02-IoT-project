# Database access setup: server, friend, Raspberry Pi

Stack: QuestDB (matches the `Caddyfile`). Files already edited for this setup:
`docker-compose.yml`, `Caddyfile`, `schema.sql`, `.env` (secrets, do not share), `pi_uplink.py` (runs on the Pi).

**Rules**

- Never expose DB ports directly to the internet.
- The friend reaches the DB over Tailscale only.
- Devices write only through the Caddy HTTPS gateway, one token per device.

**Two values you must fill in** (in `.env`):

| Variable | What | How to get it |
|---|---|---|
| `TAILSCALE_IP` | Server's Tailscale IP, e.g. `100.x.y.z` | `tailscale ip -4` on the server |
| `DOMAIN` | e.g. `iot.example.com` | Your domain, pointing at the server |

---

## 1. Server side

### Prepare

- Linux machine that stays on, with Docker and Docker Compose
- Free Tailscale account
- Domain name (or Cloudflare Tunnel / Tailscale Funnel if behind home NAT)
- Caddy installed (`sudo apt install caddy`, or use the `caddy:2` Docker image)

### Step 1: Install Tailscale

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale ip -4
```

Put the printed IP into `.env` as `TAILSCALE_IP=...`. Put your domain in as `DOMAIN=...`.

### Step 2: Start QuestDB

Keep your existing `TS_PASSWORD` exported (the TimescaleDB data was created with it). The other secrets are already in `.env`, which Docker Compose reads automatically.

```bash
export TS_PASSWORD='your-existing-password'
docker compose up -d questdb
docker compose ps
```

This recreates the `questdb` container. The data in `./data/questdb` is kept. The container now:

- uses image `questdb/questdb:10.2.0` (the version that was running)
- uses login `friend_admin` with `QDB_PASSWORD` from `.env`, instead of the default `admin/quest`
- listens on `127.0.0.1` for you and Caddy, and on `TAILSCALE_IP` for your friend (ports 9000 and 8812)

### Step 3: Create the table

Open http://localhost:9000 and paste the QuestDB block from `schema.sql`. It already has the `gas`, `light` and `distance` columns.

### Step 4: Start the HTTPS gateway

Open ports 80 and 443 on the server and point `DOMAIN` at it. Then:

```bash
set -a; . ./.env; set +a
caddy run --config Caddyfile
```

Each device has its own token in `.env` (`TOKEN_PI5`, `TOKEN_TEST`). To add a device, add a `TOKEN_<NAME>` line and one `@name header ...` + `reverse_proxy @name ...` pair in the `Caddyfile`.

### Step 5: Test the gateway from another machine

No token, expect `401`:

```bash
curl -i -X POST https://<DOMAIN>/write -d 'x a=1'
```

With a token, expect `204`:

```bash
curl -i -X POST https://<DOMAIN>/write \
  -H "Authorization: Bearer <TOKEN_TEST>" \
  --data-binary 'sensor_readings,device_id=test temperature=25,humidity=50'
```

### Step 6: Share with your friend

In the Tailscale admin console, share this machine with your friend's account. Send them `friend_admin` and the `QDB_PASSWORD` value privately.

---

## 2. Friend side

### Prepare

- Laptop and a Tailscale account
- `psql` or any SQL client (DBeaver, etc.)
- The username `friend_admin`, the password, and the server's `TAILSCALE_IP`

### Step 1: Install Tailscale

Install it and sign in.

### Step 2: Accept the share

Accept the machine share from the server owner, then check:

```bash
tailscale ping <TAILSCALE_IP>
```

### Step 3: Connect

Web console: open `http://<TAILSCALE_IP>:9000` in a browser.

Or SQL:

```bash
psql -h <TAILSCALE_IP> -p 8812 -U friend_admin -d qdb
```

### Step 4: Check it works

```sql
SELECT device_id, count(), avg(temperature) FROM sensor_readings GROUP BY device_id;
```

---

## 3. Raspberry Pi 5 side

### Prepare

- Pi 5 with Raspberry Pi OS, on WiFi or Ethernet
- ESP32 wired over UART as in `ESP32-S3_Pi5_guide.md`
- Copy `pi_uplink.py` to the Pi
- The Pi's token (`TOKEN_PI5` from `.env`) and the URL `https://<DOMAIN>/write`

### Step 1: Test the connection from the Pi

```bash
curl -i -X POST https://<DOMAIN>/write \
  -H "Authorization: Bearer <TOKEN_PI5>" \
  --data-binary 'sensor_readings,device_id=pi5-01 temperature=28.4,humidity=61'
```

Expect `204`.

### Step 2: Install the libraries

```bash
pip install pyserial requests
```

### Step 3: Store the token

Create `/etc/default/pi-uplink` (then `sudo chmod 600` it):

```bash
DEVICE_TOKEN=<TOKEN_PI5>
UPLINK_URL=https://<DOMAIN>/write
DEVICE_ID=pi5-01
SERIAL_PORT=/dev/serial0
```

Use `/dev/ttyAMA0` if `/dev/serial0` does not exist.

### Step 4: Run it

```bash
set -a; . /etc/default/pi-uplink; set +a
python3 pi_uplink.py
```

You should see each ESP32 JSON line followed by `-> 204`. A failed upload only drops that one reading.

### Step 5: Run it at boot

Create `/etc/systemd/system/pi-uplink.service`:

```ini
[Unit]
Description=ESP32 to QuestDB uplink
After=network-online.target

[Service]
EnvironmentFile=/etc/default/pi-uplink
ExecStart=/usr/bin/python3 /home/pi/pi_uplink.py
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

Adjust `User` and the script path to yours, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pi-uplink
```

### Step 6: Check on the server

```sql
SELECT * FROM sensor_readings WHERE device_id = 'pi5-01' ORDER BY ts DESC LIMIT 5;
```

The ESP32 only talks to the Pi over UART, so it needs no token.

---

## Checklist before sharing

- [ ] `TAILSCALE_IP` and `DOMAIN` filled in `.env`
- [ ] `docker compose up -d questdb` ran, default `admin/quest` login no longer works
- [ ] `401` without a token, `204` with a token
- [ ] Only ports 80 and 443 open to the internet; DB ports on localhost or the Tailscale IP only
- [ ] `.env` is `chmod 600` and not shared or committed
- [ ] Remove the `@test` matcher and `TOKEN_TEST` once testing is finished
