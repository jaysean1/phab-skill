---
name: phab
description: Phabricator skill for AI coding agents. Search, create, update tickets and view team status — all through natural language. Supports Markdown-based workflows with automatic image upload and File ID tracking.
---

# Phab Skill

Manage Phabricator tickets with full CRUD operations, image upload with File ID tracking, and Markdown-based workflow.

## Startup Config Check

**Every time this skill is invoked**, run the config check script first.

> **Path resolution:** The `scripts/` directory is located next to this SKILL.md file.
> Resolve the absolute path of this SKILL.md, then append `scripts/` to get the scripts directory.
> Example: if this file is at `/home/user/project/.claude/skills/phab/SKILL.md`,
> the scripts directory is `/home/user/project/.claude/skills/phab/scripts/`.

```bash
cd <SCRIPTS_DIR>   # Resolved absolute path to the scripts/ directory next to this file
UV_CACHE_DIR=/tmp/uv-cache uv sync  # First time only
UV_CACHE_DIR=/tmp/uv-cache uv run check_config.py
```

The script outputs a single JSON line. Parse it and follow the rules below:

### If `ok: true`

Config is valid. Proceed to the user's request (search, create, update, etc.).

### If `ok: false`

Guide the user to fill in the missing values. The `missing` and `empty` fields tell you what is needed.

> **IMPORTANT: Never collect sensitive information (API tokens, passwords) in the conversation.**
> Always direct the user to edit the config files themselves.

**Only 2 user inputs are required:**

1. **`base_url`** — Tell the user: "Please open `<SCRIPTS_DIR>/config.yaml` and set the `base_url` field to your Phabricator instance URL (e.g. `https://phabricator.example.com`)."

2. **`PHABRICATOR_API_TOKEN`** — Tell the user:
   - "Go to `<base_url>/settings/user/me/page/apitokens/` to create a token."
   - "Then open `<SCRIPTS_DIR>/.env` and paste your token as `PHABRICATOR_API_TOKEN=<your-token>`."
   - **Do NOT ask the user to paste the token in this conversation.**

3. **`username`** — **Do NOT ask the user.** After base_url and token are set, re-run `check_config.py`. It calls the `user.whoami` API to fetch and write the username automatically.

After the user confirms they have edited the files, re-run `check_config.py` to confirm `ok: true`.

## User Context

| Setting | Value | Notes |
|---------|-------|-------|
| Username | (see config.yaml) | Default owner for new tickets |
| Default Priority | `normal` | Override with `--priority` |
| Required Tags | (see config.yaml) | Always added to new tickets |

### Optional Tags (Choose ONE based on content)

> Use underscore format (e.g., `user_growth_loadshift`), not display names.
> See `config.yaml` for the full list of optional tags and when to use each.

## Capabilities

- **Search tickets** by assignee, author, status, priority
- **Get ticket details** with comments and related diffs
- **Create tickets** from Markdown files (auto-uploads images)
- **Update tickets** with description sync and incremental image upload
- **Upload files** with File ID writeback to Markdown
- **Team status** showing workload table and per-person breakdown

## Quick Start

All commands below must run from `<SCRIPTS_DIR>` (the `scripts/` directory next to this file).

```bash
cd <SCRIPTS_DIR>
UV_CACHE_DIR=/tmp/uv-cache uv sync  # First time only

# Search your open tickets
UV_CACHE_DIR=/tmp/uv-cache uv run search_tickets.py -a <username> -s open

# Get full ticket details (description + comments, no truncation)
UV_CACHE_DIR=/tmp/uv-cache uv run get_ticket.py T123456 --full-description --full-comments

# Get ticket with more activity history (default is 10)
UV_CACHE_DIR=/tmp/uv-cache uv run get_ticket.py T123456 --activity-limit 30

# Add a comment to a ticket
UV_CACHE_DIR=/tmp/uv-cache uv run update_ticket.py T123456 --comment "Your comment here"

# Create ticket from Markdown
UV_CACHE_DIR=/tmp/uv-cache uv run create_ticket.py --file prd.md --tags loadshift_team

# Update ticket from Markdown
UV_CACHE_DIR=/tmp/uv-cache uv run update_ticket.py --file prd.md

# Team workload status
UV_CACHE_DIR=/tmp/uv-cache uv run team_status.py
```

## Execution Standard (Sandbox)

- Always run UV commands with `UV_CACHE_DIR=/tmp/uv-cache` prefix in this repository.
- Do not use plain `uv run ...` or plain `uv sync` in sandbox mode.
- This avoids write errors to `~/.cache/uv` under `workspace-write`.

## Key Behavior: File ID Writeback

When uploading images, the skill writes back Phabricator File IDs as HTML comments:

```markdown
<!-- Before upload -->
![Mockup](images/mockup.png)

<!-- After upload -->
![Mockup](images/mockup.png) <!-- F123456 -->
```

This enables **incremental updates** - only new images are uploaded on subsequent syncs.

## Key Behavior: Related Documents Cleanup

When uploading to Phabricator, the `## Related Documents` section is automatically transformed:

- **Entries with ticket_id** (e.g., `(T324178)`): local file link is replaced with a Phabricator ticket link
- **Entries without ticket_id**: removed entirely (local file paths are dead links on Phabricator)
- **Historical format compatibility**: parser accepts both `—` and `-` as description separators for legacy PRDs
- **New PRD recommendation**: use `—` separator in related documents for consistent output
- **Empty section**: if no entries remain after filtering, the entire section is removed

## Key Behavior: Strict Asset Validation

For both `create_ticket.py --file` and `update_ticket.py --file`, the workflow enforces strict checks before any API write:

- If any local image path in Markdown is missing on disk, the command fails.

## Frontmatter Writeback

After ticket creation, only `ticket_id` is written back to frontmatter:

```markdown
---
title: My Feature PRD
ticket_id: T123456    <!-- Auto-added after creation -->
---
```

Other fields (`priority`, `owner`, `tags`) are read-only inputs.

## Environment Setup

Requires `PHABRICATOR_API_TOKEN` in `.env` file (created during setup):

```bash
# In scripts/.env
PHABRICATOR_API_TOKEN=your_token_here
```

Get your token at: `<base_url>/settings/user/<username>/page/apitokens/`

## References

| Document | Use Case |
|----------|----------|
| [Query Tickets](references/query-tickets.md) | Search tickets, view details, preset queries |
| [Create Tickets](references/create-tickets.md) | Create from Markdown, tag selection rules |
| [Update Tickets](references/update-tickets.md) | Sync changes, status updates |
| [File Upload](references/file-upload.md) | Upload images, File ID tracking |
| [Team Status](references/team-status.md) | Team workload overview, output format |
