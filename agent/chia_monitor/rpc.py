from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx


PORTS = {"farmer": 8559, "full_node": 8555, "harvester": 8560, "wallet": 9256}


class ChiaRPC:
    """Minimal client for local Chia RPC using Chia's own private CA certificate."""

    def __init__(self, chia_root: Path, timeout: float = 6):
        self.root = chia_root
        self.timeout = timeout

    def _certs(self, service: str) -> tuple[str, str, str]:
        ssl = self.root / "config" / "ssl"
        cert = ssl / service / f"private_{service}.crt"
        key = ssl / service / f"private_{service}.key"
        ca = ssl / "ca" / "private_ca.crt"
        return str(cert), str(key), str(ca)

    async def call(self, service: str, method: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        cert, key, ca = self._certs(service)
        async with httpx.AsyncClient(cert=(cert, key), verify=ca, timeout=self.timeout) as client:
            response = await client.post(f"https://127.0.0.1:{PORTS[service]}/{method}", json=body or {})
            response.raise_for_status()
            data = response.json()
            if data.get("success") is False:
                raise RuntimeError(data.get("error", f"{service}/{method} failed"))
            return data
