# Markdown processing utilities for the tickets skill.
# Not for ticket CRUD operations — only text parsing and transformation.

import os
import re
from dataclasses import dataclass
from typing import Any

import yaml


@dataclass
class LocalImage:
    """Represents a local image found in Markdown."""
    alt_text: str
    path: str
    full_match: str
    start_pos: int
    end_pos: int


@dataclass
class UploadedImage:
    """Represents an already-uploaded image with File ID."""
    alt_text: str
    path: str
    file_id: str
    full_match: str
    start_pos: int
    end_pos: int


def extract_local_images(content: str, base_dir: str | None = None) -> list[LocalImage]:
    """
    Extract local images from Markdown content that haven't been uploaded yet.

    Matches: ![alt](path) where path is NOT a URL and NOT followed by <!-- FXXXXXX -->

    Args:
        content: Markdown content.
        base_dir: Base directory to resolve relative paths.

    Returns:
        List of LocalImage objects.
    """
    # Pattern: ![alt](path) NOT followed by <!-- FXXXXXX -->
    # Negative lookahead ensures we don't match already-uploaded images
    pattern = r'!\[([^\]]*)\]\(((?!https?://)[^)]+)\)(?!\s*<!--\s*F\d+\s*-->)'

    images = []
    for match in re.finditer(pattern, content):
        alt_text = match.group(1)
        path = match.group(2)

        # Resolve path relative to base_dir if provided
        if base_dir and not os.path.isabs(path):
            full_path = os.path.join(base_dir, path)
        else:
            full_path = path

        # Only include if file exists
        if os.path.exists(full_path):
            images.append(LocalImage(
                alt_text=alt_text,
                path=full_path,
                full_match=match.group(0),
                start_pos=match.start(),
                end_pos=match.end(),
            ))

    return images


def extract_uploaded_images(content: str) -> list[UploadedImage]:
    """
    Extract images that have already been uploaded (have File ID comment).

    Matches: ![alt](path) <!-- FXXXXXX -->

    Args:
        content: Markdown content.

    Returns:
        List of UploadedImage objects.
    """
    pattern = r'!\[([^\]]*)\]\(([^)]+)\)\s*<!--\s*(F\d+)\s*-->'

    images = []
    for match in re.finditer(pattern, content):
        images.append(UploadedImage(
            alt_text=match.group(1),
            path=match.group(2),
            file_id=match.group(3),
            full_match=match.group(0),
            start_pos=match.start(),
            end_pos=match.end(),
        ))

    return images


def writeback_file_id(content: str, image_path: str, file_id: str) -> str:
    """
    Write back a File ID as an HTML comment after an image reference.

    Before: ![Mockup](images/mockup.png)
    After:  ![Mockup](images/mockup.png) <!-- F123456 -->

    Args:
        content: Markdown content.
        image_path: The path in the image reference (may be relative).
        file_id: The Phabricator File ID (e.g., "F123456").

    Returns:
        Updated Markdown content with File ID comment.
    """
    # Escape special regex characters in the path
    escaped_path = re.escape(image_path)

    # Match the image reference (may or may not have alt text)
    pattern = rf'(!\[[^\]]*\]\({escaped_path}\))(?!\s*<!--)'

    # Replace with original match + file ID comment
    replacement = rf'\1 <!-- {file_id} -->'

    return re.sub(pattern, replacement, content)


def writeback_file_ids(content: str, path_to_file_id: dict[str, str]) -> str:
    """
    Write back multiple File IDs to Markdown content.

    Args:
        content: Markdown content.
        path_to_file_id: Dict mapping image paths to File IDs.

    Returns:
        Updated Markdown content with all File ID comments.
    """
    for path, file_id in path_to_file_id.items():
        # Try with the full path first
        content = writeback_file_id(content, path, file_id)

        # Also try with just the filename (for relative path matching)
        basename = os.path.basename(path)
        if basename != path:
            content = writeback_file_id(content, basename, file_id)

    return content


def extract_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """
    Extract YAML frontmatter from Markdown content.

    Uses the yaml library for proper parsing, supporting:
    - Simple key: value pairs
    - Lists (both inline and multi-line)
    - Nested structures

    Args:
        content: Markdown content potentially starting with ---frontmatter---.

    Returns:
        Tuple of (frontmatter_dict, body_without_frontmatter).
    """
    frontmatter: dict[str, Any] = {}
    body = content

    # Check for frontmatter (starts with ---)
    if content.startswith('---'):
        # Find the closing ---
        end_match = re.search(r'\n---\s*\n', content[3:])
        if end_match:
            # Extract frontmatter section
            fm_end = end_match.start() + 3
            fm_content = content[3:fm_end]
            body = content[fm_end + end_match.end() - end_match.start():]

            # Parse YAML frontmatter properly
            try:
                parsed = yaml.safe_load(fm_content)
                if isinstance(parsed, dict):
                    frontmatter = parsed
            except yaml.YAMLError:
                # Fallback to simple key: value parsing if YAML fails
                for line in fm_content.strip().split('\n'):
                    if ':' in line and not line.strip().startswith('-'):
                        key, value = line.split(':', 1)
                        frontmatter[key.strip()] = value.strip()

    return frontmatter, body


def extract_body_without_frontmatter(content: str) -> str:
    """
    Extract just the body content, removing YAML frontmatter.

    Args:
        content: Markdown content.

    Returns:
        Body content without frontmatter.
    """
    _, body = extract_frontmatter(content)
    return body.strip()


def update_frontmatter_value(content: str, key: str, value: str) -> str:
    """
    Update or add a value in the frontmatter.

    Args:
        content: Markdown content.
        key: Frontmatter key to update.
        value: New value.

    Returns:
        Updated content with modified frontmatter.
    """
    if content.startswith('---'):
        # Find the closing ---
        end_match = re.search(r'\n---\s*\n', content[3:])
        if end_match:
            fm_end = end_match.start() + 3
            fm_content = content[3:fm_end]
            body = content[fm_end + end_match.end() - end_match.start():]

            # Check if key exists
            key_pattern = rf'^{re.escape(key)}:.*$'
            if re.search(key_pattern, fm_content, re.MULTILINE):
                # Update existing key
                fm_content = re.sub(key_pattern, f'{key}: {value}', fm_content, flags=re.MULTILINE)
            else:
                # Add new key
                fm_content = fm_content.rstrip() + f'\n{key}: {value}'

            return f'---{fm_content}\n---\n{body}'

    # No frontmatter exists, create one
    return f'---\n{key}: {value}\n---\n\n{content}'


def update_frontmatter_ticket_id(content: str, ticket_id: str) -> str:
    """
    Update or add the ticket_id in frontmatter.

    Args:
        content: Markdown content.
        ticket_id: The Phabricator ticket ID (e.g., "T123456").

    Returns:
        Updated content with ticket_id in frontmatter.
    """
    return update_frontmatter_value(content, 'ticket_id', ticket_id)


def get_frontmatter_ticket_id(content: str) -> str | None:
    """
    Get the ticket_id from frontmatter if it exists.

    Args:
        content: Markdown content.

    Returns:
        Ticket ID or None if not found.
    """
    frontmatter, _ = extract_frontmatter(content)
    return frontmatter.get('ticket_id')


def convert_images_to_remarkup(content: str, uploaded_images: list[UploadedImage]) -> str:
    """
    Convert Markdown image references to Phabricator Remarkup format.

    Before: ![alt](path) <!-- F123456 -->
    After: {F123456}

    This is used when creating/updating tickets to embed uploaded images.

    Args:
        content: Markdown content with uploaded images.
        uploaded_images: List of UploadedImage objects.

    Returns:
        Content with image references converted to {FXXXXXX} format.
    """
    # Sort by position in reverse order to avoid offset issues
    sorted_images = sorted(uploaded_images, key=lambda x: x.start_pos, reverse=True)

    for img in sorted_images:
        content = content[:img.start_pos] + f'{{{img.file_id}}}' + content[img.end_pos:]

    return content


def prepare_description_for_phabricator(
    content: str,
    base_dir: str | None = None,
    uploaded_file_ids: dict[str, str] | None = None,
) -> str:
    """
    Prepare Markdown content for Phabricator ticket description.

    1. Removes frontmatter
    2. Converts uploaded images (with File ID comments) to Remarkup format
    3. Optionally converts newly uploaded images using provided file_ids mapping

    Args:
        content: Markdown content.
        base_dir: Base directory for resolving image paths.
        uploaded_file_ids: Dict mapping image paths to newly uploaded File IDs.

    Returns:
        Content ready for Phabricator description.
    """
    # Remove frontmatter
    body = extract_body_without_frontmatter(content)

    # Get already-uploaded images
    uploaded_images = extract_uploaded_images(body)

    # Convert existing uploaded images to Remarkup
    if uploaded_images:
        body = convert_images_to_remarkup(body, uploaded_images)

    # Convert newly uploaded images if provided
    if uploaded_file_ids:
        for path, file_id in uploaded_file_ids.items():
            # Try to match the path in the content
            basename = os.path.basename(path)
            # Match ![alt](path) or ![alt](basename)
            pattern = rf'!\[[^\]]*\]\((?:{re.escape(path)}|{re.escape(basename)})\)'
            body = re.sub(pattern, f'{{{file_id}}}', body)

    return body


# =============================================================================
# Related Documents Cleanup for Phabricator
# =============================================================================


def transform_related_docs_for_phabricator(content: str) -> str:
    """
    Transform Related Documents section for Phabricator upload.

    - Entries with a ticket_id (TXXXXXX): convert local file link to Phabricator link
    - Entries without a ticket_id: remove entirely (local-only dead links)
    - If the section becomes empty after filtering, remove it entirely

    Args:
        content: Markdown content (body without frontmatter).

    Returns:
        Transformed content ready for Phabricator.
    """
    from phabricator import PHABRICATOR_BASE_URL

    # Find the Related Documents section (case-insensitive)
    section_pattern = re.compile(
        r'^(## [Rr]elated [Dd]ocuments)[ \t]*\n',
        re.MULTILINE,
    )
    match = section_pattern.search(content)
    if not match:
        return content

    section_start = match.start()
    section_header_end = match.end()

    # Find where the section ends (next ## heading or end of content)
    next_heading = re.search(r'^## ', content[section_header_end:], re.MULTILINE)
    if next_heading:
        section_end = section_header_end + next_heading.start()
    else:
        section_end = len(content)

    # Extract the lines in the section body
    section_body = content[section_header_end:section_end]
    lines = section_body.split('\n')

    # Patterns for entries WITH ticket_id — keep and convert to Phab link.
    # Historical docs may use "-" instead of "—", so we accept both.
    ticket_entry_patterns = [
        # Format A: - **Name** (T123456): [file](path) — desc
        #           - **Name** (T123456): [file](path) - desc
        re.compile(
            r'^\s*-\s+\*\*(?P<name>.+?)\*\*\s*'
            r'\((?P<ticket>T\d+)\)\s*:\s*'
            r'\[[^\]]+\]\([^)]+\)\s*'
            r'(?:[—-]\s*(?P<desc>.+))?$'
        ),
        # Format B: - **Name** (T123456) — [file](path) — desc
        #           - **Name** (T123456) - [file](path) - desc
        re.compile(
            r'^\s*-\s+\*\*(?P<name>.+?)\*\*\s*'
            r'\((?P<ticket>T\d+)\)\s*[—-]\s*'
            r'\[[^\]]+\]\([^)]+\)\s*'
            r'(?:[—-]\s*(?P<desc>.+))?$'
        ),
    ]

    # Pattern to detect any list entry in Related Documents section.
    # We remove list items without a ticket_id because local links are not valid on Phabricator.
    list_entry = re.compile(r'^\s*-\s+')

    transformed_lines = []
    for line in lines:
        # Check ticket_id patterns first.
        match_with_ticket = None
        for pattern in ticket_entry_patterns:
            match_with_ticket = pattern.match(line)
            if match_with_ticket:
                break

        if match_with_ticket:
            name = match_with_ticket.group("name").strip()
            ticket_id = match_with_ticket.group("ticket")
            desc = (match_with_ticket.group("desc") or "").strip()
            url = f"{PHABRICATOR_BASE_URL}/{ticket_id}"
            if desc:
                transformed_lines.append(f"- **{name}**: [{ticket_id}]({url}) — {desc}")
            else:
                transformed_lines.append(f"- **{name}**: [{ticket_id}]({url})")
            continue

        # Any other list entry (no ticket_id) → remove
        if list_entry.match(line):
            continue

        # Keep non-list lines (blank lines, etc.)
        transformed_lines.append(line)

    # Normalize leading/trailing blank lines so we can enforce stable markdown spacing.
    while transformed_lines and transformed_lines[0].strip() == "":
        transformed_lines.pop(0)
    while transformed_lines and transformed_lines[-1].strip() == "":
        transformed_lines.pop()

    # Check if any actual entries remain
    has_entries = any(list_entry.match(l) for l in transformed_lines)

    if has_entries:
        # Keep exactly one blank line after H2 heading for Phabricator rendering.
        new_section = match.group(1) + '\n\n' + '\n'.join(transformed_lines).rstrip()
        suffix = content[section_end:]
        if suffix:
            return content[:section_start] + new_section + '\n\n' + suffix.lstrip('\n')
        return content[:section_start] + new_section + '\n'
    else:
        # Remove the entire section (including trailing whitespace)
        remaining = content[section_end:].lstrip('\n')
        before = content[:section_start].rstrip('\n')
        if before:
            return before + '\n\n' + remaining
        return remaining


# =============================================================================
# Local Image Validation
# =============================================================================


def _normalize_markdown_image_path(raw_path: str) -> str:
    """
    Normalize a Markdown image path by stripping wrappers and optional title.

    Examples:
    - images/a.png -> images/a.png
    - <images/a.png> -> images/a.png
    - images/a.png "Title" -> images/a.png
    """
    path = raw_path.strip()

    # Handle <path> form
    if path.startswith("<") and path.endswith(">"):
        path = path[1:-1].strip()

    # Handle optional title: (path "title")
    title_match = re.match(r'^(.*?)\s+"[^"]*"\s*$', path)
    if title_match:
        path = title_match.group(1).strip()

    return path


def _is_local_image_path(path: str) -> bool:
    """
    Return True if the image path should resolve to a local file.
    """
    lower = path.lower()
    if not path:
        return False
    if lower.startswith(("http://", "https://", "data:", "file://")):
        return False
    if path.startswith("#"):
        return False
    return True


def collect_broken_local_image_refs(content: str, base_dir: str) -> list[str]:
    """
    Collect Markdown image paths that point to missing local files.

    Args:
        content: Markdown content.
        base_dir: Base directory to resolve relative paths.

    Returns:
        Sorted unique list of missing local image paths exactly as written in Markdown.
    """
    pattern = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')
    missing: set[str] = set()

    for match in pattern.finditer(content):
        raw_path = match.group(1)
        path = _normalize_markdown_image_path(raw_path)

        if not _is_local_image_path(path):
            continue

        full_path = path if os.path.isabs(path) else os.path.join(base_dir, path)
        if not os.path.exists(full_path):
            missing.add(path)

    return sorted(missing)
