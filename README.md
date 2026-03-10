# Phabricator Tickets Skill

A shareable [Claude Code](https://claude.com/claude-code) skill for managing Phabricator tickets from the command line.

## What this skill does

- **Search** tickets by assignee, author, status, priority
- **Create** tickets from Markdown files with automatic image upload
- **Update** tickets with description sync and incremental image upload
- **Team status** showing workload summary table and per-person breakdown

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- A Phabricator account with an API token

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/jaysean1/tickets-shared.git
cd tickets-shared/scripts

# 2. Install dependencies
UV_CACHE_DIR=/tmp/uv-cache uv sync

# 3. Run guided setup
UV_CACHE_DIR=/tmp/uv-cache uv run setup.py
```

The setup script will:
1. Create `config.yaml` and `.env` from example templates
2. Guide you through filling in your Phabricator URL, username, and API token
3. Validate your configuration
4. Test the API connection

## Quick Start

```bash
cd tickets-shared/scripts

# Search your open tickets
UV_CACHE_DIR=/tmp/uv-cache uv run search_tickets.py -a your_username -s open

# Get ticket details
UV_CACHE_DIR=/tmp/uv-cache uv run get_ticket.py T123456

# Create ticket from Markdown
UV_CACHE_DIR=/tmp/uv-cache uv run create_ticket.py --file prd.md --tags loadshift_team

# Update ticket from Markdown
UV_CACHE_DIR=/tmp/uv-cache uv run update_ticket.py --file prd.md

# Team workload overview
UV_CACHE_DIR=/tmp/uv-cache uv run team_status.py
```

## File Structure

```
tickets-shared/
├── README.md              # This file
├── SKILL.md               # Skill definition for Claude Code
├── .gitignore
├── references/            # Detailed usage guides
│   ├── create-tickets.md
│   ├── file-upload.md
│   ├── query-tickets.md
│   ├── team-status.md
│   └── update-tickets.md
└── scripts/
    ├── config.example.yaml  # Configuration template
    ├── .env.example         # Environment variable template
    ├── config.py            # Configuration loader
    ├── setup.py             # Guided setup script
    ├── phabricator.py       # Core Phabricator API
    ├── markdown_utils.py    # Markdown processing utilities
    ├── create_ticket.py     # Create tickets CLI
    ├── update_ticket.py     # Update tickets CLI
    ├── search_tickets.py    # Search tickets CLI
    ├── get_ticket.py        # Get ticket details CLI
    ├── upload_file.py       # File upload CLI
    ├── team_status.py       # Team workload status CLI
    ├── pyproject.toml       # Python project config
    └── uv.lock              # Dependency lock file
```

## Configuration

After running `setup.py`, two files are created (git-ignored):

- **`scripts/config.yaml`** — Phabricator URL, username, tags, team members
- **`scripts/.env`** — API token only

See `config.example.yaml` and `.env.example` for the template format.
