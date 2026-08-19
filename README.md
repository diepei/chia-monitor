# Chia Monitor

A small, private Chia farm monitor designed to answer one question quickly: **is my farm healthy?** It combines a read-only Python agent, a phone-first PWA, and an iPhone Scriptable widget.

## What it shows

- Farmer, node sync, plots, farm size, harvesters, and latest signage activity
- Configured disks, space used, temperature, and SMART health
- Estimated time to win from current farm and network space
- XCH balance, farming rewards, and blocks won
- Missing/failed plots, actionable alerts, and a 0–100 health score

The agent talks only to Chia RPC on `127.0.0.1` with Chia's local SSL certificates. It never reads or returns seed phrases, private keys, or wallet keys. RPC ports must remain private.

## 1. Install the agent on the farming PC

Python 3.9+ and a running Chia farmer, full node, harvester, and wallet are recommended.

```bash
cd agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Put the generated token in `config.yaml`. Set `chia_root` and list only the farm disks you want monitored. Install `smartmontools` for SMART readings. The agent still runs when `smartctl` is unavailable.

```bash
python -m chia_monitor.main --config config.yaml
curl http://127.0.0.1:8926/healthz
```

`chia-monitor.service` is an optional hardened systemd unit. Adjust its user and paths, copy it to `/etc/systemd/system/`, then enable it with `sudo systemctl enable --now chia-monitor`.

## 2. Run the PWA

```bash
npm install
npm run dev
```

Open the dashboard, tap **Demo**, and enter the agent URL and token. Both remain in that browser's local storage. Add the page to your phone's Home Screen. When dashboard and agent use different origins, add the dashboard's exact origin to `allowed_origins` in `agent/config.yaml`; do not use `*`.

## 3. Add the iPhone widget

1. Install [Scriptable](https://scriptable.app/) and create a new script.
2. Paste in `ChiaWidget.js`.
3. Set `AGENT_URL` and `API_TOKEN` at the top.
4. Add a medium Scriptable widget to the Home Screen and select the script.

The widget requests a refresh about every 15 minutes (iOS controls the actual schedule) and creates a local notification the first time it sees a new alert.

## Secure remote access with Tailscale

Tailscale lets you check the farm away from home without publishing Chia RPC or the agent to the internet.

1. Install Tailscale on the farming PC and iPhone, and sign both into the same tailnet.
2. Keep the agent on `127.0.0.1:8926`.
3. Expose only the agent over tailnet HTTPS: `tailscale serve --bg https+insecure://localhost:8926`.
4. Use the HTTPS `*.ts.net` URL shown by `tailscale serve status` in the PWA and Scriptable.
5. Optionally add a Tailscale ACL allowing only your phone/user to reach the farming PC.

Never port-forward Chia's `8555`, `8559`, `8560`, or `9256` RPC ports. Never commit `config.yaml`, your API token, or Chia SSL/private-key files.

## API and scoring

Farm-data routes require `Authorization: Bearer <token>`:

- `GET /api/status` — complete dashboard payload
- `GET /api/widget` — compact widget payload with at most three alerts
- `GET /healthz` — unauthenticated process liveness only

The collector caches a snapshot for 30 seconds by default. Health starts at 100: a critical condition costs 25 points and a warning costs 10. This is only a monitor—there are no wallet-send, plot, key, or start/stop endpoints.

## Verify

```bash
cd agent && .venv/bin/python -m pytest
cd .. && npm run build
```
