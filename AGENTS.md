# AGENTS.md

This file is the agent entry point for `phab-skill/`.

## README First

- Read `README.md` first. It is the Phabricator skill guide and workflow source.
- Keep install, setup, CLI workflow, and file-structure details in `README.md`.
- Keep current ticket-skill notes in `memory.md`; keep old skill history in `archive.md`.

## Agent Rules

- Use simple English for docs and code.
- Preserve safe read-merge-update behaviour when changing ticket update flows.
- Keep API tokens and generated credentials out of commits.
- Add or update focused tests when changing parsing, API, or upload behaviour.
- Run Git commands from this folder.
