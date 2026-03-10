# Query Tickets Reference

## Quick Actions

Common queries you'll use frequently:

```bash
cd .claude/skills/tickets/scripts

# My open tickets
UV_CACHE_DIR=/tmp/uv-cache uv run search_tickets.py -a jqian -s open

# My high priority tickets
UV_CACHE_DIR=/tmp/uv-cache uv run search_tickets.py -a jqian -p high -p unbreak

# Recent tickets I created
UV_CACHE_DIR=/tmp/uv-cache uv run search_tickets.py --author jqian -t 7d

# All open high-priority tickets
UV_CACHE_DIR=/tmp/uv-cache uv run search_tickets.py -s open -p high -t 14d
```

---

## search_tickets.py

Search for Phabricator tickets by various criteria.

### Synopsis

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run search_tickets.py [OPTIONS]
```

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--assignee` | `-a` | Filter by assignee username (repeatable) |
| `--author` | | Filter by author username (repeatable) |
| `--status` | `-s` | Filter by status: open, resolved, wontfix, invalid (repeatable) |
| `--priority` | `-p` | Filter by priority: unbreak, triage, high, normal, low, wish (repeatable) |
| `--time-range` | `-t` | Time range to search: 7d, 14d, 30d, 60d, 90d (default: 30d) |
| `--limit` | `-l` | Max results (default: 50, max: 100) |
| `--json` | | Output as JSON |

At least one filter (assignee, author, status, or priority) is required.

### Examples

```bash
# Find open tickets assigned to jqian
UV_CACHE_DIR=/tmp/uv-cache uv run search_tickets.py --assignee jqian --status open

# Find high priority tickets from the last week
UV_CACHE_DIR=/tmp/uv-cache uv run search_tickets.py --priority high --time-range 7d

# Find tickets by multiple authors
UV_CACHE_DIR=/tmp/uv-cache uv run search_tickets.py --author jqian --author smanton

# JSON output for scripting
UV_CACHE_DIR=/tmp/uv-cache uv run search_tickets.py -a jqian -s open --json
```

### Output Format

```
Found 3 ticket(s):

  T123456 🟢 Fix payment validation
    Status: Open | Priority: High
    Owner: jqian | Modified: 2024-01-15
    https://phabricator.tools.flnltd.com/T123456

  T123457 ✅ Add logging to checkout
    Status: Resolved | Priority: Normal
    Owner: jqian | Modified: 2024-01-14
    https://phabricator.tools.flnltd.com/T123457
```

---

## get_ticket.py

Get detailed information about a specific ticket.

### Synopsis

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run get_ticket.py TICKET_ID [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `TICKET_ID` | The ticket ID (e.g., T123456 or 123456) |

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--no-comments` | | Don't include comment history |
| `--no-diffs` | | Don't include related diffs |
| `--time-range` | `-t` | Time range for activity: 7d, 14d, 30d, 60d, 90d (default: 30d) |
| `--full-description` | | Show full description without truncation |
| `--json` | | Output as JSON |

### Examples

```bash
# Basic ticket info
UV_CACHE_DIR=/tmp/uv-cache uv run get_ticket.py T123456

# Full description without truncation
UV_CACHE_DIR=/tmp/uv-cache uv run get_ticket.py T123456 --full-description

# Just ticket details, no activity
UV_CACHE_DIR=/tmp/uv-cache uv run get_ticket.py T123456 --no-comments --no-diffs

# JSON output
UV_CACHE_DIR=/tmp/uv-cache uv run get_ticket.py T123456 --json
```

### Output Format

```
## T123456: Fix payment validation

**Status:** 🟢 Open | **Priority:** High
**Owner:** jqian | **Author:** smanton
**Created:** 2024-01-10 | **Modified:** 2024-01-15
**URL:** https://phabricator.tools.flnltd.com/T123456

### Description
Payment validation fails when user enters special characters...

### Recent Activity
- **[2024-01-15] jqian** commented:
  > Looking into this now, seems to be a regex issue
- **[2024-01-14] smanton** changed status: Stalled → Open

### Related Diffs
- **D789012** 🔍 Fix regex in payment validator (Needs Review)
```

---

## Status Emojis

| Status | Emoji |
|--------|-------|
| Open | 🟢 |
| Resolved | ✅ |
| Closed | 🔒 |
| In Progress | 🔨 |
| Stalled | ⏸️ |
| Invalid | ❌ |

## Priority Levels

| Priority | Description |
|----------|-------------|
| unbreak | Highest - Production is broken |
| triage | Needs immediate attention |
| high | Important, do soon |
| normal | Default priority |
| low | Nice to have |
| wish | Someday/maybe |
