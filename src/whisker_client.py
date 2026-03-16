import logging
from dataclasses import dataclass
from typing import Optional

from pylitterbot import Account

logger = logging.getLogger(__name__)


@dataclass
class RobotStatus:
    serial: str
    name: str
    is_drawer_full: bool
    drawer_level: Optional[int]  # percentage, None for LR3


async def get_robot_statuses(email: str, password: str) -> list[RobotStatus]:
    """Authenticate to Whisker and return status for all robots."""
    account = Account()
    try:
        await account.connect(username=email, password=password, load_robots=True)
        statuses: list[RobotStatus] = []
        for robot in account.robots:
            serial = robot.serial
            name = robot.name or serial

            # LR4 exposes waste_drawer_level as a percentage
            drawer_level: Optional[int] = getattr(robot, "waste_drawer_level", None)

            # LR3 uses isDFITriggered flag
            dfi_triggered: bool = getattr(robot, "is_drawer_full_indicator_triggered", False)

            if drawer_level is not None:
                is_full = drawer_level >= 100
            else:
                is_full = dfi_triggered

            statuses.append(
                RobotStatus(
                    serial=serial,
                    name=name,
                    is_drawer_full=is_full,
                    drawer_level=drawer_level,
                )
            )
            logger.debug(
                "Robot %s (%s): drawer_level=%s, dfi=%s, is_full=%s",
                name,
                serial,
                drawer_level,
                dfi_triggered,
                is_full,
            )
        return statuses
    finally:
        await account.disconnect()
