#!/usr/bin/env python3
# CLI tool to update a Phabricator ticket.
# Not for creating new tickets — use create_ticket.py for that.

import argparse
import asyncio
import json
import os
import sys

from phabricator import update_ticket, upload_files
from markdown_utils import (
    extract_local_images,
    extract_uploaded_images,
    extract_frontmatter,
    extract_body_without_frontmatter,
    writeback_file_ids,
    collect_broken_local_image_refs,
    transform_related_docs_for_phabricator,
)


def validate_markdown_assets(content: str, base_dir: str) -> bool:
    """
    Run strict asset validation before ticket update.

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


async def update_from_markdown(
    markdown_path: str,
    add_tags: list[str] | None = None,
    remove_tags: list[str] | None = None,
    owner: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    comment: str | None = None,
    output_json: bool = False,
) -> int:
    """
    Update a ticket from a Markdown file.

    The Markdown file must have ticket_id in frontmatter.
    This will:
    1. Upload any new local images
    2. Write back File IDs to the markdown
    3. Update the ticket description with the new content
    """
    if not os.path.exists(markdown_path):
        print(f"Error: File not found: {markdown_path}", file=sys.stderr)
        return 1

    # Read the Markdown file
    with open(markdown_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Get base directory for resolving image paths
    base_dir = os.path.dirname(os.path.abspath(markdown_path))

    # Strict validation checkpoint
    if not validate_markdown_assets(content, base_dir):
        return 1

    # Parse frontmatter
    frontmatter, _ = extract_frontmatter(content)

    # Get ticket_id from frontmatter
    ticket_id = frontmatter.get("ticket_id")
    if not ticket_id:
        print("Error: No ticket_id found in frontmatter", file=sys.stderr)
        print("Use create_ticket.py to create a new ticket first.", file=sys.stderr)
        return 1

    # Extract local images that need to be uploaded
    local_images = extract_local_images(content, base_dir)

    # Upload local images first
    uploaded_file_ids: dict[str, str] = {}
    if local_images:
        print(f"Uploading {len(local_images)} new image(s)...")
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

    # Get the body content (without frontmatter)
    description = extract_body_without_frontmatter(content)

    # Convert image references to Remarkup format for Phabricator
    import re
    for img in uploaded_images:
        description = description.replace(img.full_match, f'{{{img.file_id}}}')

    # Replace newly uploaded images
    for original_path, file_id in uploaded_file_ids.items():
        pattern = rf'!\[[^\]]*\]\({re.escape(original_path)}\)'
        description = re.sub(pattern, f'{{{file_id}}}', description)

    # Transform Related Documents: convert ticket links, remove local-only links
    description = transform_related_docs_for_phabricator(description)

    # Get title from frontmatter if available (for title update)
    title = frontmatter.get("title")

    # Update the ticket
    print(f"Updating {ticket_id}...")
    result = await update_ticket(
        ticket_id=ticket_id,
        title=title,
        description=description,
        status=status,
        priority=priority,
        owner=owner,
        comment=comment,
        add_tags=add_tags,
        remove_tags=remove_tags,
    )

    if not result.get("success"):
        print(f"Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
        return 1

    # Save the updated Markdown file (with file IDs)
    if uploaded_file_ids:
        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {markdown_path} with File IDs")

    if output_json:
        print(json.dumps({
            "ticket_id": ticket_id,
            "success": True,
            "uploaded_images": len(uploaded_file_ids),
            "warnings": result.get("warnings"),
        }))
    else:
        print(f"Updated {ticket_id}")
        if result.get("warnings"):
            for warning in result["warnings"]:
                print(f"  Warning: {warning}")

    return 0


async def update_direct(
    ticket_id: str,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    owner: str | None = None,
    comment: str | None = None,
    add_tags: list[str] | None = None,
    remove_tags: list[str] | None = None,
    output_json: bool = False,
) -> int:
    """Update a ticket with direct parameters."""
    # Normalize ticket ID
    if not ticket_id.startswith("T"):
        ticket_id = f"T{ticket_id}"

    result = await update_ticket(
        ticket_id=ticket_id,
        title=title,
        description=description,
        status=status,
        priority=priority,
        owner=owner,
        comment=comment,
        add_tags=add_tags,
        remove_tags=remove_tags,
    )

    if not result.get("success"):
        print(f"Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
        return 1

    if output_json:
        print(json.dumps({
            "ticket_id": ticket_id,
            "success": True,
            "warnings": result.get("warnings"),
        }))
    else:
        print(f"Updated {ticket_id}")
        if result.get("warnings"):
            for warning in result["warnings"]:
                print(f"  Warning: {warning}")

    return 0


async def main():
    parser = argparse.ArgumentParser(
        description="Update a Phabricator ticket."
    )

    # Input source
    parser.add_argument(
        "ticket_id",
        nargs="?",
        help="The ticket ID (e.g., T123456)"
    )
    parser.add_argument(
        "--file", "-f",
        help="Markdown file to update from (uses ticket_id from frontmatter)"
    )

    # Update parameters
    parser.add_argument(
        "--title", "-t",
        help="New title"
    )
    parser.add_argument(
        "--description", "-d",
        help="New description"
    )
    parser.add_argument(
        "--status", "-s",
        choices=["open", "resolved", "wontfix", "invalid", "spite"],
        help="New status"
    )
    parser.add_argument(
        "--priority",
        choices=["unbreak", "triage", "high", "normal", "low", "wish"],
        help="New priority"
    )
    parser.add_argument(
        "--owner", "-o",
        help="New owner username (use '' to unassign)"
    )
    parser.add_argument(
        "--comment", "-c",
        help="Comment to add"
    )
    parser.add_argument(
        "--add-tags",
        nargs="+",
        help="Tags to add"
    )
    parser.add_argument(
        "--remove-tags",
        nargs="+",
        help="Tags to remove"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    # Validate input
    if not args.ticket_id and not args.file:
        parser.error("Either ticket_id or --file is required")

    if args.file:
        return await update_from_markdown(
            markdown_path=args.file,
            add_tags=args.add_tags,
            remove_tags=args.remove_tags,
            owner=args.owner,
            status=args.status,
            priority=args.priority,
            comment=args.comment,
            output_json=args.json,
        )
    else:
        return await update_direct(
            ticket_id=args.ticket_id,
            title=args.title,
            description=args.description,
            status=args.status,
            priority=args.priority,
            owner=args.owner,
            comment=args.comment,
            add_tags=args.add_tags,
            remove_tags=args.remove_tags,
            output_json=args.json,
        )


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
