#!/usr/bin/env bash
# Paste this entire script into the iOS Shortcuts “Run Script over SSH” action.
# It is executed from memory; it does not install or persist anything on the miner.
set -u

PYTHON_BIN="$(command -v python3 2>/dev/null || true)"
if [ -z "$PYTHON_BIN" ] && [ -x "$HOME/chia-blockchain/venv/bin/python" ]; then
  PYTHON_BIN="$HOME/chia-blockchain/venv/bin/python"
fi
if [ -z "$PYTHON_BIN" ]; then
  printf '%s\n' '{"status":"critical","score":"0","alert":"Python 3 not found","updated":"Never"}'
  exit 0
fi

"$PYTHON_BIN" - <<'PY'
import datetime
import json
import os
import re
import shutil
import subprocess
import time


def chia_binary():
    found = shutil.which("chia")
    if found:
        return found
    candidate = os.path.expanduser("~/chia-blockchain/venv/bin/chia")
    return candidate if os.path.isfile(candidate) else None


def run(chia, *args):
    if not chia:
        return "Chia command not found"
    try:
        return subprocess.run([chia, *args], capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception as error:
        return str(error)


def match(pattern, text, default="—"):
    result = re.search(pattern, text, re.I)
    return result.group(1).strip() if result else default


chia = chia_binary()
farm = run(chia, "farm", "summary")
node = run(chia, "show", "-s")

plots_raw = match(r"(?:Plot count|Total plots):\s*([\d,]+)", farm, "0")
try:
    plots_number = int(plots_raw.replace(",", ""))
except ValueError:
    plots_number = 0

size = match(r"Total size of plots:\s*([\d.]+\s*(?:TiB|PiB|GiB))", farm)
etw = match(r"Expected time to win:\s*([^\n]+)", farm)
synced = bool(re.search(r"Sync status:\s*Synced", node, re.I)) or (
    "Synced" in node and "Not Synced" not in node
)
farmer_online = plots_number > 0 and not re.search(
    r"connection error|not running|failed to connect|chia command not found", farm, re.I
)

activity_seconds = None
log_path = os.path.expanduser("~/.chia/mainnet/log/debug.log")
try:
    with open(log_path, "rb") as handle:
        handle.seek(max(0, os.path.getsize(log_path) - 1_000_000))
        lines = handle.read().decode("utf-8", "ignore").splitlines()
    for line in reversed(lines):
        if "Signage point" in line or "eligible for farming" in line:
            stamp = datetime.datetime.fromisoformat(line[:19])
            activity_seconds = max(0, int(time.time() - stamp.timestamp()))
            break
except Exception:
    pass

alerts = []
if not farmer_online:
    alerts.append("Farmer offline or no active plots")
if not synced:
    alerts.append("Full node is not synced")
if activity_seconds is not None and activity_seconds > 300:
    alerts.append("No recent farming activity")

score = max(0, 100 - (25 if not farmer_online else 0) - (25 if not synced else 0) - (10 if activity_seconds and activity_seconds > 300 else 0))
status = "critical" if not farmer_online else "warning" if alerts else "healthy"

def age(seconds):
    if seconds is None:
        return "—"
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    return f"{seconds // 3600}h"


print(json.dumps({
    "status": status,
    "status_title": {"healthy": "Healthy", "warning": "Check farm", "critical": "Critical"}[status],
    "score": str(score),
    "farmer": "Online" if farmer_online else "Offline",
    "synced": "Synced" if synced else "Not synced",
    "plots": str(plots_number),
    "size": size,
    "activity": age(activity_seconds),
    "etw": etw,
    "alert": alerts[0] if alerts else "Everything is farming normally",
    "updated": datetime.datetime.now().strftime("%H:%M"),
}, separators=(",", ":")))
PY
