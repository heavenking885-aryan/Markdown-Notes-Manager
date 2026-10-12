"""
search.py - Search engine for Markdown Notes Manager.
Provides full-text, title, tag, category, and regex search capabilities
with relevance ranking and context snippet extraction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence, Union

from utils import DEFAULT_NOTES_DIR, Note, list_all_notes


@dataclass
class SearchResult:
    """Represents a matched note with relevance scoring and text snippets."""
    note: Note
    score: float
    match_fields: List[str] = field(default_factory=list)
    snippets: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"<SearchResult note='{self.note.title}' score={self.score:.1f} matches={self.match_fields}>"


def extract_snippets(text: str, query: str, context_chars: int = 50, max_snippets: int = 3) -> List[str]:
    """
    Extracts short contextual snippets around query matches in body text.
    Highlights query matches within the snippet text.
    """
    if not query.strip() or not text:
        return []

    snippets: List[str] = []
    # Find positions using case-insensitive match
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    matches = list(pattern.finditer(text))

    for m in matches[:max_snippets]:
        start = max(0, m.start() - context_chars)
        end = min(len(text), m.end() + context_chars)
        snippet = text[start:end].replace("\n", " ").strip()

        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""
        snippets.append(f"{prefix}{snippet}{suffix}")

    return snippets


def extract_regex_snippets(text: str, pattern: re.Pattern, context_chars: int = 50, max_snippets: int = 3) -> List[str]:
    """Extracts snippets matching a compiled regular expression."""
    snippets: List[str] = []
    matches = list(pattern.finditer(text))

    for m in matches[:max_snippets]:
        start = max(0, m.start() - context_chars)
        end = min(len(text), m.end() + context_chars)
        snippet = text[start:end].replace("\n", " ").strip()

        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""
        snippets.append(f"{prefix}{snippet}{suffix}")

    return snippets


def search_notes(
    query: str,
    notes_or_dir: Union[Sequence[Note], Path, str] = DEFAULT_NOTES_DIR,
    search_mode: str = "all",
    category_filter: Optional[str] = None,
    is_regex: bool = False,
) -> List[SearchResult]:
    """
    Searches notes based on a query string and optional filters.

    Parameters:
    - query: Search string or regex pattern
    - notes_or_dir: Sequence of loaded Note objects or directory path
    - search_mode: 'all', 'title', 'tags', 'content'
    - category_filter: Optional category name to restrict results to
    - is_regex: If True, treats query as a regular expression

    Returns:
    - List of SearchResult objects sorted by relevance score descending.
    """
    if not query.strip():
        return []

    # Resolve note collection
    if isinstance(notes_or_dir, (str, Path)):
        notes = list_all_notes(notes_or_dir)
    else:
        notes = list(notes_or_dir)

    # Optional category filter
    if category_filter:
        cat_clean = category_filter.strip().lower()
        notes = [n for n in notes if n.category.strip().lower() == cat_clean]

    results: List[SearchResult] = []
    query_str = query.strip()

    # Compile regex if requested or default case-insensitive regex pattern
    if is_regex:
        try:
            pattern = re.compile(query_str, re.IGNORECASE)
        except re.error:
            # Fallback to literal search if regex is malformed
            pattern = re.compile(re.escape(query_str), re.IGNORECASE)
    else:
        pattern = re.compile(re.escape(query_str), re.IGNORECASE)

    q_lower = query_str.lower().lstrip("#")

    for note in notes:
        score = 0.0
        match_fields: List[str] = []
        snippets: List[str] = []

        # 1. Search in Title
        if search_mode in ("all", "title"):
            title_lower = note.title.lower()
            if q_lower == title_lower:
                score += 25.0
                match_fields.append("exact title")
            elif pattern.search(note.title):
                score += 12.0
                match_fields.append("title")

        # 2. Search in Tags
        if search_mode in ("all", "tags"):
            tag_matches = [t for t in note.tags if pattern.search(t) or q_lower == t.lower()]
            if tag_matches:
                score += 10.0 * len(tag_matches)
                match_fields.append(f"tags ({', '.join(tag_matches)})")

        # 3. Search in Category
        if search_mode == "all":
            if pattern.search(note.category):
                score += 5.0
                match_fields.append(f"category ({note.category})")

        # 4. Search in Content Body
        if search_mode in ("all", "content"):
            content_matches = list(pattern.finditer(note.content))
            if content_matches:
                count = len(content_matches)
                # Diminishing score boost for high occurrences
                score += min(count * 2.0, 20.0)
                match_fields.append(f"content ({count} match{'es' if count > 1 else ''})")

                if is_regex:
                    snippets = extract_regex_snippets(note.content, pattern)
                else:
                    snippets = extract_snippets(note.content, query_str)

        if score > 0:
            results.append(
                SearchResult(
                    note=note,
                    score=score,
                    match_fields=match_fields,
                    snippets=snippets,
                )
            )

    # Sort results by score descending
    results.sort(key=lambda r: r.score, reverse=True)
    return results


def find_by_tag(tag: str, notes_or_dir: Union[Sequence[Note], Path, str] = DEFAULT_NOTES_DIR) -> List[Note]:
    """Helper to quickly filter all notes containing a given tag."""
    clean_tag = tag.strip().lstrip("#").lower()
    if isinstance(notes_or_dir, (str, Path)):
        notes = list_all_notes(notes_or_dir)
    else:
        notes = list(notes_or_dir)

    return [n for n in notes if any(t.lower() == clean_tag for t in n.tags)]
