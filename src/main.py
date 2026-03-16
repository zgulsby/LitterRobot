import asyncio
import logging
import sys

from .config import Config
from .notifier import run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    try:
        config = Config()
    except KeyError as e:
        logger.error("Missing required environment variable: %s", e)
        sys.exit(1)

    try:
        asyncio.run(run(config))
    except Exception as e:
        logger.error("Unhandled error: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
