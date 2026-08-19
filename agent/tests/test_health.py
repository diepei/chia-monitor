from chia_monitor.collector import _disk_status
from chia_monitor.config import DiskConfig, Settings
from chia_monitor.main import create_app, create_config, widgy_payload
from fastapi.testclient import TestClient


def test_settings_expand_home():
    settings = Settings(api_token="a" * 32)
    assert settings.root.is_absolute()


def test_missing_disk_is_offline():
    result = _disk_status([DiskConfig(name="missing", mountpoint="/path/that/cannot/exist")])
    assert result[0]["online"] is False


def test_farm_data_requires_token():
    client = TestClient(create_app(Settings(api_token="a" * 32)))
    assert client.get("/api/status").status_code == 401
    response = client.get("/api/widget", headers={"Authorization": f"Bearer {'a' * 32}"})
    assert response.status_code == 200
    assert set(("score", "status", "plots", "alerts")) <= response.json().keys()


def test_widgy_payload_is_flat_and_display_ready():
    payload = widgy_payload({
        "health_score": 96, "status": "healthy", "updated_at": "2026-08-20T10:15:00+00:00",
        "farmer": {"online": True, "last_activity_seconds": 18},
        "node": {"synced": True}, "farm": {"plots": 742, "size_tib": 73.4, "estimated_time_to_win_seconds": 864000, "failed_plots": 0},
        "harvesters": {"online": 2, "total": 2}, "wallet": {"balance_xch": 4.126}, "alerts": [],
    })
    assert payload["health_score"] == "96"
    assert payload["farmer_status"] == "Online"
    assert payload["farm_size"] == "73.4 TiB"
    assert payload["alert"] == "Everything is farming normally"


def test_create_config_generates_token(tmp_path):
    path = tmp_path / "config.yaml"
    token = create_config(str(path), "/home/chia/.chia/mainnet")
    assert len(token) >= 32
    assert token in path.read_text()
