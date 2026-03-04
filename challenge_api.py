# challenge_api.py

import base64
import logging
import requests

from config import API_TIMEOUT_CHALLENGE

logger = logging.getLogger(__name__)


def fetch_challenge_image(api_url: str, timeout: int = API_TIMEOUT_CHALLENGE):
    """
    Calls /get_image and returns (image_bytes, image_id).
    Raises Exception if /get_image fails.
    """

    logger.info(f"Fetching challenge image from {api_url} (timeout={timeout}s)")
    response = requests.get(api_url, timeout=timeout)
    response.raise_for_status()
    logger.info(f"Challenge API responded with status {response.status_code}")

    data = response.json()

    if not data.get("success"):
        raise Exception("/get_image returned success=False")

    image_b64 = data.get("image_b64")
    image_id = data.get("image_id")

    if not image_b64:
        raise Exception("No image_b64 in response")

    # Decode base64 → bytes
    image_bytes = base64.b64decode(image_b64)
    logger.info(f"Challenge image fetched successfully (image_id={image_id}, size={len(image_bytes)} bytes)")

    return image_bytes, image_id
