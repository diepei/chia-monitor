from __future__ import annotations

import argparse
import asyncio
import secrets
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .collector import collect
from .config import Settings


class State:
    data: dict = {"status": "critical", "health_score": 0, "alerts": [{"severity": "critical", "message": "Agent is starting"}]}


def _duration(seconds: int | None) -> str:
    if not seconds:
        return "—"
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"


def widgy_payload(data: dict) -> dict:
    status = data.get("status", "critical")
    farm = data.get("farm", {})
    farmer = data.get("farmer", {})
    node = data.get("node", {})
    harvesters = data.get("harvesters", {})
    wallet = data.get("wallet", {})
    alerts = data.get("alerts", [])
    labels = {"healthy": "Healthy", "warning": "Check farm", "critical": "Critical"}
    colors = {"healthy": "#59DB87", "warning": "#F2BD5E", "critical": "#F06D66"}
    updated = data.get("updated_at")
    try:
        updated_text = datetime.fromisoformat(updated).astimezone().strftime("%H:%M") if updated else "—"
    except (TypeError, ValueError):
        updated_text = "—"
    return {
        "health_score": str(data.get("health_score", 0)),
        "health_label": labels.get(status, "Critical"),
        "health_color": colors.get(status, "#F06D66"),
        "farmer_status": "Online" if farmer.get("online") else "Offline",
        "node_status": "Synced" if node.get("synced") else "Syncing" if node.get("syncing") else "Offline",
        "plots": str(farm.get("plots", 0)),
        "farm_size": f'{farm.get("size_tib", 0):.1f} TiB',
        "harvesters": f'{harvesters.get("online", 0)} / {harvesters.get("total", 0)}',
        "activity": _duration(farmer.get("last_activity_seconds")),
        "etw": _duration(farm.get("estimated_time_to_win_seconds")),
        "balance": f'{wallet.get("balance_xch", 0):.3f} XCH',
        "failed_plots": str(farm.get("failed_plots", 0)),
        "alert": alerts[0].get("message", "Everything is farming normally") if alerts else "Everything is farming normally",
        "updated": updated_text,
    }


def create_config(path: str, chia_root: str) -> str:
    destination = Path(path).expanduser()
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite {destination}")
    token = secrets.token_urlsafe(32)
    payload = {
        "host": "127.0.0.1",
        "port": 8926,
        "api_token": token,
        "chia_root": str(Path(chia_root).expanduser()),
        "refresh_seconds": 30,
        "activity_stale_seconds": 300,
        "allowed_origins": [],
        "disks": [],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(yaml.safe_dump(payload, sort_keys=False))
    return token


def create_app(settings: Settings) -> FastAPI:
    state = State()

    async def refresh() -> None:
        while True:
            try:
                state.data = await collect(settings)
            except Exception as exc:
                state.data = {"status": "critical", "health_score": 0, "alerts": [{"severity": "critical", "message": "Collection failed"}], "error": str(exc)}
            await asyncio.sleep(settings.refresh_seconds)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        task = asyncio.create_task(refresh())
        await asyncio.sleep(0)
        yield
        task.cancel()

    app = FastAPI(title="Chia Monitor Agent", docs_url=None, redoc_url=None, lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=False, allow_methods=["GET"], allow_headers=["Authorization"])

    def authorize(authorization: Optional[str] = Header(default=None)) -> None:
        supplied = authorization.removeprefix("Bearer ") if authorization else ""
        if not secrets.compare_digest(supplied, settings.api_token):
            raise HTTPException(status_code=401, detail="Invalid API token")

    @app.get("/healthz")
    async def healthz(): return {"ok": True}

    @app.get("/api/status", dependencies=[Depends(authorize)])
    async def status(): return state.data

    @app.get("/api/widget", dependencies=[Depends(authorize)])
    async def widget():
        d = state.data
        return {"score": d.get("health_score", 0), "status": d.get("status", "critical"), "farmer": d.get("farmer", {}).get("online", False), "synced": d.get("node", {}).get("synced", False), "plots": d.get("farm", {}).get("plots", 0), "tib": d.get("farm", {}).get("size_tib", 0), "harvesters": d.get("harvesters", {}), "etw_seconds": d.get("farm", {}).get("estimated_time_to_win_seconds", 0), "balance_xch": d.get("wallet", {}).get("balance_xch", 0), "alerts": d.get("alerts", [])[:3], "updated_at": d.get("updated_at")}

    @app.get("/api/widgy", dependencies=[Depends(authorize)])
    async def widgy(): return widgy_payload(state.data)
    return app


def run() -> None:
    parser = argparse.ArgumentParser(description="Chia Monitor agent")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--init-config", action="store_true", help="create a secure starter configuration and exit")
    parser.add_argument("--chia-root", default="~/.chia/mainnet", help="Chia root used with --init-config")
    args = parser.parse_args()
    if args.init_config:
        try:
            token = create_config(args.config, args.chia_root)
        except FileExistsError as exc:
            parser.error(str(exc))
        print(f"Configuration created: {Path(args.config).expanduser()}")
        print(f"Widgy API token: {token}")
        print("Save this token now; it is required by Widgy.")
        return
    settings = Settings.load(args.config)
    import uvicorn
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port, access_log=False)


if __name__ == "__main__": run()
