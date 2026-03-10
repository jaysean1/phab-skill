# Team Status Reference

## When to Use

Run `team_status.py` when the user asks any of the following (in English or Chinese):

- 查看全队 / 全队状态 / 团队状态
- team status / team workload / team overview
- who is working on what
- show all team members' tickets

---

## Run Command

```bash
cd .claude/skills/tickets/scripts
UV_CACHE_DIR=/tmp/uv-cache uv run team_status.py
```

To filter to a single member:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run team_status.py --member <username>
```

---

## Output Format

After the script finishes, present the results in **three sections** as described below.
Do not reprint the raw script output verbatim.

---

### Section 1 — Summary Table

Print the summary table exactly as the script outputs it.
No extra commentary is needed in this section.

Example:

```
Member        Work  Review  High Pri
---------     ----  ------  --------
jqian           3      1       1
asmith          5      2       2
...
```

---

### Section 2 — Overall Summary

Give a short team-level summary of the main work themes.

Rules:

1. Focus on **project themes**, not workload commentary.
2. Keep it short: **3-5 bullets** maximum.
3. Each bullet should include:
   - theme name
   - number of tickets
   - involved members
   - one representative ticket ID

Example:

```text
## Overall Summary

- Carrier onboarding work is the biggest stream, involving @jjtran and @cechon with 8 tickets. Representative: T327905
- PSTN / calling work is active under @kpau with 4 tickets. Representative: T324948
```

---

### Section 3 — Per-person Breakdown

Rules:

1. **Exclude review tickets** — skip any ticket whose title contains "Review request".
2. **Skip members with 0 work tickets** after filtering out review tickets.
3. **Summarise by theme** — do not list every ticket.
4. **Keep each member short** — show only the top **2-3 themes**.
5. **Attach one representative ticket** per theme.
6. **Sort themes** — high priority first, then the rest.
7. **Format each member's block:**

```text
### @username (N work tickets)

- Theme name (X tickets)
  Representative: emoji ID | Priority | Modified date | Title
  URL
```

**Example block:**

```text
### @jqian (3 work tickets)

- Quote / pricing updates (2 tickets)
  Representative: 🟠 T324178 | High | 2026-02-28 | Improve onboarding flow for new drivers
  https://phabricator.tools.flnltd.com/T324178

- Admin tools (1 ticket)
  Representative: 🟡 T321001 | Normal | 2026-02-25 | Update help centre FAQ content
  https://phabricator.tools.flnltd.com/T321001
```

---

## Deeper Progress ("具体进展")

`team_status.py` mainly works from ticket titles and lightweight grouping rules.
It may also look up a small number of representative tickets for better theme names,
but it does **not** fetch full details for every ticket.

If the user asks for deeper progress on a **specific person or ticket**, follow up with:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run get_ticket.py T<id> --full-description --full-comments
```

> **Important:** Do NOT run `get_ticket.py` for every ticket during a team overview.
> That would make too many API calls. Only look up individual tickets when the user
> explicitly asks for details on a specific ticket or person.
