from __future__ import annotations

import asyncio
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil

from .config import DiskConfig, Settings
from .rpc import ChiaRPC


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart(disk: DiskConfig) -> tuple[int | None, bool | None]:
    if not disk.device:
        return None, None
    try:
        result = subprocess.run(["smartctl", "-a", "-j", disk.device], capture_output=True, text=True, timeout=8, check=False)
        payload = json.loads(result.stdout)
        temp = payload.get("temperature", {}).get("current")
        healthy = payload.get("smart_status", {}).get("passed")
        return temp, healthy
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None, None


def _disk_status(disks: list[DiskConfig]) -> list[dict[str, Any]]:
    output = []
    for disk in disks:
        exists = Path(disk.mountpoint).is_mount() or Path(disk.mountpoint).exists()
        try:
            usage = psutil.disk_usage(disk.mountpoint)
            used = round(usage.percent, 1)
            free_tib = round(usage.free / 2**40, 2)
        except (FileNotFoundError, PermissionError):
            exists, used, free_tib = False, 0.0, 0.0
        temperature, smart = _smart(disk) if exists else (None, False)
        output.append({"name": disk.name, "mountpoint": disk.mountpoint, "online": exists, "used_percent": used, "free_tib": free_tib, "temperature_c": temperature, "smart_healthy": smart})
    return output


async def collect(settings: Settings) -> dict[str, Any]:
    rpc = ChiaRPC(settings.root)
    tasks = {
        "chain": asyncio.create_task(rpc.call("full_node", "get_blockchain_state")),
        "connections": asyncio.create_task(rpc.call("farmer", "get_connections")),
        "harvesters": asyncio.create_task(rpc.call("farmer", "get_harvesters")),
        "plots": asyncio.create_task(rpc.call("harvester", "get_plots")),
        "farmed": asyncio.create_task(rpc.call("wallet", "get_farmed_amount")),
        "balance": asyncio.create_task(rpc.call("wallet", "get_wallet_balance", {"wallet_id": 1})),
        "transactions": asyncio.create_task(rpc.call("wallet", "get_transactions", {"wallet_id": 1, "start": 0, "end": 1000, "sort_key": "RELEVANCE"})),
        "signage": asyncio.create_task(rpc.call("farmer", "get_signage_points")),
    }
    results: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    for key, task in tasks.items():
        try:
            results[key] = await task
        except Exception as exc:
            errors[key] = str(exc)

    chain = results.get("chain", {}).get("blockchain_state", {})
    sync = chain.get("sync", {})
    plots = results.get("plots", {}).get("plots", [])
    failed = results.get("plots", {}).get("failed_to_open_filenames", [])
    no_key = results.get("plots", {}).get("not_found_filenames", [])
    farm_bytes = sum(int(plot.get("file_size", 0)) for plot in plots)
    netspace = int(chain.get("space", 0) or 0)
    etw = round((netspace / farm_bytes) * 18.75) if farm_bytes and netspace else 0
    harvester_items = results.get("harvesters", {}).get("harvesters", [])
    harvester_connections = [c for c in results.get("connections", {}).get("connections", []) if c.get("type") == 2]
    total_harvesters = max(len(harvester_items), len(harvester_connections), 1 if plots else 0)
    online_harvesters = len(harvester_items) or len(harvester_connections)
    signage = results.get("signage", {}).get("signage_points", [])
    last_signage = max((float(x.get("time_received", 0)) for x in signage), default=0)
    last_activity = max(0, round(time.time() - last_signage)) if last_signage else 999999
    mojo = 10**12
    farmed = results.get("farmed", {})
    wallet = results.get("balance", {}).get("wallet_balance", {})
    blocks_won = sum(1 for tx in results.get("transactions", {}).get("transactions", []) if tx.get("type") == 2)
    disks = await asyncio.to_thread(_disk_status, settings.disks)

    farmer_online = "connections" in results
    alerts: list[dict[str, str]] = []
    if not farmer_online: alerts.append({"severity": "critical", "code": "farmer_offline", "message": "Farmer RPC is offline"})
    if not sync.get("synced", False): alerts.append({"severity": "critical" if not sync else "warning", "code": "node_sync", "message": "Full node is not synced"})
    if online_harvesters < total_harvesters: alerts.append({"severity": "critical", "code": "harvester_missing", "message": f"Only {online_harvesters} of {total_harvesters} harvesters are online"})
    if last_activity > settings.activity_stale_seconds: alerts.append({"severity": "warning", "code": "activity_stale", "message": "No recent signage point activity"})
    if failed or no_key: alerts.append({"severity": "warning", "code": "plot_errors", "message": f"{len(failed) + len(no_key)} plots failed or are missing"})
    for disk in disks:
        if not disk["online"]: alerts.append({"severity": "critical", "code": "disk_offline", "message": f'{disk["name"]} is offline'})
        elif disk["smart_healthy"] is False: alerts.append({"severity": "critical", "code": "smart_failed", "message": f'{disk["name"]} failed SMART health'})
        elif disk["temperature_c"] and disk["temperature_c"] >= 50: alerts.append({"severity": "warning", "code": "disk_hot", "message": f'{disk["name"]} is hot ({disk["temperature_c"]}°C)'})

    score = max(0, 100 - sum(25 if a["severity"] == "critical" else 10 for a in alerts))
    status = "critical" if any(a["severity"] == "critical" for a in alerts) else "warning" if alerts else "healthy"
    return {
        "health_score": score, "status": status,
        "farmer": {"online": farmer_online, "last_activity_seconds": last_activity},
        "node": {"synced": bool(sync.get("synced")), "syncing": bool(sync.get("sync_mode")), "height": int(chain.get("peak", {}).get("height", 0) if chain.get("peak") else 0)},
        "farm": {"plots": len(plots), "size_tib": round(farm_bytes / 2**40, 2), "estimated_time_to_win_seconds": etw, "failed_plots": len(failed) + len(no_key)},
        "harvesters": {"online": online_harvesters, "total": total_harvesters},
        "wallet": {"balance_xch": round(int(wallet.get("confirmed_wallet_balance", 0)) / mojo, 6), "blocks_won": blocks_won, "rewards_xch": round(int(farmed.get("farmed_amount", 0)) / mojo, 6)},
        "disks": disks, "alerts": alerts, "rpc_errors": list(errors), "updated_at": _iso_now(),
    }
