import json

from chia_monitor.baseline import FarmBaseline, LEARNING_SAMPLES


def test_baseline_learns_only_after_stable_healthy_samples(tmp_path):
    path = tmp_path / "state.json"
    baseline = FarmBaseline(path)

    for _ in range(LEARNING_SAMPLES - 1):
        alerts, info = baseline.evaluate(plots=325, farm_size_tib=32.17, harvesters=1, eligible=True)
        assert alerts == []
        assert info["learning"] is True
        assert not path.exists()

    alerts, info = baseline.evaluate(plots=325, farm_size_tib=32.17, harvesters=1, eligible=True)

    assert alerts == []
    assert info["learning"] is False
    assert json.loads(path.read_text())["plots"] == 325


def test_baseline_warns_when_capacity_drops(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"plots": 325, "farm_size_tib": 32.17, "harvesters": 1, "learned_at": "now"}))
    baseline = FarmBaseline(path)

    alerts, info = baseline.evaluate(plots=320, farm_size_tib=31.60, harvesters=1, eligible=True)

    assert info["learning"] is False
    assert alerts == [{"severity": "warning", "code": "farm_capacity_drop", "message": "5 plots missing, farm size down 0.57 TiB"}]
    assert json.loads(path.read_text())["plots"] == 325


def test_baseline_automatically_grows_after_stable_samples(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"plots": 325, "farm_size_tib": 32.17, "harvesters": 1, "learned_at": "now"}))
    baseline = FarmBaseline(path)

    for _ in range(LEARNING_SAMPLES):
        alerts, _ = baseline.evaluate(plots=330, farm_size_tib=32.70, harvesters=1, eligible=True)

    assert alerts == []
    assert json.loads(path.read_text())["plots"] == 330


def test_unhealthy_readings_do_not_create_a_baseline(tmp_path):
    path = tmp_path / "state.json"
    baseline = FarmBaseline(path)

    for _ in range(LEARNING_SAMPLES + 2):
        baseline.evaluate(plots=200, farm_size_tib=20.0, harvesters=1, eligible=False)

    assert not path.exists()
