# 📝 Markdown Notes Manager

A fast, elegant, terminal-based Markdown note-taking and management tool designed for developers and power users. It features an interactive Terminal UI (TUI) with colored tables and rendered Markdown, YAML frontmatter metadata, full-text and tag search with context snippets, system editor integration, and HTML exporting.

---

## 📂 Project Structure

```text
markdown-notes-manager/
│
├── README.md             # Project documentation and guide
├── requirements.txt      # Python dependencies (rich, PyYAML, markdown)
├── notes/                # Directory where notes are stored (.md files)
│   └── example.md        # Starter sample note
├── app.py                # Main application script (Interactive TUI + CLI)
├── utils.py              # Core helpers (CRUD, frontmatter parser, stats, export)
└── search.py             # Search engine (full-text, tags, regex, scoring, snippets)
```

---

## ⚡ Quick Start

### 1. Prerequisites
- Python 3.8 or newer installed on your machine.

### 2. Install Dependencies
Run the following command from the project root:

```bash
pip install -r requirements.txt
```

### 3. Launch the Application

#### Interactive Mode (Recommended)
Simply run `app.py` without arguments:

```bash
python app.py
```

This launches the interactive dashboard where you can browse notes, perform searches, view rendered markdown, and manage your notes using numbered menu options.

---

## 💻 CLI Commands & Subcommands

In addition to interactive mode, `app.py` supports direct CLI commands for scripting and rapid use:

### 📋 List Notes
```bash
# List all notes (sorted by last modified by default)
python app.py list

# Sort by title, creation date, or word count
python app.py list --sort title
python app.py list --sort words
python app.py list --sort created
```

### 🔍 Search Notes
```bash
# Full-text search across titles, tags, and content
python app.py search "productivity"

# Search specifically in tags
python app.py search "markdown" --mode tags

# Search specifically in titles
python app.py search "welcome" --mode title

# Filter search results by category
python app.py search "features" --category Guides

# Regular expression search
python app.py search "\b\w+ing\b" --regex
```

### ➕ Create a Note
```bash
# Create a simple note
python app.py create "My Meeting Notes"

# Create with tags and category
python app.py create "System Architecture" --tags "backend,architecture" --category "Engineering"

# Create and open directly in your system editor (Notepad, VS Code, etc.)
python app.py create "Sprint Review" --tags "agile" --edit
```

### 📖 View / Render a Note
```bash
# Render note in terminal with syntax highlighting and tables
python app.py view example.md
python app.py view "Welcome to Markdown Notes Manager"
```

### ✏️ Edit in Default Editor
```bash
# Opens the note in your default editor (VS Code, Notepad, Vim)
python app.py edit example.md
```

### 📊 Vault Statistics
```bash
# Displays note count, total words, reading time, and top tags
python app.py stats
```

### 🌐 Export Note to HTML
```bash
# Export to standalone styled HTML document in exports/ folder
python app.py export example.md

# Specify custom output path
python app.py export example.md --out exports/welcome.html
```

### 🗑️ Delete a Note
```bash
# Safe deletion (with confirmation prompt)
python app.py delete "Sprint Review"

# Force delete without confirmation prompt
python app.py delete "Sprint Review" --force
```

---

## 🏷️ Note Format & YAML Frontmatter

Notes support standard YAML frontmatter headers enclosed within `---` blocks.

```markdown
---
title: My Project Plan
tags: [dev, roadmap, 2026]
category: Work
created: 2026-10-12 10:00:00
updated: 2026-10-12 10:00:00
---

# My Project Plan

Here are the project milestones...
```

If a note doesn't have frontmatter, `app.py` automatically infers the title from the first `# Title` heading or filename.

---

## 🛠️ Modules Breakdown

- **`app.py`**: Handles user interaction, interactive loop, CLI argument parsing, Rich terminal rendering, and menu routing.
- **`utils.py`**: Manages note CRUD operations, YAML frontmatter extraction & serialization, word and reading-time statistics, system editor launching, and HTML exports.
- **`search.py`**: Search algorithm featuring relevance scoring (weighing title, tags, and body matches), tag filtering, regex matching, and contextual snippet extraction with highlighted matches.

---

## 📄 License
MIT License. Free to use and customize.
