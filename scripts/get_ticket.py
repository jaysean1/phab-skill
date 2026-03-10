#!/usr/bin/env python3
# .claude/skills/tickets/scripts/get_ticket.py
# CLI tool to get detailed information about a Phabricator ticket.
# Usage: uv run get_ticket.py T123456

import argparse
import asyncio
import json
import sys

from phabricator import get_ticket


def format_ticket_detail(ticket: dict) -> str:
    """Format ticket details for display."""
    status_emoji = {
        "Open": "🟢", "Resolved": "✅", "Closed": "🔒",
        "In Progress": "🔨", "Stalled": "⏸️", "Invalid": "❌",
    }.get(ticket["status"], "📋")

    # Format tags for display
    tags_display = ", ".join(ticket.get("tags", [])) if ticket.get("tags") else "(No tags)"

    lines = [
        f"## {ticket['id']}: {ticket['title']}",
        "",
        f"**Status:** {status_emoji} {ticket['status']} | **Priority:** {ticket['priority']}",
        f"**Owner:** {ticket['owner']} | **Author:** {ticket['author']}",
        f"**Created:** {ticket['created']} | **Modified:** {ticket['modified']}",
        f"**Tags:** {tags_display}",
        f"**URL:** {ticket['url']}",
        "",
        "### Description",
        ticket['description'] or "(No description)",
    ]

    # Add comments/activity
    if ticket.get("comments"):
        lines.append("")
        lines.append("### Recent Activity")
        for comment in ticket["comments"]:
            if comment["type"] == "comment":
                lines.append(f"- **[{comment['date']}] {comment['author']}** commented:")
                lines.append(f"  > {comment['content'].replace(chr(10), chr(10) + '  > ')}")
            elif comment["type"] == "status_change":
                lines.append(f"- **[{comment['date']}] {comment['author']}** changed status: {comment['content']}")

    # Add related diffs
    if ticket.get("related_diffs"):
        lines.append("")
        lines.append("### Related Diffs")
        for diff in ticket["related_diffs"]:
            diff_emoji = {
                "Accepted": "✅", "Needs Review": "🔍", "Needs Revision": "🔄",
                "Closed": "✅", "Abandoned": "❌",
            }.get(diff["status"], "📋")
            lines.append(f"- **{diff['id']}** {diff_emoji} {diff['title']} ({diff['status']})")

    return "\n".join(lines)


async def main():
    parser = argparse.ArgumentParser(
        description="Get detailed information about a Phabricator ticket."
    )
    parser.add_argument(
        "ticket_id",
        help="The ticket ID (e.g., T123456)"
    )
    parser.add_argument(
        "--no-comments",
        action="store_true",
        help="Don't include comment history"
    )
    parser.add_argument(
        "--no-diffs",
        action="store_true",
        help="Don't include related diffs"
    )
    parser.add_argument(
        "--time-range", "-t",
        default="30d",
        choices=["7d", "14d", "30d", "60d", "90d"],
        help="Time range for activity history (default: 30d)"
    )
    parser.add_argument(
        "--full-description",
        action="store_true",
        help="Show full description without truncation"
    )
    parser.add_argument(
        "--full-comments",
        action="store_true",
        help="Show full comment text without truncation (default: truncates at 300 chars)"
    )
    parser.add_argument(
        "--activity-limit",
        type=int,
        default=10,
        metavar="N",
        help="Max number of recent activities to show (default: 10)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    # Normalize ticket ID
    ticket_id = args.ticket_id
    if not ticket_id.startswith("T"):
        ticket_id = f"T{ticket_id}"

    result = await get_ticket(
        ticket_id=ticket_id,
        include_comments=not args.no_comments,
        include_related_diffs=not args.no_diffs,
        time_range=args.time_range,
        full_description=args.full_description,
        full_comments=args.full_comments,
        activity_limit=args.activity_limit,
    )

    if result.get("error"):
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_ticket_detail(result))


if __name__ == "__main__":
    asyncio.run(main())
