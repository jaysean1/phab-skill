# Show all team members' open ticket counts with per-person breakdown.
# Not for creating, updating, or closing tickets.

import argparse
import asyncio
import json
import re
import sys
from datetime import date
from pathlib import Path

# Allow direct import of phabricator.py from the same directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as cfg
import phabricator as ph

TEAM_MEMBERS = cfg.get("team_members", [])

PRIORITY_EMOJI = {
    "Unbreak Now!": "🔴",
    "High": "🟠",
    "Normal": "🟡",
    "Low": "🔵",
    "Wish": "⚪",
    "Needs Triage": "⚪",
}

HIGH_PRIORITIES = {"Unbreak Now!", "High"}
PRIORITY_ORDER = {
    "Unbreak Now!": 0,
    "High": 1,
    "Normal": 2,
    "Low": 3,
    "Wish": 4,
    "Needs Triage": 5,
}

MAX_MEMBER_THEMES = 3
DEEP_DIVE_LIMIT = 8
IGNORED_TAGS = {"loadshift team"}


def priority_emoji(priority: str) -> str:
    return PRIORITY_EMOJI.get(priority, "⚪")


def priority_rank(priority: str) -> int:
    return PRIORITY_ORDER.get(priority, 99)


def modified_ordinal(value: str) -> int:
    try:
        return date.fromisoformat(value).toordinal()
    except ValueError:
        return 0


def is_review_ticket(ticket: dict) -> bool:
    return "Review request" in ticket["title"]


def sort_tickets(tickets: list[dict]) -> list[dict]:
    return sorted(
        tickets,
        key=lambda ticket: (
            priority_rank(ticket["priority"]),
            -modified_ordinal(ticket["modified"]),
            ticket["id"],
        ),
    )


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def clean_title(title: str) -> str:
    cleaned = clean_text(title)
    cleaned = re.sub(r"^#+\s*", "", cleaned)
    cleaned = re.sub(r"^\|[^|]+\|\s*", "", cleaned)
    return cleaned.strip(" -|:") or clean_text(title)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug or "misc"


def extract_description_hint(description: str) -> str | None:
    if not description:
        return None

    for raw_line in description.splitlines():
        line = clean_text(raw_line.lstrip("#-*0123456789. "))
        if not line:
            continue
        if len(line) > 72:
            continue
        if line.lower() in {"overview", "summary", "description"}:
            continue
        return line.rstrip(".")
    return None


def meaningful_tags(tags: list[str]) -> list[str]:
    return [tag for tag in tags if tag.lower() not in IGNORED_TAGS]


def topic_from_title(title: str, description: str = "", tags: list[str] | None = None) -> tuple[str, str]:
    cleaned_title = clean_title(title)
    label = None

    if not label:
        bracket_match = re.match(r"^\[([^\]]+)\]\s*(.*)$", cleaned_title)
        if bracket_match:
            prefix = clean_text(bracket_match.group(1)).upper()
            if prefix:
                label = prefix
            cleaned_title = clean_text(bracket_match.group(2)) or cleaned_title

    if not label:
        for separator in (" - ", ": ", " | ", " — "):
            if separator in cleaned_title:
                label = clean_text(cleaned_title.split(separator, 1)[0])
                break

    if not label:
        label = cleaned_title

    generic_prefixes = (
        "fix ",
        "update ",
        "request ",
        "role ",
        "investigation",
        "investigate ",
    )
    if description and (
        label.lower().startswith(generic_prefixes)
        or len(label.split()) <= 2
    ):
        description_hint = extract_description_hint(description)
        if description_hint:
            label = description_hint

    if tags:
        for tag in meaningful_tags(tags):
            if tag.lower() not in label.lower() and len(label.split()) <= 2:
                label = f"{label} ({tag})"
                break

    label = clean_text(label)
    return slugify(label), label


def build_topics(tickets: list[dict], ticket_details: dict[str, dict] | None = None) -> list[dict]:
    topics: dict[str, dict] = {}

    for ticket in tickets:
        details = (ticket_details or {}).get(ticket["id"], {})
        key, display = topic_from_title(
            ticket["title"],
            description=details.get("description", ""),
            tags=details.get("tags", []),
        )
        topic = topics.setdefault(
            key,
            {
                "key": key,
                "display": display,
                "tickets": [],
                "members": set(),
            },
        )
        topic["tickets"].append(ticket)
        topic["members"].add(ticket["owner"])

    for topic in topics.values():
        topic["tickets"] = sort_tickets(topic["tickets"])
        topic["representative"] = topic["tickets"][0]
        topic["ticket_count"] = len(topic["tickets"])
        topic["high_count"] = sum(
            1 for ticket in topic["tickets"] if ticket["priority"] in HIGH_PRIORITIES
        )
        topic["latest_modified"] = max(ticket["modified"] for ticket in topic["tickets"])
        topic["member_count"] = len(topic["members"])

    return list(topics.values())


def member_topic_sort_key(topic: dict) -> tuple:
    representative = topic["representative"]
    return (
        0 if topic["high_count"] else 1,
        -topic["high_count"],
        -topic["ticket_count"],
        -modified_ordinal(topic["latest_modified"]),
        priority_rank(representative["priority"]),
        topic["display"].lower(),
    )


def truncate(text: str, max_len: int = 72) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def ticket_count_text(count: int) -> str:
    if count == 1:
        return "1 ticket"
    return f"{count} tickets"


async def fetch_ticket_details(ticket_ids: list[str]) -> dict[str, dict]:
    unique_ids = list(dict.fromkeys(ticket_ids))[:DEEP_DIVE_LIMIT]
    if not unique_ids:
        return {}

    async def fetch_one(ticket_id: str) -> tuple[str, dict | None]:
        result = await ph.get_ticket(
            ticket_id=ticket_id,
            include_comments=False,
            include_related_diffs=False,
            full_description=False,
        )
        if result.get("error"):
            return ticket_id, None
        return ticket_id, result

    pairs = await asyncio.gather(*[fetch_one(ticket_id) for ticket_id in unique_ids])
    return {ticket_id: detail for ticket_id, detail in pairs if detail}


async def fetch_all(members: list[str]) -> dict[str, list]:
    """Fetch open tickets for all members concurrently."""

    async def fetch_one(member: str) -> tuple[str, list]:
        result = await ph.search_tickets(
            assignees=[member],
            statuses=["open"],
            time_range="90d",
            limit=100,
        )
        return member, result.get("tickets", [])

    pairs = await asyncio.gather(*[fetch_one(member) for member in members])
    return dict(pairs)


def collect_deep_dive_candidates(
    work_data: dict[str, list[dict]],
    member_topics: dict[str, list[dict]],
) -> list[str]:
    candidates: list[str] = []

    for member, tickets in work_data.items():
        if not tickets or not member_topics.get(member):
            continue
        top_topic = member_topics[member][0]
        representative = top_topic["representative"]
        should_fetch = (
            representative["priority"] in HIGH_PRIORITIES
            or top_topic["ticket_count"] >= 2
            or len(top_topic["display"].split()) <= 2
        )
        if should_fetch:
            candidates.append(representative["id"])

    return list(dict.fromkeys(candidates))[:DEEP_DIVE_LIMIT]


def print_summary_table(data: dict[str, list]) -> None:
    def stats(tickets: list[dict]) -> tuple[int, int, int]:
        review = sum(1 for ticket in tickets if is_review_ticket(ticket))
        work = len(tickets) - review
        high = sum(
            1
            for ticket in tickets
            if not is_review_ticket(ticket) and ticket["priority"] in HIGH_PRIORITIES
        )
        return work, review, high

    rows = [(member, *stats(tickets)) for member, tickets in data.items()]
    rows.sort(key=lambda row: (row[1], row[2]), reverse=True)

    total_work = sum(row[1] for row in rows)
    total_review = sum(row[2] for row in rows)
    total_high = sum(row[3] for row in rows)

    name_width = max(len(member) for member in data) + 2
    header = f"{'Member':<{name_width}} {'Work':>6}  {'Review':>8}  {'High Pri':>9}"
    divider = "-" * len(header)

    print("## Summary Table")
    print()
    print(header)
    print(divider)
    for member, work, review, high in rows:
        print(f"{member:<{name_width}} {work:>6}  {review:>8}  {high:>9}")
    print(divider)
    print(f"{'TOTAL':<{name_width}} {total_work:>6}  {total_review:>8}  {total_high:>9}")
    print()


def print_breakdown(work_data: dict[str, list], member_topics: dict[str, list[dict]]) -> None:
    print("## Per Person Breakdown")
    print()

    sorted_members = sorted(
        work_data.items(),
        key=lambda item: (-len(item[1]), item[0]),
    )

    for member, tickets in sorted_members:
        if not tickets:
            continue

        topics = member_topics.get(member, [])[:MAX_MEMBER_THEMES]
        if not topics:
            continue

        print(f"### @{member} ({len(tickets)} work tickets)")
        print()
        for topic in topics:
            representative = topic["representative"]
            print(f"- {truncate(topic['display'], 48)} ({ticket_count_text(topic['ticket_count'])})")
            print(
                f"  Representative: {priority_emoji(representative['priority'])} "
                f"{representative['id']} | {representative['priority']} | "
                f"{representative['modified']} | {truncate(representative['title'])}"
            )
            print(f"  {representative['url']}")
            print()


def output_json(data: dict[str, list]) -> None:
    payload = {
        member: [
            {
                "id": ticket["id"],
                "title": ticket["title"],
                "priority": ticket["priority"],
                "modified": ticket["modified"],
                "url": ticket["url"],
            }
            for ticket in tickets
        ]
        for member, tickets in data.items()
    }
    print(json.dumps(payload, indent=2))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Show team open ticket status.")
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of plain text.")
    parser.add_argument("--member", metavar="USERNAME", help="Limit to a single team member.")
    args = parser.parse_args()

    members = [args.member] if args.member else TEAM_MEMBERS

    if not members:
        print("Error: No team members configured. Run setup.py or edit config.yaml.", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching open tickets for {len(members)} member(s)...", flush=True)
    data = await fetch_all(members)

    if args.json:
        output_json(data)
        return

    work_data = {
        member: [ticket for ticket in tickets if not is_review_ticket(ticket)]
        for member, tickets in data.items()
    }

    initial_member_topics = {
        member: sorted(build_topics(tickets), key=member_topic_sort_key)
        for member, tickets in work_data.items()
    }

    ticket_details = await fetch_ticket_details(
        collect_deep_dive_candidates(work_data, initial_member_topics)
    )

    member_topics = {
        member: sorted(build_topics(tickets, ticket_details), key=member_topic_sort_key)
        for member, tickets in work_data.items()
    }

    print_summary_table(data)
    print_breakdown(work_data, member_topics)


asyncio.run(main())
