from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)
LEARNING_SAMPLES = 5
SIZE_TOLERANCE_TIB = 0.05


class FarmBaseline:
    """Learn and persist the last confirmed healthy farm capacity."""

    def __init__(self, path: Path):
        self.path = path
        self.values = self._load()
        self._candidate: tuple[int, float, int] | None = None
        self._candidate_samples = 0

    def _load(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return {
                "plots": int(payload["plots"]),
                "farm_size_tib": float(payload["farm_size_tib"]),
                "harvesters": int(payload["harvesters"]),
                "learned_at": str(payload["learned_at"]),
            }
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            logger.warning("Ignoring invalid farm baseline %s: %s", self.path, exc)
            return None

    def _save(self, plots: int, farm_size_tib: float, harvesters: int) -> None:
        payload = {
            "version": 1,
            "plots": plots,
            "farm_size_tib": round(farm_size_tib, 2),
            "harvesters": harvesters,
            "learned_at": datetime.now(timezone.utc).isoformat(),
        }
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self.path)
        self.values = payload
        logger.info("Farm baseline updated plots=%s size_tib=%s harvesters=%s", plots, farm_size_tib, harvesters)

    def _observe_candidate(self, current: tuple[int, float, int]) -> bool:
        if current == self._candidate:
            self._candidate_samples += 1
        else:
            self._candidate = current
            self._candidate_samples = 1
        if self._candidate_samples < LEARNING_SAMPLES:
            return False
        self._save(*current)
        self._candidate = None
        self._candidate_samples = 0
        return True

    def evaluate(
        self,
        *,
        plots: int,
        farm_size_tib: float,
        harvesters: int,
        eligible: bool,
    ) -> tuple[list[dict[str, str]], dict[str, Any]]:
        current = (plots, round(farm_size_tib, 2), harvesters)
        if self.values is None:
            if eligible:
                self._observe_candidate(current)
            else:
                self._candidate = None
                self._candidate_samples = 0
            return [], {"learning": self.values is None, "samples": self._candidate_samples}

        expected_plots = int(self.values["plots"])
        expected_size = float(self.values["farm_size_tib"])
        expected_harvesters = int(self.values["harvesters"])
        alerts: list[dict[str, str]] = []

        missing_plots = max(0, expected_plots - plots)
        missing_size = max(0.0, expected_size - farm_size_tib)
        if missing_plots or missing_size > SIZE_TOLERANCE_TIB:
            details = []
            if missing_plots:
                details.append(f"{missing_plots} plots missing")
            if missing_size > SIZE_TOLERANCE_TIB:
                details.append(f"farm size down {missing_size:.2f} TiB")
            alerts.append({"severity": "warning", "code": "farm_capacity_drop", "message": ", ".join(details)})

        if 0 < harvesters < expected_harvesters:
            alerts.append({"severity": "warning", "code": "harvester_missing", "message": f"Only {harvesters} of {expected_harvesters} harvesters are online"})

        grows = plots > expected_plots or farm_size_tib > expected_size + SIZE_TOLERANCE_TIB or harvesters > expected_harvesters
        no_drop = plots >= expected_plots and farm_size_tib >= expected_size - SIZE_TOLERANCE_TIB and harvesters >= expected_harvesters
        if eligible and grows and no_drop:
            self._observe_candidate(current)
        else:
            self._candidate = None
            self._candidate_samples = 0

        return alerts, {
            "learning": False,
            "expected_plots": expected_plots,
            "expected_farm_size_tib": expected_size,
            "expected_harvesters": expected_harvesters,
        }
