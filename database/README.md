# Time-series DB pilot: runbook

Files: `docker-compose.yml`, `schema.sql`, `sender.py`, `Caddyfile`

## 1. Start
```bash
export TS_PASSWORD='choose-a-strong-password'
docker compose up -d            # or: docker compose up -d questdb
docker compose ps
```

## 2. Create tables
- TimescaleDB: `docker exec -i tsdb psql -U postgres -d pilot < schema.sql`
- QuestDB: paste the commented block into http://localhost:9000
- GreptimeDB: `psql -h 127.0.0.1 -p 4003 -d public`, paste the commented block

## 3. Send test data
```bash
python3 sender.py questdb  http://localhost:9000
python3 sender.py greptime http://localhost:4000
pip install "psycopg[binary]" && python3 sender.py timescale "postgresql://postgres:$TS_PASSWORD@localhost:5432/pilot"
```

## 4. Check the data
```sql
SELECT device_id, count(*), avg(temperature) FROM sensor_readings GROUP BY device_id;
```

## 5. Share with a friend / real devices
- Friend: install Tailscale on server and laptop, share the machine, bind compose ports to the Tailscale IP, give a read-only DB role.
- IoT devices: send InfluxDB line protocol over HTTPS through the Caddy gateway, one token per device.
- Never expose DB ports directly to the internet.

## 6. Pilot measurements to record
| Metric | How |
|---|---|
| Ingest rows/sec per DB | run several `sender.py` in parallel (set INTERVAL=0.01) |
| Query latency (last hour avg, per-device) | time the SQL above at 1M and 10M rows |
| Disk per million rows | `du -sh data/<db>` before/after |
| RAM/CPU | `docker stats` |

## 7. Backup and cleanup
- Stop first, then copy `./data/`: `docker compose stop && tar czf backup.tgz data && docker compose start`
- Remove everything: `docker compose down` then delete `./data/` (irreversible).
