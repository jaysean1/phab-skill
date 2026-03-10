#!/usr/bin/env python3
# .claude/skills/tickets/scripts/search_tickets.py
# CLI tool to search Phabricator tickets by various criteria.
# Usage: uv run search_tickets.py --assignee jqian --status open

import argparse
import asyncio
import json
import sys

from phabricator import search_tickets


def format_ticket_list(tickets: list[dict]) -> str:
    """Format tickets for display."""
    if not tickets:
        return "No tickets found."

    lines = [f"Found {len(tickets)} ticket(s):\n"]

    for ticket in tickets:
        status_emoji = {
            "Open": "🟢", "Resolved": "✅", "Closed": "🔒",
            "In Progress": "🔨", "Stalled": "⏸️", "Invalid": "❌",
        }.get(ticket["status"], "📋")

        # Format tags: show up to 3, with count if more
        tags = ticket.get("tags", [])
        if tags:
            tags_display = ", ".join(tags[:3])
            if len(tags) > 3:
                tags_display += f" (+{len(tags) - 3})"
        else:
            tags_display = "-"

        lines.append(f"  {ticket['id']} {status_emoji} {ticket['title']}")
        lines.append(f"    Status: {ticket['status']} | Priority: {ticket['priority']}")
        lines.append(f"    Owner: {ticket['owner']} | Modified: {ticket['modified']}")
        lines.append(f"    Tags: {tags_display}")
        lines.append(f"    {ticket['url']}")
        lines.append("")

    return "\n".join(lines)


async def main():
    parser = argparse.ArgumentParser(
        description="Search Phabricator tickets by various criteria."
    )
    parser.add_argument(
        "--assignee", "-a",
        action="append",
        dest="assignees",
        help="Filter by assignee username (can be used multiple times)"
    )
    parser.add_argument(
        "--author",
        action="append",
        dest="authors",
        help="Filter by author username (can be used multiple times)"
    )
    parser.add_argument(
        "--status", "-s",
        action="append",
        dest="statuses",
        choices=["open", "resolved", "wontfix", "invalid"],
        help="Filter by status (can be used multiple times)"
    )
    parser.add_argument(
        "--priority", "-p",
        action="append",
        dest="priorities",
        choices=["unbreak", "triage", "high", "normal", "low", "wish"],
        help="Filter by priority (can be used multiple times)"
    )
    parser.add_argument(
        "--time-range", "-t",
        default="30d",
        choices=["7d", "14d", "30d", "60d", "90d"],
        help="Time range to search within (default: 30d)"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=50,
        help="Maximum number of results (default: 50, max: 100)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    # Validate that at least one filter is provided
    if not any([args.assignees, args.authors, args.statuses, args.priorities]):
        parser.error("At least one filter is required: --assignee, --author, --status, or --priority")

    result = await search_tickets(
        assignees=args.assignees,
        authors=args.authors,
        statuses=args.statuses,
        priorities=args.priorities,
        time_range=args.time_range,
        limit=args.limit,
    )

    if result.get("error"):
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result["tickets"], indent=2))
    else:
        print(format_ticket_list(result["tickets"]))


if __name__ == "__main__":
    asyncio.run(main())
