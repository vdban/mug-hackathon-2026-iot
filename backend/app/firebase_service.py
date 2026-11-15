"""
Firebase Realtime Database Optional Sync Service for Smart Aquarium Operations.
Đồng bộ trạng thái điều khiển và chỉ số mới nhất sang Firebase Realtime Database
theo cơ chế non-blocking (REST API), vẫn giữ MongoDB Time Series làm kho dữ liệu chính.
"""

import os
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict

import requests
from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_PATH, override=True)

logger = logging.getLogger("firebase_service")
_FB_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="fb-sync")


def _get_firebase_url() -> str:
    return os.getenv("FIREBASE_DATABASE_URL", "").strip().rstrip("/")


def is_firebase_configured() -> bool:
    url = _get_firebase_url()
    return bool(url and "your-project-id" not in url and url.startswith("https://"))


def _put_json(url: str, data: Dict[str, Any], path: str) -> None:
    try:
        res = requests.put(url, json=data, timeout=3)
        if res.status_code not in (200, 201, 204):
            logger.debug("Firebase sync (%s) status %s: %s", path, res.status_code, res.text[:200])
    except Exception as exc:
        logger.debug("Không thể đồng bộ Firebase (%s): %s", path, exc)


def sync_state_to_firebase(path: str, data: Dict[str, Any], async_send: bool = True) -> None:
    """Đẩy snapshot trạng thái lên Firebase Realtime Database (<url>/<path>.json)."""
    if not is_firebase_configured():
        return

    base_url = _get_firebase_url()
    clean_path = path.strip("/")
    url = f"{base_url}/{clean_path}.json"

    if async_send:
        _FB_EXECUTOR.submit(_put_json, url, data, clean_path)
    else:
        _put_json(url, data, clean_path)
