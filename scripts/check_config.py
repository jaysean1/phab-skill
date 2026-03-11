#!/usr/bin/env python3
# Check config.yaml and .env for required fields; auto-fetch username via user.whoami.
# Not for ticket operations — only for startup validation by the AI agent.

import json
import shutil
import sys
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
CONFIG_EXAMPLE_PATH = SCRIPT_DIR / "config.example.yaml"
ENV_PATH = SCRIPT_DIR / ".env"
ENV_EXAMPLE_PATH = SCRIPT_DIR / ".env.example"

# Placeholder values that mean "not configured yet"
BASE_URL_PLACEHOLDERS = {"", "https://your-phabricator-instance.com"}
TOKEN_PLACEHOLDERS = {"", "api-your-token-here"}
USERNAME_PLACEHOLDERS = {"", "your_username"}


def _ensure_files() -> list[str]:
    """Copy example files if missing. Return list of newly created file names."""
    created: list[str] = []
    if not CONFIG_PATH.exists():
        if CONFIG_EXAMPLE_PATH.exists():
            shutil.copy(CONFIG_EXAMPLE_PATH, CONFIG_PATH)
            created.append("config.yaml")
        else:
            created.append("config.yaml")  # still missing, will be caught later
    if not ENV_PATH.exists():
        if ENV_EXAMPLE_PATH.exists():
            shutil.copy(ENV_EXAMPLE_PATH, ENV_PATH)
            created.append(".env")
        else:
            created.append(".env")
    return created


def _read_config() -> dict | None:
    """Read and parse config.yaml. Return None if missing or invalid."""
    if not CONFIG_PATH.exists():
        return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError:
        return None


def _read_token() -> str:
    """Read PHABRICATOR_API_TOKEN from .env file."""
    if not ENV_PATH.exists():
        return ""
    load_dotenv(ENV_PATH, override=True)
    token = ""
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("PHABRICATOR_API_TOKEN="):
                token = line.split("=", 1)[1].strip()
    return token


def _fetch_username(base_url: str, token: str) -> str | None:
    """Call user.whoami to get the current user's username. Return None on failure."""
    try:
        url = f"{base_url.rstrip('/')}/api/user.whoami"
        resp = httpx.post(url, data={"api.token": token}, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result", {})
        return result.get("userName")
    except Exception:
        return None


def _write_username_to_config(cfg: dict, username: str) -> None:
    """Write username into config.yaml while preserving other fields."""
    cfg["username"] = username
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)


def main() -> None:
    missing: list[str] = []
    empty: list[str] = []

    # Step 1: ensure files exist (copy from examples if needed)
    created = _ensure_files()

    # Step 2: read config.yaml
    cfg = _read_config()
    if cfg is None:
        missing.append("config.yaml")
        print(json.dumps({"ok": False, "missing": missing, "empty": empty}))
        sys.exit(0)

    # Step 3: check base_url
    base_url = str(cfg.get("base_url", "")).strip()
    if not base_url or base_url in BASE_URL_PLACEHOLDERS or not base_url.startswith("https://"):
        empty.append("base_url")

    # Step 4: read and check token
    token = _read_token()
    if not token or token in TOKEN_PLACEHOLDERS or not token.startswith("api-"):
        empty.append("PHABRICATOR_API_TOKEN")

    # If base_url or token is bad, report now
    if empty or missing:
        result = {"ok": False, "missing": missing, "empty": empty}
        if created:
            result["created"] = created
        print(json.dumps(result))
        sys.exit(0)

    # Step 5: auto-fetch username via user.whoami
    username = str(cfg.get("username", "")).strip()
    if not username or username in USERNAME_PLACEHOLDERS:
        fetched = _fetch_username(base_url, token)
        if fetched:
            _write_username_to_config(cfg, fetched)
            username = fetched
        else:
            empty.append("username (whoami failed)")
            print(json.dumps({"ok": False, "missing": missing, "empty": empty}))
            sys.exit(0)

    # All good
    result = {"ok": True, "username": username}
    if created:
        result["created"] = created
    print(json.dumps(result))


if __name__ == "__main__":
    main()
