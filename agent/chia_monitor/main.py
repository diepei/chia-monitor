from __future__ import annotations

import argparse
import asyncio
import secrets
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .collector import collect
from .config import Settings


class State:
    data: dict = {"status": "critical", "health_score": 0, "alerts": [{"severity": "critical", "message": "Agent is starting"}]}


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
    return app


def run() -> None:
    parser = argparse.ArgumentParser(description="Chia Monitor agent")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()
    settings = Settings.load(args.config)
    import uvicorn
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port, access_log=False)


if __name__ == "__main__": run()
