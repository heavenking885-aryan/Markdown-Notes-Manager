"""
app.py - Main entry point for Markdown Notes Manager.
Provides both an interactive terminal interface (TUI) and direct CLI subcommands.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

# Ensure UTF-8 output on Windows terminals to avoid cp1252 charmap UnicodeEncodeErrors
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Attempt to load rich for enhanced terminal aesthetics
try:
    from rich import print as rprint
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.prompt import Confirm, Prompt
    from rich.table import Table
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from search import find_by_tag, search_notes
from utils import (
    DEFAULT_NOTES_DIR,
    Note,
    create_note,
    delete_note,
    ensure_notes_dir,
    export_note_to_html,
    get_vault_stats,
    list_all_notes,
    load_note,
    open_in_editor,
)

# legacy_windows=False prevents Rich from delegating to Windows Legacy cp1252 renderer
console = Console(legacy_windows=False) if HAS_RICH else None


def safe_input(prompt_text: str = "") -> str:
    """Safely reads input from user, preventing crashes on EOF or Ctrl+C."""
    try:
        return input(prompt_text).strip()
    except (KeyboardInterrupt, EOFError):
        return ""


def print_banner() -> None:
    """Displays application banner and status."""
    if HAS_RICH and console:
        title_text = Text(" Markdown Notes Manager ", style="bold white on blue")
        subtitle = Text("Fast, organized, and beautiful note-taking in your terminal\n", style="dim")
        console.print(Panel(Text.assemble(title_text, "\n", subtitle), border_style="blue", expand=False))
    else:
        print("=" * 60)
        print("       MARKDOWN NOTES MANAGER")
        print("   Fast & organized terminal note management")
        print("=" * 60)


def display_notes_table(notes: List[Note], title: str = "Saved Notes") -> None:
    """Renders notes in a formatted table."""
    if not notes:
        if HAS_RICH and console:
            console.print("[yellow]No notes found in vault.[/yellow]")
        else:
            print("No notes found in vault.")
        return

    if HAS_RICH and console:
        table = Table(title=title, header_style="bold cyan", border_style="blue")
        table.add_column("#", style="dim", width=4, justify="right")
        table.add_column("Title", style="bold green", min_width=25)
        table.add_column("Category", style="magenta")
        table.add_column("Tags", style="cyan")
        table.add_column("Words", justify="right", style="yellow")
        table.add_column("Reading Time", justify="right")
        table.add_column("Last Modified", style="dim")

        for idx, note in enumerate(notes, 1):
            tags_str = ", ".join(f"#{t}" for t in note.tags) if note.tags else "-"
            table.add_row(
                str(idx),
                note.title,
                note.category,
                tags_str,
                str(note.word_count),
                f"~{note.reading_time_min}m",
                note.updated,
            )
        console.print(table)
    else:
        print(f"\n--- {title} ---")
        for idx, note in enumerate(notes, 1):
            tags_str = f"[{', '.join(note.tags)}]" if note.tags else "[]"
            print(f"[{idx}] {note.title} (Category: {note.category}, Tags: {tags_str}, Words: {note.word_count}, Updated: {note.updated})")


def render_note_view(note: Note) -> None:
    """Renders formatted note contents and metadata."""
    if HAS_RICH and console:
        # Header Info Panel
        tags_str = " ".join(f"[bold cyan]#{t}[/]" for t in note.tags) if note.tags else "[dim]None[/]"
        meta_info = (
            f"[bold]Category:[/] {note.category}   |   "
            f"[bold]Words:[/] {note.word_count}   |   "
            f"[bold]Reading Time:[/] ~{note.reading_time_min} min\n"
            f"[bold]Created:[/] {note.created}   |   "
            f"[bold]Updated:[/] {note.updated}\n"
            f"[bold]File:[/] {note.filepath.name}   |   "
            f"[bold]Tags:[/] {tags_str}"
        )
        console.print(Panel(meta_info, title=f"[bold green]{note.title}[/]", border_style="cyan"))

        # Render Markdown body
        console.print("\n")
        try:
            md = Markdown(note.content, code_theme="monokai")
            console.print(md)
        except Exception:
            console.print(note.content)
        console.print("\n" + "─" * 60)
    else:
        print("\n" + "=" * 60)
        print(f"TITLE: {note.title}")
        print(f"CATEGORY: {note.category} | TAGS: {', '.join(note.tags)}")
        print(f"MODIFIED: {note.updated} | WORDS: {note.word_count}")
        print("=" * 60 + "\n")
        print(note.content)
        print("\n" + "-" * 60)


def display_stats() -> None:
    """Displays vault statistics."""
    stats = get_vault_stats()
    if HAS_RICH and console:
        table = Table(title="📊 Vault Statistics", border_style="green")
        table.add_column("Metric", style="bold cyan")
        table.add_column("Value", style="bold yellow")

        table.add_row("Total Notes", str(stats["total_notes"]))
        table.add_row("Total Words", str(stats["total_words"]))
        table.add_row("Total Characters", str(stats["total_chars"]))
        table.add_row("Estimated Total Reading Time", f"~{stats['total_reading_time']} minutes")
        console.print(table)

        if stats["tags"]:
            tag_table = Table(title="🏷️ Top Tags", border_style="cyan")
            tag_table.add_column("Tag", style="cyan")
            tag_table.add_column("Frequency", style="yellow", justify="right")
            for tag, count in stats["tags"][:10]:
                tag_table.add_row(f"#{tag}", str(count))
            console.print(tag_table)

        if stats["categories"]:
            cat_table = Table(title="📁 Categories", border_style="magenta")
            cat_table.add_column("Category", style="magenta")
            cat_table.add_column("Notes Count", style="yellow", justify="right")
            for cat, count in stats["categories"]:
                cat_table.add_row(cat, str(count))
            console.print(cat_table)
    else:
        print("\n--- Vault Statistics ---")
        print(f"Total Notes: {stats['total_notes']}")
        print(f"Total Words: {stats['total_words']}")
        print(f"Total Reading Time: ~{stats['total_reading_time']} min")
        print("Tags:", ", ".join(f"#{t} ({c})" for t, c in stats["tags"][:8]))
        print("Categories:", ", ".join(f"{c} ({cnt})" for c, cnt in stats["categories"]))


def select_note_interactively(notes: List[Note], prompt_text: str = "Select a note number") -> Optional[Note]:
    """Helper to select a note from list by numerical index."""
    if not notes:
        return None

    display_notes_table(notes)
    while True:
        choice = safe_input(f"\n{prompt_text} (1-{len(notes)}, or 'c' to cancel): ")
        if choice.lower() in ("c", "cancel", "q", "quit", ""):
            return None
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(notes):
                return notes[idx - 1]
            print(f"Invalid index. Please enter a number between 1 and {len(notes)}.")
        else:
            print("Please enter a valid number or 'c' to cancel.")


# =====================================================================
# Interactive Menus & Handlers
# =====================================================================

def handle_create_note_interactive() -> None:
    """Interactively creates a new note."""
    if HAS_RICH and console:
        console.print("\n[bold green]➕ Create a New Note[/]")
    else:
        print("\n--- Create a New Note ---")

    title = safe_input("Enter Note Title: ")
    if not title:
        print("Creation cancelled: Title cannot be empty.")
        return

    category = safe_input("Enter Category [General]: ") or "General"
    tags_input = safe_input("Enter Tags (comma separated, e.g. dev, ideas): ")
    tags = [t.strip().lstrip("#") for t in tags_input.split(",") if t.strip()]

    initial_content = safe_input("Enter initial content (or leave blank to launch editor): ")

    note = create_note(title=title, content=initial_content, tags=tags, category=category)

    if HAS_RICH and console:
        console.print(f"[bold green]✔ Note '{note.title}' created successfully![/] ([dim]{note.filename}[/])")
    else:
        print(f"Note '{note.title}' created successfully at {note.filename}")

    # Prompt to open in editor
    open_now = safe_input("Open in system editor now? (y/n) [y]: ").lower()
    if open_now in ("", "y", "yes"):
        open_in_editor(note.filepath)


def handle_search_interactive() -> None:
    """Interactively queries notes with full-text search and snippets."""
    query = safe_input("\nEnter search query (or tag like #productivity): ")
    if not query:
        return

    # Check if query is tag specific
    search_mode = "all"
    if query.startswith("#"):
        search_mode = "tags"
        query = query[1:]

    results = search_notes(query, search_mode=search_mode)

    if not results:
        if HAS_RICH and console:
            console.print(f"[yellow]No matches found for '{query}'.[/yellow]")
        else:
            print(f"No matches found for '{query}'.")
        return

    if HAS_RICH and console:
        console.print(f"\n[bold green]Found {len(results)} match(es) for '{query}':[/]\n")
        table = Table(border_style="cyan")
        table.add_column("#", width=4, justify="right")
        table.add_column("Title", style="bold green", min_width=20)
        table.add_column("Matched In", style="magenta")
        table.add_column("Relevance Score", justify="right", style="yellow")
        table.add_column("Context Snippet", style="dim")

        for idx, res in enumerate(results, 1):
            snippet_str = res.snippets[0] if res.snippets else "-"
            table.add_row(
                str(idx),
                res.note.title,
                ", ".join(res.match_fields),
                f"{res.score:.1f}",
                snippet_str,
            )
        console.print(table)
    else:
        print(f"\nFound {len(results)} matches for '{query}':")
        for idx, res in enumerate(results, 1):
            snippet_str = f" | Snippet: {res.snippets[0]}" if res.snippets else ""
            print(f"[{idx}] {res.note.title} (Matches: {', '.join(res.match_fields)}){snippet_str}")

    view_choice = safe_input("\nView a note from search results? (Enter number, or press Enter to skip): ")
    if view_choice.isdigit():
        idx = int(view_choice)
        if 1 <= idx <= len(results):
            handle_view_note(results[idx - 1].note)


def handle_view_note(note: Optional[Note] = None) -> None:
    """Views a note with interactive actions (Edit, Export, Delete)."""
    if note is None:
        notes = list_all_notes()
        note = select_note_interactively(notes, "Select note to view")
        if not note:
            return

    render_note_view(note)

    # Sub-menu for actions on this note
    print("\nActions: [e] Edit | [x] Export HTML | [d] Delete | [Enter] Back to Menu")
    action = safe_input("Select action: ").lower()
    if action in ("e", "edit"):
        open_in_editor(note.filepath)
        print("Opened in system editor.")
    elif action in ("x", "export"):
        out = export_note_to_html(note.filepath)
        if out:
            print(f"Exported successfully to: {out.resolve()}")
    elif action in ("d", "delete"):
        confirm = safe_input(f"Are you sure you want to delete '{note.title}'? (y/n): ").lower()
        if confirm in ("y", "yes"):
            delete_note(note.filepath)
            print("Note deleted.")


def handle_edit_note() -> None:
    """Selects and opens a note in the system editor."""
    notes = list_all_notes()
    note = select_note_interactively(notes, "Select note to edit")
    if note:
        open_in_editor(note.filepath)
        if HAS_RICH and console:
            console.print(f"[bold green]Opened '{note.title}' in your editor.[/]")
        else:
            print(f"Opened '{note.title}' in editor.")


def handle_export_note() -> None:
    """Exports a selected note to HTML."""
    notes = list_all_notes()
    note = select_note_interactively(notes, "Select note to export to HTML")
    if note:
        out = export_note_to_html(note.filepath)
        if out:
            if HAS_RICH and console:
                console.print(f"[bold green]✔ Successfully exported to HTML:[/] [cyan]{out.resolve()}[/]")
            else:
                print(f"Successfully exported to HTML: {out.resolve()}")


def handle_delete_note() -> None:
    """Deletes a selected note with confirmation."""
    notes = list_all_notes()
    note = select_note_interactively(notes, "Select note to delete")
    if note:
        confirm = safe_input(f"Are you sure you want to permanently delete '{note.title}'? (y/n): ").lower()
        if confirm in ("y", "yes"):
            if delete_note(note.filepath):
                print(f"Note '{note.title}' has been deleted.")
            else:
                print("Failed to delete note.")


def interactive_loop() -> None:
    """Main interactive menu loop."""
    ensure_notes_dir()

    while True:
        try:
            print_banner()
            notes = list_all_notes()
            stats = get_vault_stats()

            if HAS_RICH and console:
                console.print(
                    f"[dim]Vault:[/dim] [cyan]{DEFAULT_NOTES_DIR.resolve()}[/cyan]  |  "
                    f"[dim]Notes:[/dim] [yellow]{stats['total_notes']}[/yellow]  |  "
                    f"[dim]Total Words:[/dim] [yellow]{stats['total_words']}[/yellow]\n"
                )
                console.print("[bold cyan][1][/] 📋 List Notes")
                console.print("[bold cyan][2][/] 🔍 Search Notes")
                console.print("[bold cyan][3][/] ➕ Create New Note")
                console.print("[bold cyan][4][/] 📖 View / Read Note")
                console.print("[bold cyan][5][/] ✏️  Edit Note in Editor")
                console.print("[bold cyan][6][/] 📊 Vault Statistics")
                console.print("[bold cyan][7][/] 🌐 Export Note to HTML")
                console.print("[bold cyan][8][/] 🗑️  Delete Note")
                console.print("[bold cyan][0][/] 🚪 Exit\n")
            else:
                print(f"Vault: {DEFAULT_NOTES_DIR.resolve()} | Notes: {stats['total_notes']} | Words: {stats['total_words']}\n")
                print("[1] List Notes")
                print("[2] Search Notes")
                print("[3] Create New Note")
                print("[4] View / Read Note")
                print("[5] Edit Note in Editor")
                print("[6] Vault Statistics")
                print("[7] Export Note to HTML")
                print("[8] Delete Note")
                print("[0] Exit\n")

            choice = safe_input("Enter option [0-8]: ")

            if choice == "1":
                display_notes_table(list_all_notes())
                safe_input("\nPress Enter to return to main menu...")
            elif choice == "2":
                handle_search_interactive()
                safe_input("\nPress Enter to return to main menu...")
            elif choice == "3":
                handle_create_note_interactive()
                safe_input("\nPress Enter to return to main menu...")
            elif choice == "4":
                handle_view_note()
            elif choice == "5":
                handle_edit_note()
                safe_input("\nPress Enter to return to main menu...")
            elif choice == "6":
                display_stats()
                safe_input("\nPress Enter to return to main menu...")
            elif choice == "7":
                handle_export_note()
                safe_input("\nPress Enter to return to main menu...")
            elif choice == "8":
                handle_delete_note()
                safe_input("\nPress Enter to return to main menu...")
            elif choice in ("0", "q", "exit", "quit"):
                print("Goodbye!")
                break
            else:
                if choice:
                    print("Invalid option. Please enter a number between 0 and 8.")
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break


# =====================================================================
# Command Line Interface (CLI) Subcommands
# =====================================================================

def build_parser() -> argparse.ArgumentParser:
    """Builds CLI argument parser for non-interactive command line calls."""
    parser = argparse.ArgumentParser(
        prog="markdown-notes",
        description="Markdown Notes Manager - Organize, search, and view Markdown notes.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # list
    p_list = subparsers.add_parser("list", help="List all notes")
    p_list.add_argument("--sort", choices=["updated", "created", "title", "words"], default="updated", help="Sort order")

    # search
    p_search = subparsers.add_parser("search", help="Search notes")
    p_search.add_argument("query", help="Search query string")
    p_search.add_argument("--mode", choices=["all", "title", "tags", "content"], default="all", help="Search mode")
    p_search.add_argument("--category", help="Filter by category")
    p_search.add_argument("--regex", action="store_true", help="Treat query as regular expression")

    # view
    p_view = subparsers.add_parser("view", help="View a note")
    p_view.add_argument("name", help="Note title, filename, or partial match")

    # create
    p_create = subparsers.add_parser("create", help="Create a new note")
    p_create.add_argument("title", help="Note title")
    p_create.add_argument("--category", default="General", help="Category name")
    p_create.add_argument("--tags", help="Comma-separated tags (e.g. 'work,ideas')")
    p_create.add_argument("--content", default="", help="Initial content")
    p_create.add_argument("--edit", action="store_true", help="Immediately open in system editor")

    # edit
    p_edit = subparsers.add_parser("edit", help="Open a note in the system editor")
    p_edit.add_argument("name", help="Note title or filename")

    # stats
    subparsers.add_parser("stats", help="Display vault statistics")

    # export
    p_export = subparsers.add_parser("export", help="Export a note to HTML")
    p_export.add_argument("name", help="Note title or filename")
    p_export.add_argument("--out", help="Custom output file path")

    # delete
    p_delete = subparsers.add_parser("delete", help="Delete a note")
    p_delete.add_argument("name", help="Note title or filename")
    p_delete.add_argument("--force", "-f", action="store_true", help="Delete without confirmation")

    return parser


def find_note_by_arg(name: str) -> Optional[Note]:
    """Finds a note matching by exact filename, stem, or title."""
    target = load_note(name)
    if target:
        return target

    # Search through all notes for title/stem match
    notes = list_all_notes()
    name_clean = name.strip().lower()
    for n in notes:
        if n.filename.lower() == name_clean or n.filepath.stem.lower() == name_clean or n.title.lower() == name_clean:
            return n

    # Partial title match
    for n in notes:
        if name_clean in n.title.lower():
            return n

    return None


def run_cli() -> None:
    """Handles command-line arguments and subcommands."""
    parser = build_parser()
    args = parser.parse_args()

    # If no subcommand passed, start interactive loop
    if not args.subcommand:
        interactive_loop()
        return

    ensure_notes_dir()

    if args.subcommand == "list":
        notes = list_all_notes(sort_by=args.sort)
        display_notes_table(notes, title=f"Notes (Sorted by {args.sort})")

    elif args.subcommand == "search":
        results = search_notes(
            query=args.query,
            search_mode=args.mode,
            category_filter=args.category,
            is_regex=args.regex,
        )
        if not results:
            print(f"No results found for query '{args.query}'.")
            return

        if HAS_RICH and console:
            console.print(f"\n[bold green]Found {len(results)} match(es) for '{args.query}':[/]\n")
            table = Table(border_style="cyan")
            table.add_column("Title", style="bold green")
            table.add_column("Matched Fields", style="magenta")
            table.add_column("Score", justify="right", style="yellow")
            table.add_column("Snippet", style="dim")
            for r in results:
                table.add_row(r.note.title, ", ".join(r.match_fields), f"{r.score:.1f}", r.snippets[0] if r.snippets else "-")
            console.print(table)
        else:
            for r in results:
                print(f"- {r.note.title} (Matches: {', '.join(r.match_fields)})")
                if r.snippets:
                    print(f"  Snippet: {r.snippets[0]}")

    elif args.subcommand == "view":
        note = find_note_by_arg(args.name)
        if not note:
            print(f"Error: Note matching '{args.name}' not found.")
            sys.exit(1)
        render_note_view(note)

    elif args.subcommand == "create":
        tags = [t.strip().lstrip("#") for t in args.tags.split(",")] if args.tags else []
        note = create_note(
            title=args.title,
            content=args.content,
            tags=tags,
            category=args.category,
        )
        print(f"Created note '{note.title}' ({note.filename})")
        if args.edit:
            open_in_editor(note.filepath)

    elif args.subcommand == "edit":
        note = find_note_by_arg(args.name)
        if not note:
            print(f"Error: Note matching '{args.name}' not found.")
            sys.exit(1)
        open_in_editor(note.filepath)
        print(f"Opened '{note.title}' in editor.")

    elif args.subcommand == "stats":
        display_stats()

    elif args.subcommand == "export":
        note = find_note_by_arg(args.name)
        if not note:
            print(f"Error: Note matching '{args.name}' not found.")
            sys.exit(1)
        out = export_note_to_html(note.filepath, output_path=args.out)
        if out:
            print(f"Exported note to: {out.resolve()}")

    elif args.subcommand == "delete":
        note = find_note_by_arg(args.name)
        if not note:
            print(f"Error: Note matching '{args.name}' not found.")
            sys.exit(1)
        if not args.force:
            confirm = safe_input(f"Are you sure you want to delete '{note.title}'? (y/n): ").lower()
            if confirm not in ("y", "yes"):
                print("Delete cancelled.")
                return
        if delete_note(note.filepath):
            print(f"Deleted '{note.title}'.")
        else:
            print(f"Failed to delete note.")


if __name__ == "__main__":
    run_cli()
