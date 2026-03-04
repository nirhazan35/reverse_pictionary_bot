# evaluation_api.py

import base64
import logging
import requests

from config import API_TIMEOUT_EVALUATE

logger = logging.getLogger(__name__)


def evaluate_prompt(api_url: str, image_id: str, prompt: str, timeout: int = API_TIMEOUT_EVALUATE):
    """
    Sends image_id + prompt to /play_round.
    Returns (score, image_bytes).
    Raises exception if failed.
    """

    logger.info(f"Evaluating prompt for image_id={image_id}: \"{prompt}\" (timeout={timeout}s)")
    payload = {
        "user_prompt": prompt,
        "target_image_id": image_id,
    }

    response = requests.post(api_url, payload, timeout=timeout)
    response.raise_for_status()
    logger.info(f"Evaluate API responded with status {response.status_code}")

    data = response.json()

    if not data.get("success"):
        raise Exception("/play_round returned success=False")

    score = data.get("score")
    image_b64 = data.get("image_b64")

    if score is None or image_b64 is None:
        raise Exception("Invalid /play_round response")

    image_bytes = base64.b64decode(image_b64)
    logger.info(f"Evaluation complete: score={score}, generated image size={len(image_bytes)} bytes")

    return score, image_bytes
