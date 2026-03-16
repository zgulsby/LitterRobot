import base64
import logging
from datetime import date

import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://app.ourskylight.com/api"


def _authenticate(email: str, password: str) -> tuple[str, str]:
    """Authenticate with Skylight API. Returns (user_id, token)."""
    resp = requests.post(
        f"{_BASE_URL}/sessions",
        json={"email": email, "password": password},
    )
    resp.raise_for_status()
    user = resp.json()["data"]
    return user["id"], user["attributes"]["token"]


def _auth_header(user_id: str, token: str) -> dict[str, str]:
    encoded = base64.b64encode(f"{user_id}:{token}".encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


def _get_frame(headers: dict[str, str]) -> tuple[str, str]:
    """Get the first frame ID and its first category ID."""
    resp = requests.get(f"{_BASE_URL}/frames", headers=headers)
    resp.raise_for_status()
    frames = resp.json().get("data", [])
    if not frames:
        raise RuntimeError("No Skylight frames found on this account")
    frame_id: str = frames[0]["id"]
    logger.info("Using Skylight frame: %s", frame_id)

    # Find the "Family" category (not linked to a profile)
    resp = requests.get(f"{_BASE_URL}/frames/{frame_id}/categories", headers=headers)
    resp.raise_for_status()
    categories = resp.json().get("data", [])
    category_id: str | None = None
    for cat in categories:
        if cat["attributes"]["label"] == "Family" and cat["attributes"]["linked_to_profile"]:
            category_id = cat["id"]
            break
    if not category_id:
        if not categories:
            raise RuntimeError("No categories found on Skylight frame")
        category_id = categories[0]["id"]
    return frame_id, category_id


def create_chore(email: str, password: str, summary: str, chore_date: date) -> str:
    """Create a chore on the Skylight calendar. Returns the chore ID."""
    user_id, token = _authenticate(email, password)
    headers = _auth_header(user_id, token)
    frame_id, category_id = _get_frame(headers)

    resp = requests.post(
        f"{_BASE_URL}/frames/{frame_id}/chores",
        headers=headers,
        json={
            "summary": summary,
            "date": chore_date.isoformat(),
            "category_id": int(category_id),
        },
    )
    resp.raise_for_status()
    chore_id: str = resp.json()["data"]["id"]
    logger.info("Created Skylight chore '%s' (id=%s)", summary, chore_id)
    return chore_id
