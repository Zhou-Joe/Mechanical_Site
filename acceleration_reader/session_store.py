from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import Any

from django.conf import settings

from .accdata import AccData


SESSION_KEY = "acceleration_reader"
SESSION_ROOT = "acceleration_reader"


def get_session_state(request) -> dict[str, Any]:
    state = request.session.get(SESSION_KEY)
    if not isinstance(state, dict):
        state = {"datasets": []}
        request.session[SESSION_KEY] = state
        request.session.modified = True
    state.setdefault("datasets", [])
    return state


def save_session_state(request, state: dict[str, Any]) -> None:
    request.session[SESSION_KEY] = state
    request.session.modified = True


def ensure_session_root(request) -> Path:
    if not request.session.session_key:
        request.session.create()
    root = Path(settings.MEDIA_ROOT) / SESSION_ROOT / request.session.session_key
    root.mkdir(parents=True, exist_ok=True)
    return root


def build_state_path(request, dataset_id: str) -> Path:
    return ensure_session_root(request) / f"{dataset_id}.txt"


def relative_media_path(path: Path) -> str:
    return str(path.relative_to(Path(settings.MEDIA_ROOT))).replace(os.sep, "/")


def persist_dataset(request, dataset_id: str, data: AccData) -> str:
    state_path = build_state_path(request, dataset_id)
    data.reformat(overwrite=True, setting_angle=False, cutoff=getattr(data, "cutoff", 5))
    data.rawdata.to_csv(state_path, sep="\t", header=False, index=False)
    return relative_media_path(state_path)


def add_dataset(request, data: AccData, dataset_type: str, source_name: str | None = None) -> dict[str, Any]:
    dataset_id = uuid.uuid4().hex
    state_file = persist_dataset(request, dataset_id, data)
    record = {
        "id": dataset_id,
        "name": data.filename,
        "dataset_type": dataset_type,
        "source_name": source_name or data.filename,
        "state_file": state_file,
    }
    state = get_session_state(request)
    state["datasets"].append(record)
    save_session_state(request, state)
    return record


def get_dataset_record(request, dataset_id: str) -> dict[str, Any] | None:
    for record in get_session_state(request)["datasets"]:
        if record.get("id") == dataset_id:
            return record
    return None


def find_dataset_record(request, *, dataset_id: str | None = None, name: str | None = None) -> dict[str, Any] | None:
    if dataset_id:
        return get_dataset_record(request, dataset_id)
    if name:
        for record in get_session_state(request)["datasets"]:
            if record.get("name") == name:
                return record
    return None


def load_dataset(request, record: dict[str, Any], cutoff: int) -> AccData:
    state_path = Path(settings.MEDIA_ROOT) / record["state_file"]
    return AccData(str(state_path), cutoff=cutoff)


def update_dataset(request, dataset_id: str, data: AccData) -> dict[str, Any]:
    state = get_session_state(request)
    for record in state["datasets"]:
        if record.get("id") == dataset_id:
            record["state_file"] = persist_dataset(request, dataset_id, data)
            record["name"] = data.filename
            save_session_state(request, state)
            return record
    raise KeyError(f"Dataset not found: {dataset_id}")


def remove_dataset(request, dataset_id: str) -> bool:
    state = get_session_state(request)
    removed = False
    datasets = []
    for record in state["datasets"]:
        if record.get("id") == dataset_id:
            removed = True
            state_path = Path(settings.MEDIA_ROOT) / record["state_file"]
            if state_path.exists():
                state_path.unlink()
            continue
        datasets.append(record)
    state["datasets"] = datasets
    save_session_state(request, state)
    return removed


def clear_datasets(request) -> None:
    session_key = request.session.session_key
    if session_key:
        root = Path(settings.MEDIA_ROOT) / SESSION_ROOT / session_key
        if root.exists():
            shutil.rmtree(root)
    request.session.pop(SESSION_KEY, None)
    request.session.modified = True

