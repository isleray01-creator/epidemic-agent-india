from __future__ import annotations

import hashlib
import hmac
import logging
import pickle
from pathlib import Path
from typing import Any

from ..config import settings

logger = logging.getLogger(__name__)


class TrustedStateStore:
    def __init__(self, hmac_key: str = None, storage_dir: Path = None):
        key = hmac_key or settings.pickle_hmac_key or "default-dev-key-do-not-use-in-production"
        self.hmac_key = key.encode()
        if not self.hmac_key:
            raise ValueError("PICKLE_HMAC_KEY must be set in environment")

        self.storage_dir = storage_dir or Path("saved_states")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _sign(self, data: bytes) -> str:
        return hmac.new(self.hmac_key, data, hashlib.sha256).hexdigest()

    def _verify(self, data: bytes, signature: str) -> bool:
        expected = self._sign(data)
        return hmac.compare_digest(expected, signature)

    def save(self, state: Any, filename: str = None) -> Path:
        if filename is None:
            from datetime import datetime
            filename = f"state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"

        filepath = self.storage_dir / filename
        data = pickle.dumps(state)
        signature = self._sign(data)

        combined = signature.encode() + b"||" + data
        filepath.write_bytes(combined)

        logger.info(f"Saved state to {filepath} (size: {len(data)} bytes)")
        return filepath

    def load(self, filename: str) -> Any:
        filepath = self.storage_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"State file not found: {filepath}")

        raw = filepath.read_bytes()
        try:
            signature, data = raw.split(b"||", 1)
        except ValueError:
            raise ValueError("Invalid state file format (missing signature delimiter)")

        if not self._verify(data, signature.decode()):
            raise SecurityError("Untrusted state file: HMAC verification failed")

        state = pickle.loads(data)
        logger.info(f"Loaded state from {filepath}")
        return state

    def list_states(self) -> list:
        files = list(self.storage_dir.glob("*.pkl"))
        return sorted([f.name for f in files], reverse=True)


class SecurityError(Exception):
    pass


_state_store: TrustedStateStore | None = None


def get_state_store() -> TrustedStateStore:
    global _state_store
    if _state_store is None:
        _state_store = TrustedStateStore()
    return _state_store


def save_state(state: Any, filename: str = None) -> Path:
    return get_state_store().save(state, filename)


def load_state(filename: str) -> Any:
    return get_state_store().load(filename)
