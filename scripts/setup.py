#!/usr/bin/env python3
# Interactive setup script for the tickets skill.
# Not for ticket operations — only for initial configuration.

import asyncio
import os
import shutil
import sys
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
CONFIG_EXAMPLE_PATH = SCRIPT_DIR / "config.example.yaml"
ENV_PATH = SCRIPT_DIR / ".env"
ENV_EXAMPLE_PATH = SCRIPT_DIR / ".env.example"


def print_header() -> None:
    print()
    print("=" * 60)
    print("  Phabricator Tickets Skill — Setup")
    print("=" * 60)
    print()
    print("This skill lets you search, create, and update")
    print("Phabricator tickets from the command line.")
    print()
    print("Setup has 3 phases:")
    print("  1. File Preparation — copy example configs")
    print("  2. Validation — check your settings")
    print("  3. API Connection Test — verify everything works")
    print()


def phase_1_prepare_files() -> bool:
    """Phase 1: Ensure config.yaml and .env exist."""
    print("-" * 60)
    print("Phase 1: File Preparation")
    print("-" * 60)
    print()

    # config.yaml
    if CONFIG_PATH.exists():
        print(f"  config.yaml already exists: {CONFIG_PATH}")
    else:
        shutil.copy(CONFIG_EXAMPLE_PATH, CONFIG_PATH)
        print(f"  Created config.yaml from example: {CONFIG_PATH}")

    # .env
    if ENV_PATH.exists():
        print(f"  .env already exists: {ENV_PATH}")
    else:
        shutil.copy(ENV_EXAMPLE_PATH, ENV_PATH)
        print(f"  Created .env from example: {ENV_PATH}")

    print()
    print("Please open and edit these two files:")
    print()
    print(f"  1. {CONFIG_PATH}")
    print(f"  2. {ENV_PATH}")
    print()
    print("Fields to fill in config.yaml:")
    print("  - base_url     : Your Phabricator instance URL")
    print("  - username      : Your Phabricator username")
    print("  - required_tags : Tags auto-added to new tickets")
    print("  - team_members  : Team member list (for team_status)")
    print()
    print("Fields to fill in .env:")
    print("  - PHABRICATOR_API_TOKEN")
    print("    Get your token at:")
    print("    <base_url>/settings/user/<username>/page/apitokens/")
    print()

    input("Press Enter when you have finished editing both files...")
    print()
    return True


def phase_2_validate() -> bool:
    """Phase 2: Validate config.yaml and .env values."""
    print("-" * 60)
    print("Phase 2: Validation")
    print("-" * 60)
    print()

    all_ok = True

    # --- config.yaml exists and parses ---
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        print("  ✅ config.yaml is valid YAML")
    except FileNotFoundError:
        print("  ❌ config.yaml not found")
        return False
    except yaml.YAMLError as e:
        print(f"  ❌ config.yaml has invalid YAML: {e}")
        return False

    # --- base_url ---
    base_url = cfg.get("base_url", "")
    if base_url and str(base_url).startswith("https://"):
        print(f"  ✅ base_url: {base_url}")
    else:
        print(f"  ❌ base_url must start with https:// (got: {base_url!r})")
        all_ok = False

    # --- username ---
    username = cfg.get("username", "")
    if username and str(username) != "your_username":
        print(f"  ✅ username: {username}")
    else:
        print(f"  ❌ username is empty or still the placeholder (got: {username!r})")
        all_ok = False

    # --- .env: PHABRICATOR_API_TOKEN ---
    token = ""
    try:
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("PHABRICATOR_API_TOKEN="):
                    token = line.split("=", 1)[1].strip()
    except FileNotFoundError:
        print("  ❌ .env file not found")
        all_ok = False

    if token and token.startswith("api-") and token != "api-your-token-here":
        print(f"  ✅ PHABRICATOR_API_TOKEN: {token[:8]}...")
    else:
        print(f"  ❌ PHABRICATOR_API_TOKEN must start with 'api-' (got: {token[:12]!r}...)")
        all_ok = False

    # --- Optional warnings ---
    required_tags = cfg.get("required_tags", [])
    if not required_tags:
        print("  ⚠️  No required_tags configured — tickets will be created without default tags")

    team_members = cfg.get("team_members", [])
    if not team_members:
        print("  ⚠️  No team_members configured — team_status.py will not work")

    print()

    if not all_ok:
        print("Some required fields are missing or invalid.")
        print("Please fix the issues above and run setup.py again.")
        return False

    return True


async def phase_3_api_test() -> bool:
    """Phase 3: Test API connectivity."""
    print("-" * 60)
    print("Phase 3: API Connection Test")
    print("-" * 60)
    print()

    # Import after validation so config is available
    sys.path.insert(0, str(SCRIPT_DIR))

    # Force reload of phabricator module (it reads config at import time)
    import phabricator as ph

    # Read username from config
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    username = cfg.get("username", "")

    # Test 1: Resolve username
    print(f"  Testing username resolution for '{username}'...")
    try:
        phid = await ph.resolve_username_to_phid(username)
        if phid:
            print(f"  ✅ Username resolved: {username} -> {phid[:20]}...")
        else:
            print(f"  ❌ Username '{username}' not found on Phabricator")
            print("     Check that your username is correct in config.yaml")
            return False
    except Exception as e:
        print(f"  ❌ Username resolution failed: {e}")
        print("     Check your base_url and API token")
        return False

    # Test 2: Search tickets
    print(f"  Testing ticket search for '{username}'...")
    try:
        result = await ph.search_tickets(
            assignees=[username],
            statuses=["open"],
            limit=1,
        )
        if result.get("error"):
            print(f"  ❌ Search failed: {result['error']}")
            return False
        count = len(result.get("tickets", []))
        print(f"  ✅ Search succeeded ({count} ticket(s) returned)")
    except Exception as e:
        print(f"  ❌ Search failed: {e}")
        return False

    print()
    print("=" * 60)
    print("  ✅ Setup complete! You're ready to use the tickets skill.")
    print("=" * 60)
    print()
    return True


async def main() -> int:
    print_header()

    if not phase_1_prepare_files():
        return 1

    if not phase_2_validate():
        return 1

    if not await phase_3_api_test():
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
