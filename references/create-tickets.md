# Create Tickets Reference

## create_ticket.py

Create a new Phabricator ticket from a Markdown file or direct input.

### Synopsis

```bash
# From Markdown file
UV_CACHE_DIR=/tmp/uv-cache uv run create_ticket.py --file PATH [OPTIONS]

# Initialize frontmatter only (no ticket creation)
UV_CACHE_DIR=/tmp/uv-cache uv run create_ticket.py --file PATH --init [--title-override TITLE]

# Direct creation
UV_CACHE_DIR=/tmp/uv-cache uv run create_ticket.py --title TITLE [OPTIONS]
```

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--file` | `-f` | Markdown file to create ticket from |
| `--title` | `-t` | Ticket title (for direct creation) |
| `--init` | | Initialize frontmatter only (use with --file) |
| `--title-override` | | Override title for --init mode |
| `--skip-mermaid` | | Skip automatic Mermaid conversion (strict validation still enforced) |
| `--description` | `-d` | Ticket description (only with --title) |
| `--tags` | | Project/tag names to add (space-separated) |
| `--owner` | `-o` | Username to assign the ticket to |
| `--parent` | `-p` | Parent ticket ID (e.g., T123456) for sub-task |
| `--priority` | | Priority: unbreak, triage, high, normal, low, wish |
| `--json` | | Output as JSON |

---

## Tag Selection

See [SKILL.md](../SKILL.md#optional-tags-choose-one-based-on-content) for available tags.

**Quick reference:**
- Required: `loadshift_team`
- Optional: Choose ONE based on content category

### Category Detection Keywords

Use these keywords to auto-detect which optional tag slug to use:

**`basic_user_experience_loadshift`** (Basic User Experience):
- UI, UX, interface, design, usability
- User feedback, user testing
- Mobile experience, responsive
- Accessibility, navigation

**`ops_enterprise_team_efficiency_improvement_loadshift`** (Ops / Enterprise Efficiency):
- Admin, dashboard, reporting
- Automation, workflow, efficiency
- Operations, enterprise, management
- Analytics, metrics, monitoring

**`user_growth_loadshift`** (User Growth):
- Onboarding, activation, retention
- Marketing, conversion, funnel
- Engagement, notification, email
- Referral, growth, acquisition

---

## Markdown File Format

The Markdown file can include YAML frontmatter:

```markdown
---
ticket: t123456
---

# My Feature PRD

## Overview

Description of the feature...

## Mockups

![Flow Diagram](images/flow.png)
![UI Design](images/design.png)
```

> 💡 **Best Practice:** Keep frontmatter minimal. Only `title` is needed before creation. The `ticket_id` will be auto-added after.

### Frontmatter Fields

| Field | Description | Writeback |
|-------|-------------|-----------|
| `title` | Ticket title | No |
| `ticket_id` | Phabricator ticket ID | **Yes** ✅ |

---

## What Happens on Creation

1. **Mermaid checkpoint** - Convert Mermaid diagrams to PNG (unless `--skip-mermaid`)
2. **Strict Mermaid validation** - Every Mermaid block must have a matching PNG reference and local PNG file
3. **Strict local image validation** - Every local Markdown image path must exist on disk
4. **Parse frontmatter** for metadata
5. **Extract local images** from Markdown (including Mermaid PNGs)
6. **Upload images** to Phabricator
7. **Write back File IDs** as HTML comments: `![alt](path) <!-- F123456 -->`
8. **Convert images** to Remarkup format: `{F123456}`
9. **Transform Related Documents** for Phabricator:
   - Entries with `(Txxxxxx)` become clickable Phabricator links
   - Entries without ticket_id are removed from uploaded description
   - Historical separator compatibility: both `—` and `-` are accepted
10. **Create ticket** with description
11. **Write back ticket_id** to frontmatter
12. **Save updated Markdown** file

---

## Document Initialization (`--init`)

Use `--init` to prepare a Markdown document before ticket creation:

```bash
# Initialize with auto-detected title (from H1 heading)
UV_CACHE_DIR=/tmp/uv-cache uv run create_ticket.py --file doc.md --init

# Initialize with explicit title
UV_CACHE_DIR=/tmp/uv-cache uv run create_ticket.py --file doc.md --init --title-override "My Custom Title"
```

**What `--init` does:**
1. Checks if file already has a ticket_id (error if yes)
2. Determines title: `--title-override` > frontmatter > H1 heading
3. Creates/updates frontmatter with title field
4. Does NOT create a ticket

**Use cases:**
- Prepare multiple documents for batch ticket creation
- Verify title extraction before committing to ticket creation
- Set up frontmatter structure for new documents

---

## Mermaid Diagram Conversion

The script automatically converts Mermaid code blocks to PNG images before creating tickets.

**How it works:**
1. Detects Mermaid blocks without corresponding PNG images
2. Calls `mermaid-to-png` skill to convert diagrams
3. Re-reads the file to include new PNGs in upload

**Skip conversion:**
```bash
UV_CACHE_DIR=/tmp/uv-cache uv run create_ticket.py --file doc.md --skip-mermaid --tags loadshift_team
```

> ⚠️ `--skip-mermaid` only skips **auto-conversion**.  
> It does **not** skip validation. If Mermaid blocks still have no valid PNG mapping, creation fails.

**Requirements:**
- Node.js must be installed
- `mermaid-to-png` skill must be present in `.claude/skills/`

**Error handling:**
- Missing Node.js → Error, stop ticket creation
- Script not found → Error, stop ticket creation
- Conversion timeout (5min) → Error, stop ticket creation
- Mermaid block without matching PNG reference → Error, stop ticket creation
- Mermaid PNG path exists in Markdown but file missing on disk → Error, stop ticket creation
- Any local image path missing on disk → Error, stop ticket creation

---

## Examples

```bash
# Create from Markdown file (always include loadshift_team!)
UV_CACHE_DIR=/tmp/uv-cache uv run create_ticket.py --file prd.md --tags loadshift_team

# Add multiple tags
UV_CACHE_DIR=/tmp/uv-cache uv run create_ticket.py --file prd.md --tags loadshift_team webapp payments

# Specify owner and priority
UV_CACHE_DIR=/tmp/uv-cache uv run create_ticket.py --file prd.md --tags loadshift_team --owner jqian --priority high

# Create as sub-task
UV_CACHE_DIR=/tmp/uv-cache uv run create_ticket.py --file subtask.md --tags loadshift_team --parent T100000

# Direct creation (no file)
UV_CACHE_DIR=/tmp/uv-cache uv run create_ticket.py --title "Fix login bug" --description "Bug details" --tags loadshift_team bug --priority high

# JSON output for scripting
UV_CACHE_DIR=/tmp/uv-cache uv run create_ticket.py --file prd.md --tags loadshift_team --json
```

---

## Output

```
Uploading 2 image(s)...
  ✅ Uploaded 2 file(s)
Creating ticket: My Feature PRD

✅ Created T123456: My Feature PRD
   URL: https://phabricator.tools.flnltd.com/T123456
   Images: 2 embedded

📝 Updated prd.md with ticket_id
```

---

## After Creation

Your Markdown file is updated with `ticket_id` and File IDs:

```markdown
---
title: My Feature PRD
ticket_id: T123456
---

# My Feature PRD

## Mockups

![Flow Diagram](images/flow.png) <!-- F111111 -->
![UI Design](images/design.png) <!-- F222222 -->
```

---

## Error Handling

| Error | Solution |
|-------|----------|
| "No title found" | Add `title:` to frontmatter or H1 heading |
| "Already has ticket_id" | Use `update_ticket.py` instead |
| "Could not find user" | Check username spelling |
| "Image not found" | Check image paths are correct |
| "Mermaid validation failed" | Ensure each Mermaid block has a matching `mermaid-N.png` image reference directly above it, and file exists |
| "Local image path validation failed" | Fix missing local image files before running create |
