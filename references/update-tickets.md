# Update Tickets Reference

## ⚠️ Read First Rule

**Before updating any ticket, ALWAYS read the current state first:**

```bash
# Always do this first
UV_CACHE_DIR=/tmp/uv-cache uv run get_ticket.py T123456

# Then update
UV_CACHE_DIR=/tmp/uv-cache uv run update_ticket.py T123456 --status resolved
```

This prevents:
- Overwriting recent changes by others
- Missing important context in comments
- Conflicting status changes

---

## update_ticket.py

Update an existing Phabricator ticket.

### Synopsis

```bash
# From Markdown file (uses ticket_id from frontmatter)
UV_CACHE_DIR=/tmp/uv-cache uv run update_ticket.py --file PATH [OPTIONS]

# Direct update
UV_CACHE_DIR=/tmp/uv-cache uv run update_ticket.py TICKET_ID [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `TICKET_ID` | The ticket ID (e.g., T123456) - not needed with --file |

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--file` | `-f` | Markdown file to update from |
| `--title` | `-t` | New title |
| `--description` | `-d` | New description |
| `--status` | `-s` | New status: open, resolved, wontfix, invalid, spite |
| `--priority` | | New priority: unbreak, triage, high, normal, low, wish |
| `--owner` | `-o` | New owner username (use '' to unassign) |
| `--comment` | `-c` | Comment to add |
| `--add-tags` | | Tags to add (space-separated) |
| `--remove-tags` | | Tags to remove (space-separated) |
| `--skip-mermaid` | | Skip automatic Mermaid conversion (strict validation still enforced) |
| `--json` | | Output as JSON |

---

## Update from Markdown

When using `--file`, the script:

1. **Mermaid checkpoint** - Convert Mermaid diagrams to PNG (unless `--skip-mermaid`)
2. **Strict Mermaid validation** - Every Mermaid block must have matching PNG reference + local file
3. **Strict local image validation** - Every local Markdown image path must exist on disk
4. **Reads ticket_id** from frontmatter
5. **Uploads new images** (those without File ID comments)
6. **Writes back File IDs** to the Markdown
7. **Transforms Related Documents** for Phabricator:
   - Entries with `(Txxxxxx)` become clickable Phabricator links
   - Entries without ticket_id are removed from uploaded description
   - Historical separator compatibility: both `—` and `-` are accepted
8. **Syncs the description** to Phabricator
9. **Applies any CLI options** (status, comment, tags, etc.)

---

## Examples

```bash
# Sync description from Markdown (uploads new images)
UV_CACHE_DIR=/tmp/uv-cache uv run update_ticket.py --file prd.md

# Mark as resolved with comment
UV_CACHE_DIR=/tmp/uv-cache uv run update_ticket.py T123456 --status resolved --comment "Fixed in D789012"

# Change owner
UV_CACHE_DIR=/tmp/uv-cache uv run update_ticket.py T123456 --owner smanton

# Unassign ticket
UV_CACHE_DIR=/tmp/uv-cache uv run update_ticket.py T123456 --owner ''

# Update tags (see SKILL.md for available tag slugs)
UV_CACHE_DIR=/tmp/uv-cache uv run update_ticket.py T123456 --add-tags user_growth_loadshift --remove-tags wip

# Sync Markdown and add comment
UV_CACHE_DIR=/tmp/uv-cache uv run update_ticket.py --file prd.md --comment "Updated requirements"

# Skip auto-conversion but still enforce Mermaid/asset validation
UV_CACHE_DIR=/tmp/uv-cache uv run update_ticket.py --file prd.md --skip-mermaid

# JSON output
UV_CACHE_DIR=/tmp/uv-cache uv run update_ticket.py T123456 --status open --json
```

---

## Incremental Image Upload

The skill tracks which images have been uploaded using File ID comments:

```markdown
<!-- Already uploaded - will NOT be re-uploaded -->
![Old Image](images/old.png) <!-- F111111 -->

<!-- New image - WILL be uploaded -->
![New Image](images/new.png)
```

After running `update_ticket.py --file`:

```markdown
![Old Image](images/old.png) <!-- F111111 -->
![New Image](images/new.png) <!-- F222222 -->
```

---

## Output

```
Uploading 1 new image(s)...
  ✅ Uploaded 1 file(s)
Updating T123456...
✅ Updated T123456
📝 Updated prd.md with File IDs
```

---

## Status Values

| Status | Description |
|--------|-------------|
| `open` | Ticket is open/active |
| `resolved` | Work is complete |
| `wontfix` | Won't be fixed (by design) |
| `invalid` | Not a valid issue |
| `spite` | Closed out of spite (rarely used) |

---

## Error Handling

| Error | Solution |
|-------|----------|
| "No ticket_id found in frontmatter" | Create ticket first with `create_ticket.py` |
| "Could not find user" | Check username spelling |
| "Tags not found" | Check tag/project names |
| "No changes specified" | Provide at least one change option |
| "Mermaid validation failed" | Ensure each Mermaid block has matching `mermaid-N.png` reference and file |
| "Local image path validation failed" | Fix missing local image files before running update |

---

## Workflow: Edit and Sync

1. **Read the ticket first** to check current state:
   ```bash
   UV_CACHE_DIR=/tmp/uv-cache uv run get_ticket.py T123456
   ```

2. **Edit your Markdown file** - add content, screenshots, etc.

3. **Sync to Phabricator**:
   ```bash
   UV_CACHE_DIR=/tmp/uv-cache uv run update_ticket.py --file prd.md
   ```

4. **Check the ticket** - all changes are reflected in Phabricator

5. **Repeat** as needed - only new images are uploaded each time
