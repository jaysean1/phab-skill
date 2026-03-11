#!/usr/bin/env bash
# One-line installer for Phab skill.
# Not for use outside of a project root directory.

set -euo pipefail

SKILL_DIR=".claude/skills/phab"
REPO_URL="https://github.com/jaysean1/phab-skill.git"

# --- Check: are we in a project root? ---
if [ ! -d ".claude" ] && [ ! -f ".git/config" ]; then
  echo "Error: Run this from your project root (expected .claude/ or .git/ directory)."
  echo "  cd /path/to/your/project && curl -fsSL ... | bash"
  exit 1
fi

# --- Check: already installed? ---
if [ -d "$SKILL_DIR" ]; then
  echo "Phab skill already exists at $SKILL_DIR"
  echo "To update, run: cd $SKILL_DIR && git pull"
  exit 0
fi

# --- Clone ---
echo "Installing Phab skill..."
mkdir -p .claude/skills
git clone "$REPO_URL" "$SKILL_DIR"

# --- Install Python dependencies ---
echo "Installing Python dependencies..."
cd "$SKILL_DIR/scripts"
UV_CACHE_DIR=/tmp/uv-cache uv sync

echo ""
echo "Done! Phab skill installed at $SKILL_DIR"
echo ""
echo "Next step: type /phab in Claude Code to start the guided setup."
