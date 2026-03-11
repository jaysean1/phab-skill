# Phab — Phabricator Skill for AI Coding Agents

> A plug-and-play skill that lets AI coding agents (Claude Code, Cursor, Windsurf, etc.)
> manage Phabricator tickets through natural language.

No need to memorise CLI flags or API calls — just tell your AI agent what you want,
and it handles search, create, update, and team status for you.

### ✨ Features

| | Feature | What it does |
|---|---------|-------------|
| 🔍 | **Search & Query** | Find tickets by assignee, status, priority, keyword — in natural language |
| 📝 | **Create Ticket** | Turn a local Markdown file into a Phabricator ticket, one command |
| 🔄 | **Sync Ticket** | Push local edits to an existing ticket with safe read-merge-update |
| 👥 | **Team Status** | Workload overview — open counts, priority breakdown, per-person details |
| 📎 | **Auto File Upload** | Local images uploaded automatically; File ID written back to Markdown |
| ⚡ | **Skill Hot-reload** | Repo-level install — edit SKILL.md, save, and your AI agent picks up changes instantly. Fork & customise your own workflows on top of Phab |

> **Works with:** Claude Code `/phab` · Cursor · Windsurf · any agent that supports skill files

## Install

**One-line install** (run from your project root):

```bash
curl -fsSL https://raw.githubusercontent.com/jaysean1/phab-skill/main/install.sh | bash
```

This clones the repo into `.claude/skills/phab/` and installs Python dependencies.
Because it is a git clone, you can `git pull` inside the skill folder to update anytime.

> **Manual install** — if you prefer to do it yourself:
>
> ```bash
> mkdir -p .claude/skills
> git clone https://github.com/jaysean1/phab-skill.git .claude/skills/phab
> cd .claude/skills/phab/scripts && UV_CACHE_DIR=/tmp/uv-cache uv sync
> ```

## Setup (First Time)

After install, type `/phab` in Claude Code (or your AI agent) and it will guide you
through a quick 2-step setup:

1. **Phabricator URL** — your team's Phabricator instance (e.g. `https://phabricator.example.com`)
2. **API token** — get one at `<base_url>/settings/user/me/page/apitokens/`

That's it! Your **username is detected automatically** via the `user.whoami` API — no need
to type it in.

The skill runs a config check (`check_config.py`) every time it starts. If anything is
missing, it guides you through the setup interactively.

You can also run the config check manually:

```bash
cd .claude/skills/phab/scripts
UV_CACHE_DIR=/tmp/uv-cache uv run check_config.py
```

## Core Workflows

### Search Tickets

Find tickets by assignee, status, priority, or keyword.

```
"Show me all open tickets assigned to alice"
"Find high-priority bugs created this week"
```

### Create Ticket

Create a Phabricator ticket from a local Markdown file. Images are uploaded automatically.

```
"Create a ticket from prd.md with tag loadshift_team"
```

After creation, the ticket ID (e.g. `T123456`) is written back to the Markdown frontmatter
so you can update it later.

### Update Ticket

Sync changes from your local Markdown to an existing ticket. Uses a read-merge-update
workflow to avoid overwriting changes made on Phabricator.

```
"Update the ticket from prd.md"
"Add a comment to T123456: design review done"
```

### Team Status

Get a workload summary for your team — open ticket counts, priority breakdown,
and per-person details.

```
"Show team status"
```

## Key Features

### File Upload & Phab ID Writeback

When you create or update a ticket from Markdown, local images are automatically uploaded
to Phabricator. The File ID is written back as an HTML comment:

```markdown
<!-- Before -->
![Mockup](images/mockup.png)

<!-- After -->
![Mockup](images/mockup.png) <!-- F123456 -->
```

On subsequent updates, images with a File ID comment are **skipped** — no duplicate uploads.

### Targeted Update via Frontmatter `ticket_id`

The `ticket_id` field in your Markdown frontmatter links the file to a specific ticket:

```markdown
---
title: My Feature PRD
ticket_id: T123456
---
```

When you say "update the ticket from this file", the skill reads the existing ticket,
merges your local changes, and pushes the update — a safe read-merge-update workflow.

### Related Documents Cleanup

When uploading to Phabricator, the `## Related Documents` section is transformed:
- Entries with `ticket_id` → replaced with Phabricator ticket links
- Entries without `ticket_id` → removed (local file paths are dead links on Phabricator)

## File Structure

```
phab-skill/
├── README.md               # This file
├── SKILL.md                # Skill definition (name, description, instructions)
├── install.sh              # One-line installer
├── references/             # Detailed usage guides
│   ├── create-tickets.md
│   ├── file-upload.md
│   ├── query-tickets.md
│   ├── team-status.md
│   └── update-tickets.md
└── scripts/
    ├── config.example.yaml # Configuration template
    ├── .env.example        # API token template
    ├── check_config.py     # Startup config check (auto-fetches username)
    ├── setup.py            # Interactive setup wizard
    ├── config.py           # Configuration loader
    ├── phabricator.py      # Core Phabricator API client
    ├── markdown_utils.py   # Markdown processing
    ├── create_ticket.py    # Create tickets from Markdown
    ├── update_ticket.py    # Update tickets / add comments
    ├── search_tickets.py   # Search & filter tickets
    ├── get_ticket.py       # Get ticket details
    ├── upload_file.py      # File upload utility
    ├── team_status.py      # Team workload status
    └── pyproject.toml      # Python dependencies
```

## Configuration

After running setup, two files are created in `scripts/` (both git-ignored):

| File | Contents |
|------|----------|
| `config.yaml` | Phabricator URL, username, default tags, team members |
| `.env` | `PHABRICATOR_API_TOKEN=your_token_here` |

See `config.example.yaml` and `.env.example` for the template format.
