"""Local configuration management for Text Graphics Agent.

Reads and writes config.json in the current working directory to store
API Keys, providers, model names, and scope boundaries safely.
"""

from __future__ import annotations

import json
import os
from typing import Any

CONFIG_FILE = "config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "api_provider": "gemini",
    "api_key": "",
    "model_name": "gemini-2.5-flash",
    "allowed_scopes": [
        "app/config/settings.json",
        "app/static/play.html"
    ],
    "required_anchors": [
        "system_prompt",
        "NPC dialogue"
    ],
    "disabled_constraints": []
}


def normalize_config_data(config_data: dict[str, Any]) -> dict[str, Any]:
    """Returns a copy with comma-separated UI fields normalized to lists."""
    normalized = dict(config_data)
    if isinstance(normalized.get("allowed_scopes"), str):
        normalized["allowed_scopes"] = [
            s.strip() for s in normalized["allowed_scopes"].split(",") if s.strip()
        ]
    if isinstance(normalized.get("required_anchors"), str):
        normalized["required_anchors"] = [
            a.strip() for a in normalized["required_anchors"].split(",") if a.strip()
        ]
    if isinstance(normalized.get("disabled_constraints"), str):
        normalized["disabled_constraints"] = [
            c.strip() for c in normalized["disabled_constraints"].split(",") if c.strip()
        ]
    return normalized


def load_config() -> dict[str, Any]:
    """Loads configuration from local config.json. Creates it with defaults if missing."""
    config_path = os.path.abspath(os.path.join(os.getcwd(), CONFIG_FILE))
    
    if not os.path.exists(config_path):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
        
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure all keys from DEFAULT_CONFIG exist
            merged = DEFAULT_CONFIG.copy()
            merged.update(data)
            return merged
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config_data: dict[str, Any]) -> bool:
    """Saves config data back to config.json in the working directory."""
    config_path = os.path.abspath(os.path.join(os.getcwd(), CONFIG_FILE))
    try:
        config_data = normalize_config_data(config_data)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
