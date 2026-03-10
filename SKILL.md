---
name: tickets
description: This skill manages Phabricator ticket workflows. It supports (1) querying tickets by various criteria, (2) creating new tickets with optional image attachments from Markdown, (3) updating existing tickets using a read-merge-update approach, (4) uploading files to the file server, and (5) showing team workload status.
---

# Tickets Skill

Manage Phabricator tickets with full CRUD operations, image upload with File ID tracking, and Markdown-based workflow.

## First Time Setup

Run the guided setup script to configure your environment:

```bash
cd tickets-shared/scripts
UV_CACHE_DIR=/tmp/uv-cache uv sync
UV_CACHE_DIR=/tmp/uv-cache uv run setup.py
```

This will:
1. Create `config.yaml` and `.env` from example templates
2. Guide you through filling in your settings
3. Validate your configuration
4. Test the API connection

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

```bash
cd tickets-shared/scripts
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
