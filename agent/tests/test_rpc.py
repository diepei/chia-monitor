from pathlib import Path
from unittest.mock import Mock, patch

from chia_monitor.rpc import ChiaRPC


def _write_rpc_files(root: Path, service: str = "full_node") -> None:
    ssl_root = root / "config" / "ssl"
    service_root = ssl_root / service
    ca_root = ssl_root / "ca"
    service_root.mkdir(parents=True)
    ca_root.mkdir(parents=True)
    (service_root / f"private_{service}.crt").write_text("certificate")
    (service_root / f"private_{service}.key").write_text("key")
    (ca_root / "private_ca.crt").write_text("ca")


def test_rpc_uses_ports_from_chia_config(tmp_path):
    config = tmp_path / "config"
    config.mkdir()
    (config / "config.yaml").write_text(
        "full_node:\n  rpc_port: 18555\nfarmer:\n  rpc_port: 18559\n"
    )

    rpc = ChiaRPC(tmp_path)

    assert rpc.ports["full_node"] == 18555
    assert rpc.ports["farmer"] == 18559
    assert rpc.ports["harvester"] == 8560


def test_rpc_tls_validates_private_ca_without_loopback_hostname(tmp_path):
    _write_rpc_files(tmp_path)
    context = Mock()
    context.check_hostname = True

    with patch("chia_monitor.rpc.ssl.create_default_context", return_value=context) as create_context:
        rpc = ChiaRPC(tmp_path)
        result, cert, key, ca = rpc._ssl_context("full_node")

    assert result is context
    assert context.check_hostname is False
    context.load_cert_chain.assert_called_once_with(certfile=cert, keyfile=key)
    create_context.assert_called_once()
    assert ca.endswith("private_ca.crt")


def test_missing_rpc_certificate_reports_exact_path(tmp_path):
    rpc = ChiaRPC(tmp_path)

    try:
        rpc._ssl_context("farmer")
    except FileNotFoundError as exc:
        assert "private_farmer.crt" in str(exc)
    else:
        raise AssertionError("missing Chia certificate was not reported")
