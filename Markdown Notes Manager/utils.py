"""
utils.py - Core utilities and helper functions for Markdown Notes Manager.
Handles note loading, parsing, frontmatter extraction, saving, statistics,
editor opening, and HTML exporting.
"""

from __future__ import annotations

import os
import re
import sys
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Optional YAML support with standard library fallback
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Optional Markdown library for HTML export
try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False

DEFAULT_NOTES_DIR = Path("notes")
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


@dataclass
class Note:
    """Represents a Markdown note file with metadata and content."""
    filename: str
    filepath: Path
    title: str
    tags: List[str] = field(default_factory=list)
    category: str = "General"
    created: str = ""
    updated: str = ""
    content: str = ""  # Body content excluding frontmatter
    raw: str = ""      # Full raw file text
    word_count: int = 0
    char_count: int = 0
    reading_time_min: int = 1

    @property
    def file_size(self) -> int:
        """Returns file size in bytes if file exists."""
        if self.filepath.exists():
            return self.filepath.stat().st_size
        return len(self.raw.encode("utf-8"))


def ensure_notes_dir(notes_dir: Path | str = DEFAULT_NOTES_DIR) -> Path:
    """Ensures that the notes storage directory exists."""
    path = Path(notes_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def slugify(text: str) -> str:
    """Converts a title into a safe, filesystem-friendly filename."""
    clean = re.sub(r"[^\w\s-]", "", text.strip().lower())
    clean = re.sub(r"[-\s]+", "-", clean)
    return clean or "untitled-note"


def parse_frontmatter(raw_text: str) -> Tuple[Dict[str, Any], str]:
    """
    Splits markdown file content into frontmatter metadata and markdown body.
    Supports YAML frontmatter delimited by '---'.
    Gracefully falls back to simple regex parsing if PyYAML is not installed.
    """
    match = FRONTMATTER_PATTERN.match(raw_text)
    if not match:
        return {}, raw_text

    yaml_block = match.group(1)
    body = raw_text[match.end():]
    metadata: Dict[str, Any] = {}

    if HAS_YAML:
        try:
            parsed = yaml.safe_load(yaml_block)
            if isinstance(parsed, dict):
                metadata = parsed
        except Exception:
            metadata = {}
    else:
        # Fallback basic key-value parser
        for line in yaml_block.splitlines():
            line = line.strip()
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if val.startswith("[") and val.endswith("]"):
                    # Basic tag list: [tag1, tag2]
                    items = [t.strip().strip("'\"") for t in val[1:-1].split(",") if t.strip()]
                    metadata[key] = items
                else:
                    metadata[key] = val

    return metadata, body


def serialize_frontmatter(metadata: Dict[str, Any], body: str) -> str:
    """Serializes metadata into a YAML frontmatter block prefixed to markdown body."""
    if not metadata:
        return body

    if HAS_YAML:
        yaml_str = yaml.dump(metadata, sort_keys=False, default_flow_style=None)
        return f"---\n{yaml_str}---\n\n{body.lstrip()}"
    else:
        lines = ["---"]
        for k, v in metadata.items():
            if isinstance(v, list):
                joined = ", ".join(str(item) for item in v)
                lines.append(f"{k}: [{joined}]")
            else:
                lines.append(f"{k}: {v}")
        lines.append("---\n")
        return "\n".join(lines) + f"\n{body.lstrip()}"


def calculate_stats(content: str) -> Tuple[int, int, int]:
    """Calculates word count, character count, and estimated reading time in minutes."""
    words = re.findall(r"\b\w+\b", content)
    word_count = len(words)
    char_count = len(content)
    # Average reading speed is ~200 words per minute
    reading_time = max(1, round(word_count / 200)) if word_count > 0 else 0
    return word_count, char_count, reading_time


def extract_title_fallback(body: str, default_title: str) -> str:
    """Extracts the first H1 heading (# Title) from markdown body if no title in frontmatter."""
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return default_title


def load_note(filepath_or_name: Path | str, notes_dir: Path | str = DEFAULT_NOTES_DIR) -> Optional[Note]:
    """Loads and parses a single markdown note file."""
    base_dir = ensure_notes_dir(notes_dir)
    target = Path(filepath_or_name)

    if not target.is_absolute() and not target.exists():
        target = base_dir / target
        if not target.suffix:
            target = target.with_suffix(".md")

    if not target.exists() or not target.is_file():
        return None

    try:
        raw_text = target.read_text(encoding="utf-8")
    except Exception:
        try:
            raw_text = target.read_text(encoding="latin-1")
        except Exception:
            return None

    metadata, body = parse_frontmatter(raw_text)

    # Derive title
    file_stem_title = target.stem.replace("-", " ").replace("_", " ").title()
    title = str(metadata.get("title") or extract_title_fallback(body, file_stem_title))

    # Tags normalization
    raw_tags = metadata.get("tags", [])
    if isinstance(raw_tags, str):
        tags = [t.strip().lstrip("#") for t in raw_tags.split(",") if t.strip()]
    elif isinstance(raw_tags, list):
        tags = [str(t).strip().lstrip("#") for t in raw_tags if str(t).strip()]
    else:
        tags = []

    # Also detect inline hashtags in body (e.g. #tag)
    inline_tags = re.findall(r"(?:^|\s)#([a-zA-Z0-9_-]+)", body)
    for it in inline_tags:
        if it.lower() not in [t.lower() for t in tags]:
            tags.append(it)

    category = str(metadata.get("category", "General"))

    # Timestamps
    stat = target.stat()
    created_time = metadata.get("created")
    if not created_time:
        created_time = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")

    updated_time = metadata.get("updated")
    if not updated_time:
        updated_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

    word_count, char_count, reading_time = calculate_stats(body)

    return Note(
        filename=target.name,
        filepath=target.resolve(),
        title=title,
        tags=tags,
        category=category,
        created=str(created_time),
        updated=str(updated_time),
        content=body.strip(),
        raw=raw_text,
        word_count=word_count,
        char_count=char_count,
        reading_time_min=reading_time,
    )


def list_all_notes(notes_dir: Path | str = DEFAULT_NOTES_DIR, sort_by: str = "updated") -> List[Note]:
    """Returns a list of all markdown notes in the notes directory, sorted by field."""
    base_dir = ensure_notes_dir(notes_dir)
    notes: List[Note] = []

    for file in base_dir.rglob("*.md"):
        if file.is_file():
            note = load_note(file, base_dir)
            if note:
                notes.append(note)

    if sort_by == "title":
        notes.sort(key=lambda n: n.title.lower())
    elif sort_by == "created":
        notes.sort(key=lambda n: n.created, reverse=True)
    elif sort_by == "words":
        notes.sort(key=lambda n: n.word_count, reverse=True)
    else:  # default 'updated'
        notes.sort(key=lambda n: n.updated, reverse=True)

    return notes


def save_note(
    filepath_or_name: Path | str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    notes_dir: Path | str = DEFAULT_NOTES_DIR,
) -> Note:
    """Saves note content and metadata to disk."""
    base_dir = ensure_notes_dir(notes_dir)
    target = Path(filepath_or_name)

    if not target.is_absolute():
        target = base_dir / target
        if not target.suffix:
            target = target.with_suffix(".md")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta = metadata.copy() if metadata else {}

    if "created" not in meta:
        meta["created"] = now_str
    meta["updated"] = now_str

    full_text = serialize_frontmatter(meta, content)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(full_text, encoding="utf-8")

    note = load_note(target, base_dir)
    assert note is not None
    return note


def create_note(
    title: str,
    content: str = "",
    tags: Optional[List[str]] = None,
    category: str = "General",
    filename: Optional[str] = None,
    notes_dir: Path | str = DEFAULT_NOTES_DIR,
) -> Note:
    """Creates a brand new markdown note with frontmatter metadata."""
    base_dir = ensure_notes_dir(notes_dir)
    clean_title = title.strip() or "Untitled Note"

    if not filename:
        slug = slugify(clean_title)
        filename = f"{slug}.md"
        # Avoid collisions
        counter = 1
        test_path = base_dir / filename
        while test_path.exists():
            filename = f"{slug}-{counter}.md"
            test_path = base_dir / filename
            counter += 1

    clean_tags = [t.strip().lstrip("#") for t in (tags or []) if t.strip()]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    metadata = {
        "title": clean_title,
        "tags": clean_tags,
        "category": category.strip() or "General",
        "created": now_str,
        "updated": now_str,
    }

    body = content.strip()
    if not body:
        body = f"# {clean_title}\n\nStart writing your note here..."

    return save_note(filename, body, metadata, notes_dir=base_dir)


def delete_note(filepath_or_name: Path | str, notes_dir: Path | str = DEFAULT_NOTES_DIR) -> bool:
    """Deletes a note file from disk."""
    base_dir = ensure_notes_dir(notes_dir)
    target = Path(filepath_or_name)
    if not target.is_absolute():
        target = base_dir / target
        if not target.suffix:
            target = target.with_suffix(".md")

    if target.exists() and target.is_file():
        target.unlink()
        return True
    return False


def open_in_editor(filepath_or_name: Path | str, notes_dir: Path | str = DEFAULT_NOTES_DIR) -> bool:
    """
    Opens note in the user's default system editor or preferred environment editor.
    Works seamlessly across Windows, macOS, and Linux.
    """
    base_dir = ensure_notes_dir(notes_dir)
    target = Path(filepath_or_name)
    if not target.is_absolute():
        target = base_dir / target
        if not target.suffix:
            target = target.with_suffix(".md")

    if not target.exists():
        return False

    abs_path = str(target.resolve())

    # Check for $EDITOR or $VISUAL environment variables
    env_editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
    if env_editor:
        try:
            subprocess.run([env_editor, abs_path], check=False)
            return True
        except Exception:
            pass

    # Windows specific launch
    if sys.platform == "win32":
        try:
            os.startfile(abs_path)  # type: ignore[attr-defined]
            return True
        except Exception:
            try:
                subprocess.Popen(["notepad.exe", abs_path])
                return True
            except Exception:
                pass
    elif sys.platform == "darwin":
        try:
            subprocess.Popen(["open", abs_path])
            return True
        except Exception:
            pass
    else:
        try:
            subprocess.Popen(["xdg-open", abs_path])
            return True
        except Exception:
            pass

    return False


def get_vault_stats(notes_dir: Path | str = DEFAULT_NOTES_DIR) -> Dict[str, Any]:
    """Gathers summary statistics for all notes in the vault."""
    notes = list_all_notes(notes_dir)
    total_notes = len(notes)
    total_words = sum(n.word_count for n in notes)
    total_chars = sum(n.char_count for n in notes)
    total_reading_time = sum(n.reading_time_min for n in notes)

    tag_freq: Dict[str, int] = {}
    cat_freq: Dict[str, int] = {}

    for n in notes:
        for t in n.tags:
            tag_freq[t] = tag_freq.get(t, 0) + 1
        cat_freq[n.category] = cat_freq.get(n.category, 0) + 1

    sorted_tags = sorted(tag_freq.items(), key=lambda x: x[1], reverse=True)
    sorted_cats = sorted(cat_freq.items(), key=lambda x: x[1], reverse=True)

    return {
        "total_notes": total_notes,
        "total_words": total_words,
        "total_chars": total_chars,
        "total_reading_time": total_reading_time,
        "tags": sorted_tags,
        "categories": sorted_cats,
    }


def export_note_to_html(
    filepath_or_name: Path | str,
    output_path: Optional[Path | str] = None,
    notes_dir: Path | str = DEFAULT_NOTES_DIR,
) -> Optional[Path]:
    """Exports a markdown note to a styled HTML document."""
    note = load_note(filepath_or_name, notes_dir)
    if not note:
        return None

    if HAS_MARKDOWN:
        html_body = markdown.markdown(
            note.content,
            extensions=["extra", "codehilite", "tables", "toc"],
        )
    else:
        # Fallback simple converter
        escaped = note.content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html_body = f"<pre>{escaped}</pre>"

    tags_html = "".join(f'<span class="tag">#{t}</span>' for t in note.tags)
    template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{note.title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            max-width: 820px;
            margin: 40px auto;
            padding: 0 20px;
            color: #24292f;
            background-color: #f6f8fa;
        }}
        .card {{
            background: #ffffff;
            border: 1px solid #d0d7de;
            border-radius: 8px;
            padding: 32px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }}
        .header {{
            border-bottom: 2px solid #eaecef;
            padding-bottom: 16px;
            margin-bottom: 24px;
        }}
        .title {{
            margin-top: 0;
            color: #1f2328;
            font-size: 2rem;
        }}
        .meta {{
            font-size: 0.9rem;
            color: #57609a;
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
            margin-bottom: 12px;
        }}
        .tag {{
            display: inline-block;
            background: #ddf4ff;
            color: #0969da;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            margin-right: 6px;
            font-weight: 500;
        }}
        pre {{
            background: #24292e;
            color: #f6f8fa;
            padding: 16px;
            border-radius: 6px;
            overflow-x: auto;
        }}
        code {{
            background: #eff1f3;
            padding: 2px 4px;
            border-radius: 4px;
            font-family: Consolas, "Courier New", monospace;
        }}
        pre code {{
            background: transparent;
            padding: 0;
            color: inherit;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 16px 0;
        }}
        th, td {{
            border: 1px solid #d0d7de;
            padding: 8px 12px;
            text-align: left;
        }}
        th {{
            background-color: #f6f8fa;
        }}
        blockquote {{
            border-left: 4px solid #0969da;
            margin: 0;
            padding-left: 16px;
            color: #57606a;
            font-style: italic;
        }}
        hr {{
            border: 0;
            height: 1px;
            background: #d0d7de;
            margin: 24px 0;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1 class="title">{note.title}</h1>
            <div class="meta">
                <span>📁 <strong>Category:</strong> {note.category}</span>
                <span>🕒 <strong>Updated:</strong> {note.updated}</span>
                <span>📊 <strong>Words:</strong> {note.word_count}</span>
                <span>⏱️ <strong>Read:</strong> ~{note.reading_time_min} min</span>
            </div>
            <div>{tags_html}</div>
        </div>
        <div class="markdown-body">
            {html_body}
        </div>
    </div>
</body>
</html>
"""
    if output_path is None:
        exports_dir = Path("exports")
        exports_dir.mkdir(parents=True, exist_ok=True)
        out_file = exports_dir / f"{note.filepath.stem}.html"
    else:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

    out_file.write_text(template, encoding="utf-8")
    return out_file
