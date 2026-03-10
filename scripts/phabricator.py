# Core Phabricator API implementation for the tickets skill.
# Not for direct CLI use — other scripts import functions from here.

import os
import re
import base64
import time
from pathlib import Path
from typing import Any
import httpx
from dotenv import load_dotenv

import config as cfg

# Load environment variables from .env file using absolute path
# This ensures the .env file is found regardless of the current working directory
_SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(_SCRIPT_DIR / ".env")

PHABRICATOR_API_TOKEN = os.getenv("PHABRICATOR_API_TOKEN")
PHABRICATOR_BASE_URL = cfg.get("base_url", "")


def get_api_token() -> str:
    """Get the Phabricator API token, raising an error if not set."""
    token = PHABRICATOR_API_TOKEN
    if not token:
        raise ValueError(
            "PHABRICATOR_API_TOKEN not set. "
            "Please set it in your .env file or environment variables."
        )
    return token


async def upload_file(file_path: str) -> tuple[str, str | None]:
    """
    Upload a file to Phabricator.

    Args:
        file_path: Local path to the file to upload.

    Returns:
        Tuple of (file_path, file_id) where file_id is like "F123456" or None on error.
    """
    try:
        with open(file_path, "rb") as file:
            file_data = file.read()
            data_base64 = base64.b64encode(file_data).decode()

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Upload the file
            upload_url = f"{PHABRICATOR_BASE_URL}/api/file.upload"
            upload_payload = {
                "api.token": get_api_token(),
                "data_base64": data_base64,
                "name": os.path.basename(file_path),
            }
            response = await client.post(upload_url, data=upload_payload)
            result = response.json()

            if "error_code" in result and result["error_code"]:
                print(f"Error uploading {file_path}: {result.get('error_info', 'Unknown error')}")
                return file_path, None

            phid = result["result"]

            # Get the file ID from the PHID
            info_url = f"{PHABRICATOR_BASE_URL}/api/file.info"
            info_payload = {
                "api.token": get_api_token(),
                "phid": phid,
            }
            info_response = await client.post(info_url, data=info_payload)
            file_id = info_response.json()["result"]["id"]

        return file_path, f"F{file_id}"

    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return file_path, None
    except Exception as e:
        print(f"Error uploading file {file_path}: {str(e)}")
        return file_path, None


async def upload_files(file_paths: list[str]) -> tuple[dict[str, str], list[str]]:
    """
    Upload multiple files to Phabricator.

    Args:
        file_paths: List of local file paths to upload.

    Returns:
        Tuple of (successful_uploads, errors) where:
        - successful_uploads: dict mapping file_path -> file_id (e.g., "F12345")
        - errors: list of error messages
    """
    successful_uploads: dict[str, str] = {}
    errors: list[str] = []

    for file_path in file_paths:
        if not os.path.exists(file_path):
            errors.append(f"File not found: {file_path}")
            continue

        _, file_id = await upload_file(file_path)
        if file_id:
            successful_uploads[file_path] = file_id
        else:
            errors.append(f"Failed to upload: {file_path}")

    return successful_uploads, errors


def format_file_references(file_ids: list[str]) -> str:
    """
    Format file IDs as Phabricator Remarkup references.

    Args:
        file_ids: List of file IDs (e.g., ["F123", "F456"])

    Returns:
        Formatted Remarkup string with each file on a new line.
        Example: "{F123}\n{F456}"
    """
    if not file_ids:
        return ""
    return "\n".join(f"{{{file_id}}}" for file_id in file_ids)


async def resolve_username_to_phid(username: str) -> str | None:
    """
    Resolve a Phabricator username to its PHID.

    Args:
        username: The Phabricator username.

    Returns:
        The user's PHID or None if not found.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{PHABRICATOR_BASE_URL}/api/user.search"
        payload = {
            "api.token": get_api_token(),
            "constraints[usernames][0]": username,
        }
        response = await client.post(url, data=payload)
        result = response.json()

        if "result" in result and result["result"]["data"]:
            return result["result"]["data"][0]["phid"]
        return None


async def resolve_usernames_to_phids(usernames: list[str]) -> dict[str, str]:
    """
    Resolve multiple Phabricator usernames to their PHIDs.

    Args:
        usernames: List of Phabricator usernames.

    Returns:
        Dict mapping username -> PHID for found users.
    """
    if not usernames:
        return {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{PHABRICATOR_BASE_URL}/api/user.search"
        payload = {"api.token": get_api_token()}
        for i, username in enumerate(usernames):
            payload[f"constraints[usernames][{i}]"] = username

        response = await client.post(url, data=payload)
        result = response.json()

        phid_map = {}
        if "result" in result and result["result"]["data"]:
            for user in result["result"]["data"]:
                phid_map[user["fields"]["username"]] = user["phid"]
        return phid_map


async def resolve_phids_to_usernames(phids: list[str]) -> dict[str, str]:
    """
    Resolve multiple PHIDs to usernames.

    Args:
        phids: List of user PHIDs.

    Returns:
        Dict mapping PHID -> username for found users.
    """
    if not phids:
        return {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{PHABRICATOR_BASE_URL}/api/user.search"
        payload = {"api.token": get_api_token()}
        for i, phid in enumerate(phids):
            payload[f"constraints[phids][{i}]"] = phid

        response = await client.post(url, data=payload)
        result = response.json()

        phid_map = {}
        if "result" in result and result["result"]["data"]:
            for user in result["result"]["data"]:
                phid_map[user["phid"]] = user["fields"]["username"]
        return phid_map


async def resolve_project_slug_to_phid(slug: str) -> str | None:
    """
    Resolve a project/tag slug to its PHID.

    Args:
        slug: The project slug (e.g., "webapp", "payments")

    Returns:
        The project's PHID or None if not found.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{PHABRICATOR_BASE_URL}/api/project.search"
        payload = {
            "api.token": get_api_token(),
            "constraints[slugs][0]": slug,
        }
        response = await client.post(url, data=payload)
        result = response.json()

        if "result" in result and result["result"]["data"]:
            return result["result"]["data"][0]["phid"]
        return None


async def resolve_project_slugs_to_phids(slugs: list[str]) -> tuple[list[str], list[str]]:
    """
    Resolve multiple project/tag slugs to their PHIDs.

    Args:
        slugs: List of project slugs.

    Returns:
        Tuple of (resolved_phids, not_found_slugs).
    """
    resolved = []
    not_found = []

    for slug in slugs:
        phid = await resolve_project_slug_to_phid(slug)
        if phid:
            resolved.append(phid)
        else:
            not_found.append(slug)

    return resolved, not_found


async def resolve_project_phids_to_names(phids: list[str]) -> dict[str, str]:
    """
    Batch resolve project PHIDs to their display names.

    Args:
        phids: List of project PHIDs.

    Returns:
        Dict mapping PHID -> project name for found projects.
    """
    if not phids:
        return {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{PHABRICATOR_BASE_URL}/api/project.search"
        payload = {"api.token": get_api_token()}
        for i, phid in enumerate(phids):
            payload[f"constraints[phids][{i}]"] = phid

        response = await client.post(url, data=payload)
        result = response.json()

        return {
            proj["phid"]: proj["fields"]["name"]
            for proj in result.get("result", {}).get("data", [])
        }


async def search_tickets(
    assignees: list[str] | None = None,
    authors: list[str] | None = None,
    statuses: list[str] | None = None,
    priorities: list[str] | None = None,
    time_range: str = "30d",
    limit: int = 50,
) -> dict[str, Any]:
    """
    Search for Phabricator tickets by various criteria.

    Args:
        assignees: Filter by assignee usernames.
        authors: Filter by author usernames.
        statuses: Filter by status ('open', 'resolved', 'wontfix', 'invalid').
        priorities: Filter by priority ('unbreak', 'triage', 'high', 'normal', 'low', 'wish').
        time_range: Search within timeframe ('7d', '14d', '30d', '60d', '90d').
        limit: Max results (max 100).

    Returns:
        Dict with 'tickets' list and 'error' string if any.
    """
    if not any([assignees, authors, statuses, priorities]):
        return {"tickets": [], "error": "Please provide at least one filter."}

    limit = min(limit, 100)

    # Calculate time range
    time_multipliers = {"7d": 7, "14d": 14, "30d": 30, "60d": 60, "90d": 90}
    days = time_multipliers.get(time_range, 30)
    since_timestamp = int(time.time()) - (days * 24 * 60 * 60)

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Resolve usernames to PHIDs
        assignee_phids = []
        author_phids = []
        phid_to_username = {}

        if assignees:
            phid_map = await resolve_usernames_to_phids(assignees)
            assignee_phids = list(phid_map.values())
            phid_to_username.update({v: k for k, v in phid_map.items()})
            if not assignee_phids:
                return {"tickets": [], "error": f"Could not find users: {', '.join(assignees)}"}

        if authors:
            phid_map = await resolve_usernames_to_phids(authors)
            author_phids = list(phid_map.values())
            phid_to_username.update({v: k for k, v in phid_map.items()})
            if not author_phids:
                return {"tickets": [], "error": f"Could not find users: {', '.join(authors)}"}

        # Build search payload
        url = f"{PHABRICATOR_BASE_URL}/api/maniphest.search"
        payload = {
            "api.token": get_api_token(),
            "constraints[modifiedStart]": since_timestamp,
            "attachments[projects]": 1,  # Request project/tag attachments
            "order": "newest",
            "limit": limit,
        }

        if assignee_phids:
            for i, phid in enumerate(assignee_phids):
                payload[f"constraints[assigned][{i}]"] = phid

        if author_phids:
            for i, phid in enumerate(author_phids):
                payload[f"constraints[authorPHIDs][{i}]"] = phid

        if statuses:
            for i, status in enumerate(statuses):
                payload[f"constraints[statuses][{i}]"] = status

        if priorities:
            priority_map = {
                "unbreak": 100, "triage": 90, "high": 80,
                "normal": 50, "low": 25, "wish": 0,
            }
            for i, priority in enumerate(priorities):
                payload[f"constraints[priorities][{i}]"] = priority_map.get(priority.lower(), priority)

        response = await client.post(url, data=payload)
        result = response.json()

        if "result" not in result or not result["result"]["data"]:
            return {"tickets": [], "error": None}

        tickets = result["result"]["data"]

        # Resolve additional user PHIDs
        user_phids_to_resolve = set()
        for ticket in tickets:
            if ticket["fields"].get("ownerPHID"):
                user_phids_to_resolve.add(ticket["fields"]["ownerPHID"])
            if ticket["fields"].get("authorPHID"):
                user_phids_to_resolve.add(ticket["fields"]["authorPHID"])

        user_phids_to_resolve -= set(phid_to_username.keys())
        if user_phids_to_resolve:
            resolved = await resolve_phids_to_usernames(list(user_phids_to_resolve))
            phid_to_username.update(resolved)

        # Collect and resolve project PHIDs for tags
        project_phids_to_resolve = set()
        for ticket in tickets:
            project_phids = ticket.get("attachments", {}).get("projects", {}).get("projectPHIDs", [])
            project_phids_to_resolve.update(project_phids)

        phid_to_project_name = await resolve_project_phids_to_names(list(project_phids_to_resolve))

        # Format tickets
        formatted_tickets = []
        for ticket in tickets:
            fields = ticket["fields"]
            owner_phid = fields.get("ownerPHID")
            author_phid = fields.get("authorPHID")

            # Get tags from project attachments
            project_phids = ticket.get("attachments", {}).get("projects", {}).get("projectPHIDs", [])
            tags = [phid_to_project_name.get(phid, phid) for phid in project_phids]

            formatted_tickets.append({
                "id": f"T{ticket['id']}",
                "title": fields.get("name", "Untitled"),
                "status": fields.get("status", {}).get("name", "Unknown"),
                "priority": fields.get("priority", {}).get("name", "Unknown"),
                "owner": phid_to_username.get(owner_phid, "Unassigned") if owner_phid else "Unassigned",
                "author": phid_to_username.get(author_phid, "Unknown") if author_phid else "Unknown",
                "modified": time.strftime("%Y-%m-%d", time.localtime(fields.get("dateModified", 0))),
                "url": f"{PHABRICATOR_BASE_URL}/T{ticket['id']}",
                "tags": tags,
            })

        return {"tickets": formatted_tickets, "error": None}


async def get_ticket(
    ticket_id: str,
    include_comments: bool = True,
    include_related_diffs: bool = True,
    time_range: str = "30d",
    full_description: bool = False,
    full_comments: bool = False,
    activity_limit: int = 10,
) -> dict[str, Any]:
    """
    Get detailed ticket information.

    Args:
        ticket_id: The ticket ID (e.g., 'T123456').
        include_comments: Include comment history.
        include_related_diffs: Include related diffs.
        time_range: Time range for activity ('7d', '14d', '30d', etc.).
        full_description: Return full description without truncation.
        full_comments: Return full comment text without truncation.
        activity_limit: Max number of recent activities to return (default 10).

    Returns:
        Dict with ticket details or error.
    """
    time_multipliers = {"7d": 7, "14d": 14, "30d": 30, "60d": 60, "90d": 90}
    days = time_multipliers.get(time_range, 30)
    since_timestamp = int(time.time()) - (days * 24 * 60 * 60)

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Fetch ticket
        url = f"{PHABRICATOR_BASE_URL}/api/maniphest.search"
        payload = {
            "api.token": get_api_token(),
            "constraints[ids][0]": re.sub(r"^T", "", ticket_id),
            "attachments[projects]": 1,  # Request project/tag attachments
        }
        response = await client.post(url, data=payload)
        result = response.json()

        if "result" not in result or not result["result"]["data"]:
            return {"error": f"Ticket {ticket_id} not found"}

        ticket = result["result"]["data"][0]
        fields = ticket["fields"]

        # Resolve user PHIDs
        phid_to_username = {}
        user_phids = []
        if fields.get("ownerPHID"):
            user_phids.append(fields["ownerPHID"])
        if fields.get("authorPHID"):
            user_phids.append(fields["authorPHID"])

        if user_phids:
            phid_to_username = await resolve_phids_to_usernames(user_phids)

        owner_phid = fields.get("ownerPHID")
        author_phid = fields.get("authorPHID")

        description = fields.get("description", {}).get("raw", "")
        if not full_description and len(description) > 1500:
            description = description[:1500] + "..."

        # Resolve project PHIDs to names for tags
        project_phids = ticket.get("attachments", {}).get("projects", {}).get("projectPHIDs", [])
        phid_to_project_name = await resolve_project_phids_to_names(project_phids)
        tags = [phid_to_project_name.get(phid, phid) for phid in project_phids]

        ticket_data = {
            "id": f"T{ticket['id']}",
            "title": fields.get("name", "Untitled"),
            "description": description,
            "status": fields.get("status", {}).get("name", "Unknown"),
            "priority": fields.get("priority", {}).get("name", "Unknown"),
            "owner": phid_to_username.get(owner_phid, "Unassigned") if owner_phid else "Unassigned",
            "author": phid_to_username.get(author_phid, "Unknown") if author_phid else "Unknown",
            "created": time.strftime("%Y-%m-%d", time.localtime(fields.get("dateCreated", 0))),
            "modified": time.strftime("%Y-%m-%d", time.localtime(fields.get("dateModified", 0))),
            "tags": tags,
            "url": f"{PHABRICATOR_BASE_URL}/T{ticket['id']}",
            "comments": [],
            "related_diffs": [],
        }

        # Fetch comments
        if include_comments:
            txn_url = f"{PHABRICATOR_BASE_URL}/api/transaction.search"
            txn_payload = {
                "api.token": get_api_token(),
                "objectIdentifier": ticket_id,
            }
            txn_response = await client.post(txn_url, data=txn_payload)
            txn_result = txn_response.json()

            if "result" in txn_result and txn_result["result"]["data"]:
                transactions = txn_result["result"]["data"]

                # Collect user PHIDs from transactions
                txn_user_phids = set()
                for txn in transactions:
                    if txn.get("authorPHID"):
                        txn_user_phids.add(txn["authorPHID"])

                new_phids = txn_user_phids - set(phid_to_username.keys())
                if new_phids:
                    resolved = await resolve_phids_to_usernames(list(new_phids))
                    phid_to_username.update(resolved)

                comments = []
                for txn in transactions:
                    txn_time = txn.get("dateCreated", 0)
                    if txn_time < since_timestamp:
                        continue

                    txn_type = txn.get("type", "")
                    author_phid = txn.get("authorPHID", "")
                    author_name = phid_to_username.get(author_phid, "Unknown")
                    date_str = time.strftime("%Y-%m-%d", time.localtime(txn_time))

                    if txn_type == "comment" and txn.get("comments"):
                        comment_text = txn["comments"][0].get("content", {}).get("raw", "")
                        truncated = comment_text if full_comments else (
                            comment_text[:300] + "..." if len(comment_text) > 300 else comment_text
                        )
                        comments.append({
                            "type": "comment",
                            "author": author_name,
                            "date": date_str,
                            "content": truncated,
                        })
                    elif txn_type == "status":
                        old_status = txn.get("fields", {}).get("old", "unknown")
                        new_status = txn.get("fields", {}).get("new", "unknown")
                        comments.append({
                            "type": "status_change",
                            "author": author_name,
                            "date": date_str,
                            "content": f"{old_status} → {new_status}",
                        })

                ticket_data["comments"] = comments[-activity_limit:]  # Last N activities

        # Fetch related diffs
        if include_related_diffs:
            edge_url = f"{PHABRICATOR_BASE_URL}/api/edge.search"
            edge_payload = {
                "api.token": get_api_token(),
                "sourcePHIDs[0]": ticket["phid"],
                "types[0]": "task.revision",
            }
            edge_response = await client.post(edge_url, data=edge_payload)
            edge_result = edge_response.json()

            if "result" in edge_result and edge_result["result"]["data"]:
                diff_phids = [edge["destinationPHID"] for edge in edge_result["result"]["data"]]

                if diff_phids:
                    diff_url = f"{PHABRICATOR_BASE_URL}/api/differential.revision.search"
                    diff_payload = {"api.token": get_api_token()}
                    for i, phid in enumerate(diff_phids[:10]):
                        diff_payload[f"constraints[phids][{i}]"] = phid

                    diff_response = await client.post(diff_url, data=diff_payload)
                    diff_result = diff_response.json()

                    if "result" in diff_result and diff_result["result"]["data"]:
                        for diff in diff_result["result"]["data"]:
                            ticket_data["related_diffs"].append({
                                "id": f"D{diff['id']}",
                                "title": diff["fields"]["title"],
                                "status": diff["fields"]["status"]["name"],
                            })

        return ticket_data


async def create_ticket(
    title: str,
    description: str | None = None,
    priority: str | None = None,
    owner: str | None = None,
    parent_ticket: str | None = None,
    tags: list[str] | None = None,
    file_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Create a new Phabricator ticket.

    Args:
        title: The ticket title (required).
        description: The ticket description.
        priority: Priority ('unbreak', 'triage', 'high', 'normal', 'low', 'wish').
        owner: Username to assign the ticket to.
        parent_ticket: Parent ticket ID (e.g., 'T123456').
        tags: Project/tag slugs to add.
        file_ids: Pre-uploaded file IDs to embed (e.g., ['F123', 'F456']).

    Returns:
        Dict with 'ticket_id', 'url', and optional 'error'.
    """
    transactions = []
    transactions.append({"type": "title", "value": title})

    # Handle description with embedded files
    if description or file_ids:
        desc_content = description or ""
        if file_ids:
            file_refs = format_file_references(file_ids)
            desc_content = f"{desc_content}\n\n{file_refs}" if desc_content else file_refs
        transactions.append({"type": "description", "value": desc_content})

    if priority:
        priority_map = {
            "unbreak": "unbreak", "triage": "triage", "high": "high",
            "normal": "normal", "low": "low", "wish": "wish",
        }
        transactions.append({"type": "priority", "value": priority_map.get(priority.lower(), priority)})

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Resolve owner
        if owner:
            owner_phid = await resolve_username_to_phid(owner)
            if not owner_phid:
                return {"error": f"Could not find user '{owner}'"}
            transactions.append({"type": "owner", "value": owner_phid})

        # Resolve parent ticket
        if parent_ticket:
            parent_url = f"{PHABRICATOR_BASE_URL}/api/maniphest.search"
            parent_payload = {
                "api.token": get_api_token(),
                "constraints[ids][0]": re.sub(r"^T", "", parent_ticket),
            }
            parent_response = await client.post(parent_url, data=parent_payload)
            parent_result = parent_response.json()

            if "result" not in parent_result or not parent_result["result"]["data"]:
                return {"error": f"Could not find parent ticket '{parent_ticket}'"}

            parent_phid = parent_result["result"]["data"][0]["phid"]
            transactions.append({"type": "parent", "value": parent_phid})

        # Resolve tags
        if tags:
            resolved_tags, not_found = await resolve_project_slugs_to_phids(tags)
            if resolved_tags:
                transactions.append({"type": "projects.add", "value": resolved_tags})

        # Create ticket
        url = f"{PHABRICATOR_BASE_URL}/api/maniphest.edit"
        payload = {"api.token": get_api_token()}

        for i, txn in enumerate(transactions):
            payload[f"transactions[{i}][type]"] = txn["type"]
            if isinstance(txn["value"], list):
                for j, val in enumerate(txn["value"]):
                    payload[f"transactions[{i}][value][{j}]"] = val
            else:
                payload[f"transactions[{i}][value]"] = txn["value"]

        response = await client.post(url, data=payload)
        result = response.json()

        if "error_code" in result and result["error_code"]:
            return {"error": result.get("error_info", "Unknown error")}

        task = result["result"]["object"]
        task_id = f"T{task['id']}"

        return {
            "ticket_id": task_id,
            "url": f"{PHABRICATOR_BASE_URL}/{task_id}",
            "error": None,
        }


async def update_ticket(
    ticket_id: str,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    owner: str | None = None,
    comment: str | None = None,
    add_tags: list[str] | None = None,
    remove_tags: list[str] | None = None,
    file_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Update an existing Phabricator ticket.

    Args:
        ticket_id: The ticket ID (e.g., 'T123456').
        title: New title.
        description: New description.
        status: New status ('open', 'resolved', 'wontfix', 'invalid', 'spite').
        priority: New priority.
        owner: New owner username (empty string to unassign).
        comment: Comment to add.
        add_tags: Tags to add.
        remove_tags: Tags to remove.
        file_ids: Pre-uploaded file IDs to embed in description.

    Returns:
        Dict with 'success' bool and optional 'error'.
    """
    transactions = []
    warnings = []

    if title is not None:
        transactions.append({"type": "title", "value": title})

    if description is not None or file_ids:
        desc_content = description or ""
        if file_ids:
            file_refs = format_file_references(file_ids)
            desc_content = f"{desc_content}\n\n{file_refs}" if desc_content else file_refs
        transactions.append({"type": "description", "value": desc_content})

    if status is not None:
        transactions.append({"type": "status", "value": status})

    if priority is not None:
        priority_map = {
            "unbreak": "unbreak", "triage": "triage", "high": "high",
            "normal": "normal", "low": "low", "wish": "wish",
        }
        transactions.append({"type": "priority", "value": priority_map.get(priority.lower(), priority)})

    if owner is not None:
        if owner == "":
            transactions.append({"type": "owner", "value": None})
        else:
            owner_phid = await resolve_username_to_phid(owner)
            if not owner_phid:
                return {"success": False, "error": f"Could not find user '{owner}'"}
            transactions.append({"type": "owner", "value": owner_phid})

    if comment is not None:
        transactions.append({"type": "comment", "value": comment})

    if add_tags:
        resolved, not_found = await resolve_project_slugs_to_phids(add_tags)
        if resolved:
            transactions.append({"type": "projects.add", "value": resolved})
        if not_found:
            warnings.append(f"Tags not found: {', '.join(not_found)}")

    if remove_tags:
        resolved, not_found = await resolve_project_slugs_to_phids(remove_tags)
        if resolved:
            transactions.append({"type": "projects.remove", "value": resolved})
        if not_found:
            warnings.append(f"Tags not found: {', '.join(not_found)}")

    if not transactions:
        return {"success": False, "error": "No changes specified"}

    url = f"{PHABRICATOR_BASE_URL}/api/maniphest.edit"
    payload = {
        "api.token": get_api_token(),
        "objectIdentifier": ticket_id,
    }

    for i, txn in enumerate(transactions):
        payload[f"transactions[{i}][type]"] = txn["type"]
        if txn["value"] is None:
            payload[f"transactions[{i}][value]"] = ""
        elif isinstance(txn["value"], list):
            for j, val in enumerate(txn["value"]):
                payload[f"transactions[{i}][value][{j}]"] = val
        else:
            payload[f"transactions[{i}][value]"] = txn["value"]

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, data=payload)
            result = response.json()

            if "error_code" in result and result["error_code"]:
                return {"success": False, "error": result.get("error_info", "Unknown error")}

            return {"success": True, "warnings": warnings if warnings else None}

    except Exception as e:
        return {"success": False, "error": str(e)}
