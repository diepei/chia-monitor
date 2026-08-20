from __future__ import annotations

import json
import logging
import ssl
from pathlib import Path
from typing import Any

import httpx
import yaml


PORTS = {"farmer": 8559, "full_node": 8555, "harvester": 8560, "wallet": 9256}
logger = logging.getLogger(__name__)


class ChiaRPC:
    """Minimal client for local Chia RPC using Chia's own private CA certificate."""

    def __init__(self, chia_root: Path, timeout: float = 6):
        self.root = chia_root
        self.timeout = timeout
        self.ports = self._ports()

    def _ports(self) -> dict[str, int]:
        config_path = self.root / "config" / "config.yaml"
        try:
            config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            logger.warning("Could not read Chia config %s; using default RPC ports: %s", config_path, exc)
            return PORTS.copy()
        return {
            service: int(config.get(service, {}).get("rpc_port", default))
            for service, default in PORTS.items()
        }

    def _certs(self, service: str) -> tuple[str, str, str]:
        ssl = self.root / "config" / "ssl"
        cert = ssl / service / f"private_{service}.crt"
        key = ssl / service / f"private_{service}.key"
        ca = ssl / "ca" / "private_ca.crt"
        return str(cert), str(key), str(ca)

    def _ssl_context(self, service: str) -> tuple[ssl.SSLContext, str, str, str]:
        cert, key, ca = self._certs(service)
        for label, path in (("certificate", cert), ("private key", key), ("private CA", ca)):
            if not Path(path).is_file():
                raise FileNotFoundError(f"Chia RPC {label} not found: {path}")
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca)
        # Chia's local RPC certificates authenticate through its private CA but
        # are not issued for the loopback IP. The official clients likewise do
        # not validate the hostname for local RPC connections.
        context.check_hostname = False
        context.load_cert_chain(certfile=cert, keyfile=key)
        return context, cert, key, ca

    async def call(self, service: str, method: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        port = self.ports[service]
        endpoint = f"https://127.0.0.1:{port}/{method}"
        try:
            context, cert, _key, ca = self._ssl_context(service)
            logger.debug("RPC request service=%s endpoint=%s cert=%s ca=%s", service, endpoint, cert, ca)
            async with httpx.AsyncClient(verify=context, timeout=self.timeout) as client:
                response = await client.post(endpoint, json=body or {})
                logger.debug("RPC response service=%s method=%s status=%s", service, method, response.status_code)
                response.raise_for_status()
                data = response.json()
                preview = json.dumps(data, default=str)
                logger.debug("RPC JSON service=%s method=%s response=%s", service, method, preview[:4096])
                if data.get("success") is False:
                    raise RuntimeError(data.get("error", f"{service}/{method} failed"))
                return data
        except Exception:
            logger.exception("RPC failed service=%s endpoint=%s", service, endpoint)
            raise
