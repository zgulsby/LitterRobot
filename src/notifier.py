import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .skylight_client import create_chore
from .config import Config
from .whisker_client import RobotStatus, get_robot_statuses

logger = logging.getLogger(__name__)

STATE_FILE = Path("state.json")
_GCS_BUCKET = os.getenv("GCS_BUCKET")
_GCS_STATE_OBJECT = "state.json"


def _load_state() -> dict[str, Any]:
    if _GCS_BUCKET:
        from google.cloud import storage
        blob = storage.Client().bucket(_GCS_BUCKET).blob(_GCS_STATE_OBJECT)
        return json.loads(blob.download_as_text()) if blob.exists() else {}
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def _save_state(state: dict[str, Any]) -> None:
    if _GCS_BUCKET:
        from google.cloud import storage
        storage.Client().bucket(_GCS_BUCKET).blob(_GCS_STATE_OBJECT).upload_from_string(
            json.dumps(state, indent=2), content_type="application/json"
        )
        return
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _should_notify(serial: str, state: dict[str, Any], dedup_hours: int) -> bool:
    last_notified = state.get(serial, {}).get("last_notified")
    if not last_notified:
        return True
    last_dt = datetime.fromisoformat(last_notified)
    elapsed_hours = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
    return elapsed_hours >= dedup_hours


def _is_above_threshold(robot: RobotStatus, threshold: int) -> bool:
    if robot.drawer_level is not None:
        return robot.drawer_level >= threshold
    return robot.is_drawer_full


async def run(config: Config) -> None:
    """Main orchestration: check robots, notify if needed."""
    statuses = await get_robot_statuses(config.whisker_email, config.whisker_password)
    state = _load_state()

    for robot in statuses:
        if _is_above_threshold(robot, config.drawer_threshold):
            if _should_notify(robot.serial, state, config.dedup_hours):
                logger.info(
                    "Drawer needs attention on %s (level=%s). Creating Skylight chore.",
                    robot.name,
                    robot.drawer_level,
                )
                create_chore(
                    email=config.skylight_email,
                    password=config.skylight_password,
                    summary=config.chore_summary,
                    chore_date=datetime.now(timezone.utc).date(),
                )
                state.setdefault(robot.serial, {})["last_notified"] = datetime.now(
                    timezone.utc
                ).isoformat()
            else:
                logger.info(
                    "Drawer full on %s but already notified recently, skipping.",
                    robot.name,
                )
        else:
            # Drawer is clear — reset dedup state so we notify next time it fills
            if robot.serial in state:
                logger.info(
                    "Drawer clear on %s, resetting dedup state.", robot.name
                )
                state.pop(robot.serial)
            else:
                logger.info(
                    "Robot %s: drawer at %s%% (threshold: %s%%) — OK.",
                    robot.name,
                    robot.drawer_level if robot.drawer_level is not None else "N/A",
                    config.drawer_threshold,
                )

    _save_state(state)
