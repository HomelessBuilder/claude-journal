# CLAUDE.md — journal project (public framework)

*This is the public counterpart to a private working repo. It shows the
structure and format of the journal system — not the actual log content.*

## What this project is

This is the flat-file prototype of a machine-wide activity journal. It will eventually migrate to a MySQL backend via `~/devlog-engine`. Until then, it is the working system.

It covers **all activity on this machine** — not just specific projects. Every Claude Code session (including the overseer at `~/`), system configuration, research, and exploration is loggable here.

It has two jobs:

1. **Re-entry aid.** When Diego returns to any project or activity after an irregular gap,
   the journal gives him fast context: what was happening, what the next
   action is, what's blocked.

2. **Content source material.** The same log entries serve as raw material
   for LinkedIn posts, blog posts, YouTube Shorts scripts, and eventually a
   book and course — under the "Homeless Builder" brand. Write once, repurpose
   many times. Don't write separate versions per output type.

## Scope

All machine activity is in scope:

| Activity Type | Examples |
|---|---|
| Project sessions | sandiegoai.help, devlog-engine, any new project |
| Overseer sessions | Home-directory Claude Code decisions and planning |
| System / admin | Installs, config changes, infrastructure work |
| Research / exploration | Investigations that don't belong to a specific project |

*This scope is maintained by the overseer instance at `~/`. Do not edit this table directly from within a journal session — ask the overseer to update it when something new is added.*

## File structure

```
claude-journal/
  CLAUDE.md               ← this file
  DEVLOG.md               ← the running log (append only, newest entries at top)
  CURRENT.md              ← current state per project (overwritten each session)
  .claude/
    commands/
      journal.md           ← /journal slash command
```

## Migration Note

This flat-file system is a prototype. Once `~/devlog-engine` delivers the MySQL write script, entries will be written to the database instead of DEVLOG.md. The format and fields will stay the same — only the destination changes.

## DEVLOG.md format

Each entry follows this structure exactly:

```
## YYYY-MM-DD — [Project / Activity]
**Status:** one sentence on where the project stands right now
**Tags:** [Technical] [Process] [Story] [System] (use one or more)

[2–5 sentences: what happened, what the real obstacle was, what was learned,
any notable moment or quote. Plain language. No code-level detail — that's
git's job. Write from the perspective of someone explaining the session to
a colleague who understands the work but wasn't there.]

---
```

Tag definitions:
- **[Technical]** — a specific tool, setup, or code lesson
- **[Process]** — how the work was approached, AI collaboration pattern, workflow decision
- **[Story]** — frustration, reframe, realization, human moment worth capturing for content
- **[System]** — machine-level activity: installs, config, infrastructure, admin tasks

Newest entries go at the TOP of DEVLOG.md. Do not reorder existing entries.

## CURRENT.md format

One section per active project, overwritten (not appended) each session:

```
# Current Project Status
*Last updated: YYYY-MM-DD*

## [Project Name]
**Status:** one sentence
**In progress when session ended:** what was mid-flight
**Next action:** the single clearest thing to do when returning
**Open questions / blockers:** anything unresolved

---
```

## Handoff Format

Any Claude Code instance (including the overseer) passes a session summary in this format:

```
Project / Activity: [name or description]
Date: [YYYY-MM-DD]
What happened: [2–5 sentences in plain language]
Real obstacle: [what slowed things down or required a decision]
In progress when session ended: [anything mid-flight]
Next action: [the single clearest thing to do next time]
Open questions / blockers: [anything unresolved]
Tag: [Technical | Process | Story | System] (one or more)
```

The journal instance writes the DEVLOG entry from that summary, then updates CURRENT.md. It does not need to read source project files — the summary is the source of truth.

## Rules for this session (librarian role)

- Never touch project source code. This session only writes to journal files.
- When receiving a /journal handoff, write the DEVLOG entry first, then update
  the relevant project section in CURRENT.md.
- Do not invent detail. If the summary passed in is thin, write a thin entry
  rather than padding it. Flag to Diego that the source material was sparse.
- Commit both files together after writing:
  `git add DEVLOG.md CURRENT.md && git commit -m "Session log: YYYY-MM-DD — [Project / Activity]"`
- Ask Diego to confirm before committing if anything in the entry feels
  uncertain or worth reviewing.
