#!/usr/bin/env python3
# CLI tool to create a Phabricator ticket from a Markdown file or direct input.
# Not for updating existing tickets — use update_ticket.py for that.

import argparse
import asyncio
import json
import os
import sys

from phabricator import create_ticket, upload_files
from markdown_utils import (
    extract_local_images,
    extract_uploaded_images,
    extract_frontmatter,
    extract_body_without_frontmatter,
    update_frontmatter_ticket_id,
    update_frontmatter_value,
    writeback_file_ids,
    collect_broken_local_image_refs,
    transform_related_docs_for_phabricator,
)


def validate_markdown_assets(content: str, base_dir: str) -> bool:
    """
    Run strict asset validation before ticket creation.

    Rules:
    - Every local Markdown image path must exist on disk.
    """
    missing_local_images = collect_broken_local_image_refs(content, base_dir)
    if missing_local_images:
        print("Error: Local image path validation failed.", file=sys.stderr)
        print("  - Missing local image files:", file=sys.stderr)
        for path in missing_local_images:
            resolved = path if os.path.isabs(path) else os.path.join(base_dir, path)
            print(f"    * {path} (resolved: {resolved})", file=sys.stderr)
        return False

    return True


async def create_from_markdown(
    markdown_path: str,
    tags: list[str] | None = None,
    owner: str | None = None,
    parent: str | None = None,
    priority: str | None = None,
    output_json: bool = False,
) -> int:
    """
    Create a ticket from a Markdown file.

    The Markdown file can have:
    - YAML frontmatter with title, priority, owner, parent, tags
    - Local images that will be uploaded automatically
    - Already-uploaded images (with File ID comments) that will be embedded

    After creation, the ticket_id will be written back to the frontmatter.
    """
    if not os.path.exists(markdown_path):
        print(f"Error: File not found: {markdown_path}", file=sys.stderr)
        return 1

    # Read the Markdown file
    with open(markdown_path, "r", encoding="utf-8") as f:
        content = f.read()
    base_dir = os.path.dirname(os.path.abspath(markdown_path))

    # Strict validation checkpoint
    if not validate_markdown_assets(content, base_dir):
        return 1

    # Parse frontmatter for metadata
    frontmatter, _ = extract_frontmatter(content)

    # Check if already has a ticket_id
    if frontmatter.get("ticket_id"):
        print(f"Warning: This file already has ticket_id: {frontmatter['ticket_id']}", file=sys.stderr)
        print("Use update_ticket.py to update an existing ticket.", file=sys.stderr)
        return 1

    # Get title from frontmatter or first heading
    title = frontmatter.get("title")
    if not title:
        # Try to extract from first H1 heading
        import re
        h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if h1_match:
            title = h1_match.group(1).strip()
        else:
            print("Error: No title found in frontmatter or as H1 heading", file=sys.stderr)
            return 1

    # Get other metadata (CLI args override frontmatter)
    final_priority = priority or frontmatter.get("priority")
    final_owner = owner or frontmatter.get("owner")
    final_parent = parent or frontmatter.get("parent")

    # Handle tags - can be a list (YAML array) or comma-separated string
    fm_tags = frontmatter.get("tags")
    if tags:
        # CLI args override frontmatter
        final_tags = tags
    elif isinstance(fm_tags, list):
        # YAML list format: tags: \n  - tag1 \n  - tag2
        final_tags = fm_tags
    elif isinstance(fm_tags, str) and fm_tags:
        # Comma-separated string format: tags: tag1, tag2
        final_tags = [t.strip() for t in fm_tags.split(",") if t.strip()]
    else:
        final_tags = None

    if final_tags:
        final_tags = [t.strip() if isinstance(t, str) else t for t in final_tags if t]

    # Extract local images that need to be uploaded
    local_images = extract_local_images(content, base_dir)

    # Upload local images first
    uploaded_file_ids: dict[str, str] = {}
    if local_images:
        print(f"Uploading {len(local_images)} image(s)...")
        file_paths = [img.path for img in local_images]
        successful_uploads, errors = await upload_files(file_paths)

        if errors:
            for error in errors:
                print(f"  Warning: {error}", file=sys.stderr)

        if successful_uploads:
            # Map original paths to file IDs
            import re
            for img in local_images:
                if img.path in successful_uploads:
                    match = re.search(r'!\[[^\]]*\]\(([^)]+)\)', img.full_match)
                    if match:
                        original_path = match.group(1)
                        uploaded_file_ids[original_path] = successful_uploads[img.path]

            # Write back file IDs to the markdown
            content = writeback_file_ids(content, uploaded_file_ids)
            print(f"  Uploaded {len(successful_uploads)} file(s)")

    # Extract already-uploaded images
    uploaded_images = extract_uploaded_images(content)
    all_file_ids = [img.file_id for img in uploaded_images]
    all_file_ids.extend(uploaded_file_ids.values())

    # Get the body content (without frontmatter)
    description = extract_body_without_frontmatter(content)

    # Convert image references to Remarkup format for Phabricator
    # Replace ![alt](path) <!-- FXXXXXX --> with {FXXXXXX}
    import re
    for img in uploaded_images:
        description = description.replace(img.full_match, f'{{{img.file_id}}}')

    # Replace newly uploaded images
    for original_path, file_id in uploaded_file_ids.items():
        pattern = rf'!\[[^\]]*\]\({re.escape(original_path)}\)'
        description = re.sub(pattern, f'{{{file_id}}}', description)

    # Transform Related Documents: convert ticket links, remove local-only links
    description = transform_related_docs_for_phabricator(description)

    # Create the ticket
    print(f"Creating ticket: {title}")
    result = await create_ticket(
        title=title,
        description=description,
        priority=final_priority,
        owner=final_owner,
        parent_ticket=final_parent,
        tags=final_tags,
    )

    if result.get("error"):
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1

    ticket_id = result["ticket_id"]
    ticket_url = result["url"]

    # Write back ticket_id to frontmatter
    content = update_frontmatter_ticket_id(content, ticket_id)

    # Save the updated Markdown file
    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write(content)

    if output_json:
        print(json.dumps({
            "ticket_id": ticket_id,
            "url": ticket_url,
            "title": title,
            "uploaded_images": len(all_file_ids),
        }))
    else:
        print(f"\nCreated {ticket_id}: {title}")
        print(f"   URL: {ticket_url}")
        if all_file_ids:
            print(f"   Images: {len(all_file_ids)} embedded")
        print(f"\n   Updated {markdown_path} with ticket_id")

    return 0


async def create_direct(
    title: str,
    description: str | None = None,
    tags: list[str] | None = None,
    owner: str | None = None,
    parent: str | None = None,
    priority: str | None = None,
    output_json: bool = False,
) -> int:
    """Create a ticket with direct title/description input."""
    result = await create_ticket(
        title=title,
        description=description,
        priority=priority,
        owner=owner,
        parent_ticket=parent,
        tags=tags,
    )

    if result.get("error"):
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1

    ticket_id = result["ticket_id"]
    ticket_url = result["url"]

    if output_json:
        print(json.dumps({
            "ticket_id": ticket_id,
            "url": ticket_url,
            "title": title,
        }))
    else:
        print(f"Created {ticket_id}: {title}")
        print(f"   URL: {ticket_url}")

    return 0


def init_document(markdown_path: str, title_override: str | None = None) -> int:
    """
    Initialize Markdown document frontmatter with title field.

    This is a pre-flight step before ticket creation. It ensures the document
    has proper frontmatter with a title, without creating a ticket.

    Args:
        markdown_path: Path to the Markdown file.
        title_override: Optional title to use instead of auto-detection.

    Returns:
        0 on success, 1 on error.
    """
    import re

    # Check if file exists
    if not os.path.exists(markdown_path):
        print(f"Error: File not found: {markdown_path}", file=sys.stderr)
        return 1

    # Read the file
    with open(markdown_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse existing frontmatter
    frontmatter, _ = extract_frontmatter(content)

    # Check if already has a ticket_id - don't allow re-init
    if frontmatter.get("ticket_id"):
        print(f"Error: This file already has ticket_id: {frontmatter['ticket_id']}", file=sys.stderr)
        print("Cannot re-initialize a document that already has a ticket.", file=sys.stderr)
        return 1

    # Determine title: CLI override > frontmatter > H1 heading
    title = title_override
    if not title:
        title = frontmatter.get("title")
    if not title:
        # Try to extract from first H1 heading
        h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if h1_match:
            title = h1_match.group(1).strip()

    if not title:
        print("Error: Could not determine title.", file=sys.stderr)
        print("Please provide a title via --title, frontmatter, or H1 heading.", file=sys.stderr)
        return 1

    # Update frontmatter with title
    content = update_frontmatter_value(content, "title", title)

    # Save the file
    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Initialized document: {markdown_path}")
    print(f"   Title: {title}")
    print("\n   Frontmatter updated. Ready for ticket creation.")

    return 0


async def main():
    parser = argparse.ArgumentParser(
        description="Create a Phabricator ticket from a Markdown file or direct input."
    )

    # Input source
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--file", "-f",
        help="Markdown file to create ticket from"
    )
    group.add_argument(
        "--title", "-t",
        help="Ticket title (for direct creation)"
    )

    # Init mode (works with --file)
    parser.add_argument(
        "--init",
        action="store_true",
        help="Initialize frontmatter only, without creating a ticket (use with --file)"
    )
    parser.add_argument(
        "--title-override",
        help="Override title for --init mode (optional)"
    )

    # Optional parameters
    parser.add_argument(
        "--description", "-d",
        help="Ticket description (only with --title)"
    )
    parser.add_argument(
        "--tags",
        nargs="+",
        help="Project/tag names to add"
    )
    parser.add_argument(
        "--owner", "-o",
        help="Username to assign the ticket to"
    )
    parser.add_argument(
        "--parent", "-p",
        help="Parent ticket ID (e.g., T123456)"
    )
    parser.add_argument(
        "--priority",
        choices=["unbreak", "triage", "high", "normal", "low", "wish"],
        help="Ticket priority"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    # Handle --init mode
    if args.init:
        if not args.file:
            print("Error: --init requires --file", file=sys.stderr)
            return 1
        return init_document(
            markdown_path=args.file,
            title_override=args.title_override,
        )

    # Handle normal ticket creation
    if args.file:
        return await create_from_markdown(
            markdown_path=args.file,
            tags=args.tags,
            owner=args.owner,
            parent=args.parent,
            priority=args.priority,
            output_json=args.json,
        )
    else:
        return await create_direct(
            title=args.title,
            description=args.description,
            tags=args.tags,
            owner=args.owner,
            parent=args.parent,
            priority=args.priority,
            output_json=args.json,
        )


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
