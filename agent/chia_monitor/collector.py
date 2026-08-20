from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil

from .config import DiskConfig, Settings
from .baseline import FarmBaseline
from .rpc import ChiaRPC


logger = logging.getLogger(__name__)
BLOCKS_PER_YEAR = 1_681_920


def _block_reward_xch(height: int) -> float:
    if height < 3 * BLOCKS_PER_YEAR:
        return 2.0
    if height < 6 * BLOCKS_PER_YEAR:
        return 1.0
    if height < 9 * BLOCKS_PER_YEAR:
        return 0.5
    if height < 12 * BLOCKS_PER_YEAR:
        return 0.25
    return 0.125


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart(disk: DiskConfig) -> tuple[int | None, bool | None]:
    if not disk.device:
        return None, None
    smartctl = shutil.which("smartctl")
    if not smartctl and os.name == "nt":
        candidate = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "smartmontools" / "bin" / "smartctl.exe"
        smartctl = str(candidate) if candidate.exists() else None
    if not smartctl:
        return None, None
    try:
        result = subprocess.run([smartctl, "-a", "-j", disk.device], capture_output=True, text=True, timeout=8, check=False)
        payload = json.loads(result.stdout)
        temp = payload.get("temperature", {}).get("current")
        healthy = payload.get("smart_status", {}).get("passed")
        return temp, healthy
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
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


async def collect(settings: Settings, baseline: FarmBaseline | None = None) -> dict[str, Any]:
    rpc = ChiaRPC(settings.root)
    tasks = {
        "chain": asyncio.create_task(rpc.call("full_node", "get_blockchain_state")),
        "connections": asyncio.create_task(rpc.call("farmer", "get_connections")),
        "harvesters": asyncio.create_task(rpc.call("farmer", "get_harvesters")),
        "plots": asyncio.create_task(rpc.call("harvester", "get_plots")),
        "farmed": asyncio.create_task(rpc.call("wallet", "get_farmed_amount")),
    }
    results: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    for key, task in tasks.items():
        try:
            results[key] = await task
        except Exception as exc:
            errors[key] = f"{type(exc).__name__}: {exc}"
            logger.error("RPC collection failed key=%s error=%s", key, errors[key])

    chain = results.get("chain", {}).get("blockchain_state", {})
    sync = chain.get("sync", {})
    plots = results.get("plots", {}).get("plots", [])
    failed = results.get("plots", {}).get("failed_to_open_filenames", [])
    no_key = results.get("plots", {}).get("not_found_filenames", [])
    farm_bytes = sum(int(plot.get("file_size", 0)) for plot in plots)
    netspace = int(chain.get("space", 0) or 0)
    etw = round((netspace / farm_bytes) * 18.75) if farm_bytes and netspace else 0
    peak_height = int(chain.get("peak", {}).get("height", 0) if chain.get("peak") else 0)
    harvester_items = results.get("harvesters", {}).get("harvesters", [])
    if not plots and harvester_items:
        plots = [plot for harvester in harvester_items for plot in harvester.get("plots", [])]
        failed = [name for harvester in harvester_items for name in harvester.get("failed_to_open_filenames", [])]
        no_key = [name for harvester in harvester_items for name in harvester.get("no_key_filenames", harvester.get("not_found_filenames", []))]
        farm_bytes = sum(int(plot.get("file_size", 0)) for plot in plots)
        etw = round((netspace / farm_bytes) * 18.75) if farm_bytes and netspace else 0
    daily_xch = round((86400 / etw) * _block_reward_xch(peak_height), 6) if etw else 0.0
    harvester_connections = [c for c in results.get("connections", {}).get("connections", []) if c.get("type") == 2]
    total_harvesters = max(len(harvester_items), len(harvester_connections), 1 if plots else 0)
    online_harvesters = len(harvester_items) or len(harvester_connections)
    farmed = results.get("farmed", {})
    last_time_farmed = int(farmed.get("last_time_farmed", 0) or 0)
    last_block_at = datetime.fromtimestamp(last_time_farmed, timezone.utc).isoformat() if last_time_farmed else None
    disks = await asyncio.to_thread(_disk_status, settings.disks)

    farmer_online = "connections" in results or "harvesters" in results
    alerts: list[dict[str, str]] = []
    if not farmer_online: alerts.append({"severity": "critical", "code": "farmer_offline", "message": "Farmer RPC is offline"})
    if not sync.get("synced", False): alerts.append({"severity": "critical", "code": "node_sync", "message": "Full node is not synced"})
    if online_harvesters == 0: alerts.append({"severity": "critical", "code": "harvester_offline", "message": "No harvesters are online"})
    if not plots: alerts.append({"severity": "critical", "code": "no_plots", "message": "No farming plots are available"})

    offline_disks = [disk for disk in disks if not disk["online"]]
    all_disks_offline = bool(disks) and len(offline_disks) == len(disks)
    eligible_for_baseline = farmer_online and bool(sync.get("synced")) and online_harvesters > 0 and bool(plots) and not offline_disks and not failed and not no_key
    baseline_info: dict[str, Any] = {"learning": False}
    if baseline is not None:
        baseline_alerts, baseline_info = baseline.evaluate(
            plots=len(plots), farm_size_tib=round(farm_bytes / 2**40, 2), harvesters=online_harvesters, eligible=eligible_for_baseline
        )
        alerts.extend(baseline_alerts)

    if failed or no_key: alerts.append({"severity": "warning", "code": "plot_errors", "message": f"{len(failed) + len(no_key)} plots failed or are missing"})
    if all_disks_offline:
        alerts.append({"severity": "critical", "code": "all_disks_offline", "message": "All configured farm disks are offline"})
    else:
        for disk in offline_disks:
            alerts.append({"severity": "warning", "code": "disk_offline", "message": f'{disk["name"]} is offline; farming continues'})
    for disk in disks:
        if disk["online"] and disk["smart_healthy"] is False: alerts.append({"severity": "warning", "code": "smart_failed", "message": f'{disk["name"]} failed SMART health'})
        elif disk["temperature_c"] and disk["temperature_c"] >= 50: alerts.append({"severity": "warning", "code": "disk_hot", "message": f'{disk["name"]} is hot ({disk["temperature_c"]}°C)'})

    if "farmed" in errors:
        alerts.append({"severity": "warning", "code": "farming_rewards_unavailable", "message": "Block reward history is unavailable"})

    status = "critical" if any(a["severity"] == "critical" for a in alerts) else "warning" if alerts else "healthy"
    return {
        "status": status,
        "farmer": {"online": farmer_online},
        "node": {"synced": bool(sync.get("synced")), "syncing": bool(sync.get("sync_mode")), "height": peak_height},
        "farm": {"plots": len(plots), "size_tib": round(farm_bytes / 2**40, 2), "estimated_time_to_win_seconds": etw, "failed_plots": len(failed) + len(no_key)},
        "harvesters": {"online": online_harvesters, "total": total_harvesters},
        "farming": {"estimated_daily_xch": daily_xch, "blocks_won": int(farmed.get("blocks_won", 0) or 0), "last_block_height": int(farmed.get("last_height_farmed", 0) or 0), "last_block_at": last_block_at},
        "disks": disks, "alerts": alerts, "baseline": baseline_info, "rpc_errors": errors, "updated_at": _iso_now(),
    }
