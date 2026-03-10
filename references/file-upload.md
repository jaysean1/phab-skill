# File Upload Reference

## upload_file.py

Upload files to Phabricator with automatic File ID tracking.

### Synopsis

```bash
# Upload single file
UV_CACHE_DIR=/tmp/uv-cache uv run upload_file.py --file PATH

# Process Markdown file (upload all images, write back File IDs)
UV_CACHE_DIR=/tmp/uv-cache uv run upload_file.py --markdown PATH [--dry-run]
```

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--file` | `-f` | Single file to upload |
| `--markdown` | `-m` | Markdown file to process |
| `--dry-run` | | Show what would be uploaded without uploading |
| `--json` | | Output as JSON |

### Single File Upload

Upload a single file and get its File ID:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run upload_file.py --file screenshot.png
```

Output:
```
Uploading screenshot.png...
✅ Uploaded: screenshot.png → F123456
   Remarkup: {F123456}
```

Use the Remarkup syntax `{F123456}` to embed in Phabricator tickets or diffs.

### Markdown Processing

Process a Markdown file to upload all local images:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run upload_file.py --markdown prd.md
```

This will:
1. Find all local images in the Markdown
2. Skip already-uploaded images (those with File ID comments)
3. Upload new images to Phabricator
4. Write back File IDs as HTML comments
5. Save the updated Markdown

### File ID Writeback Format

Before upload:
```markdown
![Screenshot](images/screenshot.png)
![Diagram](images/diagram.png)
```

After upload:
```markdown
![Screenshot](images/screenshot.png) <!-- F123456 -->
![Diagram](images/diagram.png) <!-- F123457 -->
```

The HTML comment is invisible when rendered but tracks the upload status.

### Image Detection Patterns

**Detected (will be uploaded):**
```markdown
![Alt text](path/to/image.png)
![](image.jpg)
![Screenshot](../assets/shot.gif)
```

**Skipped (already uploaded):**
```markdown
![Image](path.png) <!-- F123456 -->
```

**Skipped (external URLs):**
```markdown
![Logo](https://example.com/logo.png)
![Image](http://cdn.example.com/img.jpg)
```

### Examples

```bash
# Upload a screenshot
UV_CACHE_DIR=/tmp/uv-cache uv run upload_file.py --file ~/Desktop/screenshot.png

# Process a PRD document
UV_CACHE_DIR=/tmp/uv-cache uv run upload_file.py --markdown ~/docs/feature-prd.md

# Preview what would be uploaded
UV_CACHE_DIR=/tmp/uv-cache uv run upload_file.py --markdown ~/docs/feature-prd.md --dry-run

# Get JSON output for scripting
UV_CACHE_DIR=/tmp/uv-cache uv run upload_file.py --file image.png --json
```

### Dry Run Output

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run upload_file.py --markdown prd.md --dry-run
```

```
Found 3 image(s) to upload:
  - /Users/jqian/docs/images/flow.png
  - /Users/jqian/docs/images/mockup.png
  - /Users/jqian/docs/images/diagram.png

[Dry run] No files uploaded.
```

### Supported File Types

Phabricator accepts most common file types:
- Images: PNG, JPG, GIF, SVG, WebP
- Documents: PDF, DOC, DOCX
- Others: ZIP, TXT, etc.

### Error Handling

| Error | Solution |
|-------|----------|
| "File not found" | Check file path exists |
| "Failed to upload" | Check network/API token |
| "No local images found" | Images may already be uploaded |

### Integration with create_ticket.py / update_ticket.py

You don't usually need to run `upload_file.py` separately. Both `create_ticket.py` and `update_ticket.py` automatically:

1. Detect local images
2. Upload them
3. Write back File IDs
4. Convert to Remarkup for Phabricator

Use `upload_file.py` directly when you want to:
- Upload files without creating/updating a ticket
- Preview uploads with `--dry-run`
- Get File IDs for manual use

### Remarkup Reference

Once uploaded, embed files in Phabricator using:

| Syntax | Description |
|--------|-------------|
| `{F123456}` | Embed image/file inline |
| `{F123456, size=full}` | Full-size image |
| `{F123456, size=thumb}` | Thumbnail |
| `{F123456, layout=left}` | Float left |
