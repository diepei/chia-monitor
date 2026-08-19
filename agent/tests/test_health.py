from chia_monitor.collector import _disk_status
from chia_monitor.config import DiskConfig, Settings
from chia_monitor.main import create_app
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
