import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    whisker_email: str = os.environ["WHISKER_EMAIL"]
    whisker_password: str = os.environ["WHISKER_PASSWORD"]
    drawer_threshold: int = int(os.getenv("DRAWER_THRESHOLD", "80"))
    skylight_email: str = os.environ["SKYLIGHT_EMAIL"]
    skylight_password: str = os.environ["SKYLIGHT_PASSWORD"]
    dedup_hours: int = int(os.getenv("DEDUP_HOURS", "12"))
