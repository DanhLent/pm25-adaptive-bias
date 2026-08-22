from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATE_SCHEMA_VERSION = 1


class StateCompatibilityError(RuntimeError):
    pass


class PipelineLockedError(RuntimeError):
    pass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_json_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def processing_config_hash(config: dict[str, Any], active_config: dict[str, Any]) -> str:
    frozen_active = {
        key: active_config[key]
        for key in (
            "model_name",
            "selected_alpha_shift",
            "scale",
            "pm25_min",
            "pm25_max",
            "bias_min",
            "bias_max",
            "alert_on",
            "alert_off",
            "alert_thresholds",
        )
    }
    return canonical_json_hash(
        {
            "hardware_aligned": config["hardware_aligned"],
            "purpleair_qc_policy": config["purpleair_qc_policy"],
            "active_core": frozen_active,
        }
    )


def initial_pipeline_state(
    *,
    config_hash: str,
    model_version: str,
    active_alpha_shift: int,
) -> dict[str, Any]:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "model_version": model_version,
        "config_hash": config_hash,
        "last_successful_raw_timestamp": None,
        "last_processed_hour": None,
        "processed_input_hash": None,
        "bias_x16": 0,
        "hysteresis_state": 0,
        "sample_index": 0,
        "active_alpha_shift": int(active_alpha_shift),
        "last_reconciliation": None,
        "last_backup": None,
        "last_alpha_evaluation": None,
        "updated_at_utc": None,
    }


def validate_pipeline_state(
    state: dict[str, Any],
    *,
    config_hash: str,
    model_version: str,
    active_alpha_shift: int,
) -> None:
    if int(state.get("schema_version", -1)) != STATE_SCHEMA_VERSION:
        raise StateCompatibilityError(
            f"State schema mismatch: expected {STATE_SCHEMA_VERSION}, "
            f"got {state.get('schema_version')!r}."
        )
    if state.get("model_version") != model_version:
        raise StateCompatibilityError(
            f"State model mismatch: expected {model_version!r}, "
            f"got {state.get('model_version')!r}."
        )
    if state.get("config_hash") != config_hash:
        raise StateCompatibilityError("State config hash does not match active processing config.")
    if int(state.get("active_alpha_shift", -1)) != int(active_alpha_shift):
        raise StateCompatibilityError("State alpha shift does not match active alpha shift.")
    if int(state.get("hysteresis_state", -1)) not in {0, 1}:
        raise StateCompatibilityError("State hysteresis_state must be 0 or 1.")


def read_pipeline_state(path: str | Path) -> dict[str, Any] | None:
    path = Path(path)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise StateCompatibilityError(f"Pipeline state is unreadable: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise StateCompatibilityError(f"Pipeline state must be a JSON object: {path}")
    return payload


def _json_default(value):
    """Convert NumPy scalar values to native Python values for JSON."""
    module = type(value).__module__
    if module == "numpy" or module.startswith("numpy."):
        item = getattr(value, "item", None)
        if callable(item):
            return item()

    raise TypeError(
        f"Object of type {value.__class__.__name__} "
        "is not JSON serializable"
    )


def write_json_atomic(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        suffix=".tmp",
        prefix=f"{path.name}.",
        dir=path.parent,
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            json.dump(payload, handle, indent=2, sort_keys=True, default=_json_default)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise


class ExclusivePipelineLock:
    """Simple no-overlap lock; stale locks require explicit operator review."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.token = uuid.uuid4().hex
        self.acquired = False

    def __enter__(self) -> "ExclusivePipelineLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "pid": os.getpid(),
            "token": self.token,
            "created_at_utc": utc_now_iso(),
        }
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        try:
            descriptor = os.open(self.path, flags)
        except FileExistsError as exc:
            detail = ""
            try:
                existing = json.loads(self.path.read_text(encoding="utf-8"))
                detail = (
                    f" Existing lock pid={existing.get('pid')} "
                    f"created_at_utc={existing.get('created_at_utc')}."
                )
            except Exception:
                detail = " Existing lock is unreadable."
            raise PipelineLockedError(
                f"Unified pipeline lock already exists: {self.path}.{detail} "
                "Verify that no process is running before removing a stale lock."
            ) from exc
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        self.acquired = True
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if not self.acquired:
            return
        try:
            existing = json.loads(self.path.read_text(encoding="utf-8"))
            if existing.get("token") != self.token:
                raise PipelineLockedError(
                    f"Refusing to remove lock owned by another process: {self.path}"
                )
            self.path.unlink()
        finally:
            self.acquired = False


__all__ = [
    "ExclusivePipelineLock",
    "PipelineLockedError",
    "STATE_SCHEMA_VERSION",
    "StateCompatibilityError",
    "canonical_json_hash",
    "initial_pipeline_state",
    "processing_config_hash",
    "read_pipeline_state",
    "validate_pipeline_state",
    "write_json_atomic",
]
