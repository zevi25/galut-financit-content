"""
Wavespeed — Nano Banana 2 (google/nano-banana-2/text-to-image)
API: https://api.wavespeed.ai/api/v3
"""
import base64
import time
import requests
from backend.config import WAVESPEED_API_KEY

_BASE_URL = "https://api.wavespeed.ai/api/v3"
_MODEL    = "google/nano-banana-2/text-to-image"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {WAVESPEED_API_KEY}",
        "Content-Type": "application/json",
    }


def _submit(prompt: str) -> str:
    payload = {
        "prompt": prompt,
        "aspect_ratio": "9:16",
        "resolution": "2k",
        "output_format": "jpeg",
    }
    resp = requests.post(
        f"{_BASE_URL}/{_MODEL}",
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"]["id"]


def _poll(prediction_id: str, poll_interval: float = 3.0, timeout: float = 300.0) -> str:
    """Poll until completed; return image URL."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(
            f"{_BASE_URL}/predictions/{prediction_id}/result",
            headers=_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        status = data.get("status")
        if status == "completed":
            outputs = data["outputs"]
            return outputs[0] if isinstance(outputs, list) else outputs
        if status in ("failed", "canceled"):
            raise RuntimeError(f"Wavespeed {status}: {data.get('error')}")
        time.sleep(poll_interval)
    raise TimeoutError(f"Prediction {prediction_id} timed out")


class NanoBananaClient:

    def generate_image_bytes(self, prompt: str) -> bytes:
        if not WAVESPEED_API_KEY:
            raise RuntimeError("WAVESPEED_API_KEY is not set in .env")
        prediction_id = _submit(prompt)
        image_url = _poll(prediction_id)
        resp = requests.get(image_url, timeout=60)
        resp.raise_for_status()
        return resp.content

    def generate_image_b64(self, prompt: str) -> str:
        return base64.b64encode(self.generate_image_bytes(prompt)).decode("utf-8")
