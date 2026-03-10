#!/usr/bin/env python3
# .claude/skills/tickets/scripts/upload_file.py
# CLI tool to upload files to Phabricator with File ID writeback to Markdown.
# Usage: uv run upload_file.py --file image.png
# Usage: uv run upload_file.py --markdown /path/to/doc.md

import argparse
import asyncio
import json
import os
import sys

from phabricator import upload_file, upload_files
from markdown_utils import (
    extract_local_images,
    writeback_file_ids,
)


async def upload_single_file(file_path: str, output_json: bool = False) -> int:
    """Upload a single file and print the result."""
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        return 1

    print(f"Uploading {file_path}...")
    _, file_id = await upload_file(file_path)

    if not file_id:
        print(f"Error: Failed to upload {file_path}", file=sys.stderr)
        return 1

    if output_json:
        print(json.dumps({"file_path": file_path, "file_id": file_id}))
    else:
        print(f"✅ Uploaded: {file_path} → {file_id}")
        print(f"   Remarkup: {{{file_id}}}")

    return 0


async def upload_from_markdown(markdown_path: str, dry_run: bool = False, output_json: bool = False) -> int:
    """
    Extract images from Markdown, upload them, and write back File IDs.

    This function:
    1. Reads the Markdown file
    2. Finds all local images that haven't been uploaded yet
    3. Uploads each image to Phabricator
    4. Writes back the File ID as an HTML comment: ![alt](path) <!-- FXXXXXX -->
    5. Saves the updated Markdown file
    """
    if not os.path.exists(markdown_path):
        print(f"Error: Markdown file not found: {markdown_path}", file=sys.stderr)
        return 1

    # Read the Markdown file
    with open(markdown_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Get the directory of the Markdown file for resolving relative paths
    base_dir = os.path.dirname(os.path.abspath(markdown_path))

    # Extract local images that haven't been uploaded
    local_images = extract_local_images(content, base_dir)

    if not local_images:
        print("No local images found to upload.")
        return 0

    print(f"Found {len(local_images)} image(s) to upload:")
    for img in local_images:
        print(f"  - {img.path}")

    if dry_run:
        print("\n[Dry run] No files uploaded.")
        return 0

    # Upload all images
    file_paths = [img.path for img in local_images]
    successful_uploads, errors = await upload_files(file_paths)

    # Report results
    results = []
    if successful_uploads:
        print(f"\n✅ Successfully uploaded {len(successful_uploads)} file(s):")
        for path, file_id in successful_uploads.items():
            print(f"  - {os.path.basename(path)} → {file_id}")
            results.append({"file_path": path, "file_id": file_id})

    if errors:
        print(f"\n❌ Failed to upload {len(errors)} file(s):")
        for error in errors:
            print(f"  - {error}")

    # Write back File IDs to the Markdown file
    if successful_uploads:
        # Create a mapping from the original path in markdown to file_id
        # We need to match using the path as it appears in the markdown
        path_to_file_id = {}
        for img in local_images:
            if img.path in successful_uploads:
                # Use the path from the original markdown match
                # Extract just the path portion from the full_match
                import re
                match = re.search(r'!\[[^\]]*\]\(([^)]+)\)', img.full_match)
                if match:
                    original_path = match.group(1)
                    path_to_file_id[original_path] = successful_uploads[img.path]

        if path_to_file_id:
            updated_content = writeback_file_ids(content, path_to_file_id)

            # Save the updated Markdown
            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(updated_content)

            print(f"\n📝 Updated {markdown_path} with File IDs")

    if output_json:
        print(json.dumps(results, indent=2))

    return 0 if not errors else 1


async def main():
    parser = argparse.ArgumentParser(
        description="Upload files to Phabricator. Can upload individual files or process a Markdown file."
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--file", "-f",
        help="Single file to upload"
    )
    group.add_argument(
        "--markdown", "-m",
        help="Markdown file to process (extracts and uploads images, writes back File IDs)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be uploaded without actually uploading"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    if args.file:
        return await upload_single_file(args.file, args.json)
    else:
        return await upload_from_markdown(args.markdown, args.dry_run, args.json)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
