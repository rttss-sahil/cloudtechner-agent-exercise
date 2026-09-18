"""Load runbooks from a directory into structured documents."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

ID_RE = re.compile(r"(?:^|[/_-])(RB|DOC)[-_]?(\d{3})", re.IGNORECASE)


def extract_doc_id(name: str, text: str, index: int) -> str:
    """Prefer an id in the filename (RB-002), then frontmatter 'id:', then position."""
    for candidate in (name, text[:200]):
        m = ID_RE.search(candidate)
        if m:
            return f"{m.group(1).upper()}-{m.group(2)}"
    fm = re.search(r"^(?:id|doc[-_]?id)\s*[:=]\s*(RB[-_]?\d{3})", text, re.I | re.M)
    if fm:
        return fm.group(1).upper().replace("_", "-")
    return f"RB-{index + 1:03d}"


def read_runbooks(dir_path: Path) -> list[dict[str, Any]]:
    """Return [{id, name, text, ...}] for every *.md/*.txt file under dir_path."""
    if not dir_path.exists():
        raise FileNotFoundError(f"Runbooks directory not found: {dir_path}")

    files = sorted(
        p for p in dir_path.rglob("*")
        if p.is_file() and p.suffix.lower() in (".md", ".txt", ".markdown")
    )
    if not files:
        raise FileNotFoundError(f"No .md/.txt files found under {dir_path}")

    docs: list[dict[str, Any]] = []
    for idx, path in enumerate(files):
        text = path.read_text(encoding="utf-8", errors="replace")
        doc_id = extract_doc_id(path.stem, text, idx)
        docs.append({"id": doc_id, "name": path.name, "path": str(path), "text": text})
    return docs