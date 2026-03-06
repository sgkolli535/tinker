from __future__ import annotations

import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


def _score(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def load_json(path: str | Path) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def fuzzy_match(identified_name: str, entries: list[dict[str, Any]], key: str = "id") -> tuple[dict[str, Any] | None, float]:
    best: dict[str, Any] | None = None
    best_score = 0.0
    for entry in entries:
        candidate = str(entry.get(key, ""))
        score = max(_score(identified_name, candidate), _score(identified_name, str(entry.get("type", ""))))
        if score > best_score:
            best = entry
            best_score = score
    return best, best_score
