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
        # Standardize allowed_scopes and required_anchors to lists
        if isinstance(config_data.get("allowed_scopes"), str):
            config_data["allowed_scopes"] = [
                s.strip() for s in config_data["allowed_scopes"].split(",") if s.strip()
            ]
        if isinstance(config_data.get("required_anchors"), str):
            config_data["required_anchors"] = [
                a.strip() for a in config_data["required_anchors"].split(",") if a.strip()
            ]
        if isinstance(config_data.get("disabled_constraints"), str):
            config_data["disabled_constraints"] = [
                c.strip() for c in config_data["disabled_constraints"].split(",") if c.strip()
            ]

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
