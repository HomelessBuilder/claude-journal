#!/usr/bin/env python3
"""
journal_server.py

A small local-only web server for the claude-journal system. It does two
things that the plain `python3 -m http.server` cannot:

1. Serves the journal directory's files normally (devlog.html, DEVLOG.md,
   new-entry.html, etc.) — same as before.
2. Accepts a POST request from new-entry.html and appends a properly
   formatted entry directly to DEVLOG.md on disk.

This server is intended for LOCAL USE ONLY. It listens on 127.0.0.1
(localhost) by default, which means it is not reachable from other
machines or the internet — only from the same computer it's running on.
Do not change the bind address to 0.0.0.0 or your real IP unless you
specifically understand the security implications of exposing a
file-writing server to a network.

Usage:
    python3 journal_server.py
    # then open http://localhost:4242/devlog.html
    # or http://localhost:4242/new-entry.html

Writing behavior:
- Appends the new entry directly below the header block in DEVLOG.md
  (newest entries at the top, matching the existing convention).
- Does NOT run git commands. Writing the file and committing it to git
  remain separate, deliberate steps — you still choose when to commit.
- Re-validates and re-sanitizes the incoming data server-side, even
  though new-entry.html already does this in the browser. Browser-side
  validation can always be bypassed (e.g. by a direct request to the
  server), so the server is the actual safety boundary, not the page.
"""

import http.server
import json
import re
import socketserver
from pathlib import Path

HOST = "127.0.0.1"
PORT = 4242
JOURNAL_DIR = Path(__file__).resolve().parent
DEVLOG_PATH = JOURNAL_DIR / "DEVLOG.md"

ALLOWED_TAGS = {"Technical", "Process", "Story"}
MAX_FIELD_LENGTHS = {
    "project": 100,
    "title": 120,
    "what": 2000,
    "obstacles": 2000,
    "learned": 2000,
    "outcome": 1000,
    "commits": 600,
}


def escape_for_markdown(text: str) -> str:
    """Escape characters that have special meaning in HTML/markdown
    rendering, so user-typed text can never break devlog.html or the
    file's structure."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def strip_divider_lines(text: str) -> str:
    """Prevent a line that is only '---' from appearing inside body text,
    since that exact sequence is used as the entry separator and would
    fracture one entry into two if left unescaped."""
    lines = text.split("\n")
    fixed = ["\\-\\-\\-" if line.strip() == "---" else line for line in lines]
    return "\n".join(fixed)


def sanitize(text: str) -> str:
    return strip_divider_lines(escape_for_markdown(text.strip()))


def validate_date(date_str: str) -> bool:
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str))


def build_entry(data: dict) -> str:
    """Build the markdown block for one entry, matching the existing
    DEVLOG.md format exactly."""
    date = data["date"]
    title = sanitize(data["title"])
    project = sanitize(data["project"])
    tags = " ".join(f"[{t}]" for t in data["tags"])

    lines = [f"## {date} — {title}", ""]
    lines.append(f"**Project:** {project}")
    lines.append(f"**Tags:** {tags}")
    lines.append("")
    lines.append("**What happened:**")
    lines.append(sanitize(data["what"]))
    lines.append("")

    if data.get("obstacles"):
        lines.append("**Obstacles hit:**")
        lines.append(sanitize(data["obstacles"]))
        lines.append("")

    if data.get("learned"):
        lines.append("**What was learned:**")
        lines.append(sanitize(data["learned"]))
        lines.append("")

    lines.append("**Outcome:**")
    lines.append(sanitize(data["outcome"]))
    lines.append("")

    if data.get("commits"):
        lines.append("**Related commits:**")
        lines.append(sanitize(data["commits"]))
        lines.append("")

    lines.append("---")
    lines.append("")

    return "\n".join(lines)


def insert_entry_at_top(entry_text: str) -> None:
    """Insert the new entry directly below the file's header block
    (anything before the first '## ' heading), above existing entries.
    If DEVLOG.md doesn't exist yet, create it with a minimal header."""
    if not DEVLOG_PATH.exists():
        header = "# Development & Journal Log\n\n"
        DEVLOG_PATH.write_text(header + entry_text, encoding="utf-8")
        return

    original = DEVLOG_PATH.read_text(encoding="utf-8")
    match = re.search(r"^## ", original, re.MULTILINE)

    if match:
        insert_at = match.start()
        new_content = original[:insert_at] + entry_text + "\n" + original[insert_at:]
    else:
        # no existing entries yet — append after whatever header exists
        new_content = original.rstrip() + "\n\n" + entry_text

    DEVLOG_PATH.write_text(new_content, encoding="utf-8")


class JournalRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(JOURNAL_DIR), **kwargs)

    def do_POST(self):
        if self.path != "/api/new-entry":
            self.send_error(404, "Unknown endpoint")
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length)
            data = json.loads(raw_body)
        except (ValueError, json.JSONDecodeError):
            self._send_json(400, {"error": "Malformed request body."})
            return

        errors = self._validate(data)
        if errors:
            self._send_json(400, {"error": " ".join(errors)})
            return

        try:
            entry_text = build_entry(data)
            insert_entry_at_top(entry_text)
        except OSError as e:
            self._send_json(500, {"error": f"Could not write to DEVLOG.md: {e}"})
            return

        self._send_json(200, {"status": "written", "entry": entry_text})

    def _validate(self, data: dict) -> list:
        errors = []

        for field in ("project", "date", "title", "what", "outcome"):
            if not data.get(field) or not str(data.get(field)).strip():
                errors.append(f"Missing required field: {field}.")

        if data.get("date") and not validate_date(data["date"]):
            errors.append("Date must be in YYYY-MM-DD format.")

        for field, max_len in MAX_FIELD_LENGTHS.items():
            value = data.get(field, "")
            if value and len(str(value)) > max_len:
                errors.append(f"Field '{field}' exceeds {max_len} characters.")

        tags = data.get("tags", [])
        if not isinstance(tags, list) or not tags:
            errors.append("At least one tag is required.")
        elif not all(t in ALLOWED_TAGS for t in tags):
            errors.append("Invalid tag value provided.")

        return errors

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Quieter console output — only show errors, not every GET request
        if "POST" in (args[0] if args else ""):
            super().log_message(format, *args)


def main():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((HOST, PORT), JournalRequestHandler) as httpd:
        print(f"Journal server running at http://localhost:{PORT}")
        print(f"Serving and writing within: {JOURNAL_DIR}")
        print("New entry form: http://localhost:4242/new-entry.html")
        print("Log viewer:     http://localhost:4242/devlog.html")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down.")


if __name__ == "__main__":
    main()
