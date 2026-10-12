---
title: Welcome to Markdown Notes Manager
tags: [getting-started, productivity, markdown]
category: Guides
created: 2026-10-12 10:00:00
updated: 2026-10-12 10:00:00
status: published
---

# Welcome to Markdown Notes Manager 🚀

A lightweight, terminal-based Markdown note-taking and management tool designed for speed, clarity, and ease of use.

---

## 📌 Features Overview

- **Full Markdown Support**: Headings, lists, tables, blockquotes, and code snippets.
- **YAML Frontmatter**: Organize notes with metadata like `tags`, `category`, and timestamps.
- **Powerful Search**: Filter by keywords, tags, or perform regex searches across all notes.
- **System Editor Integration**: Open and edit any note in your favorite editor (VS Code, Notepad, Vim).
- **Exporting**: Convert any note to standalone HTML.

---

## 🎯 Quick Checklist

- [x] Install dependencies with `pip install -r requirements.txt`
- [x] Run `python app.py` to launch interactive mode
- [ ] Create your first custom note
- [ ] Try searching with keywords or tags (`#productivity`)
- [ ] Export a note to HTML

---

## 💻 Sample Code Block

```python
from utils import load_note
from search import search_notes

# Load and search notes easily
results = search_notes("productivity")
for res in results:
    print(f"Found match in: {res['title']}")
```

---

## 📊 Summary Table

| Feature | Shortcut / Command | Description |
| :--- | :--- | :--- |
| **List Notes** | `1` or `python app.py list` | Browse all saved notes with stats |
| **Search** | `2` or `python app.py search <term>` | Query titles, tags, and content |
| **New Note** | `3` or `python app.py create <title>` | Create a note with automatic frontmatter |
| **View Note** | `4` or `python app.py view <name>` | Render formatted Markdown in terminal |
| **Edit Note** | `5` or `python app.py edit <name>` | Launch your preferred editor |

> *"The palest ink is better than the best memory."* — Chinese Proverb
