#!/usr/bin/env python3
"""Spelling and grammar checker.

Usage:
    python spellcheck.py "Some text to check"
    python spellcheck.py -f document.txt
    python spellcheck.py                  # interactive mode

Works on Windows, macOS, and Linux. Requires Python 3.8+.
Optional: `pip install language-tool-python` enables grammar checking
(needs Java). Without it, spelling checking still works.
"""

import argparse
import os
import sys
from pathlib import Path

# Allow running from a source checkout without installation
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from spellcheck_core.speller import SpellCheckerFacade
except ModuleNotFoundError:  # installed as a package
    try:
        from spellcheck.speller import SpellCheckerFacade
    except ModuleNotFoundError:
        SpellCheckerFacade = None

try:
    import language_tool_python

    LANGUAGETOOL_AVAILABLE = True
except ImportError:
    LANGUAGETOOL_AVAILABLE = False

try:
    from spellcheck_core.grammar import LT_CONFIG
except ModuleNotFoundError:
    LT_CONFIG = {
        "maxTextLength": 500_000,
        "maxTextHardLength": 500_000,
        "maxCheckTimeMillis": 60_000,
        "maxSpellingSuggestions": 5,
        "requestLimit": 5_000,
        "requestLimitPeriodInSeconds": 86_400,
    }

if sys.version_info < (3, 8):
    sys.exit("spellcheck requires Python 3.8 or newer.")


# --------------------------------------------------------------------------
# Windows console fix: make UTF-8 output work on cp1252 terminals.
# --------------------------------------------------------------------------
if os.name == "nt":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except AttributeError:  # Python < 3.7
        pass


spell_checker = SpellCheckerFacade() if SpellCheckerFacade else None
_grammar_tool = None


def grammar_tool():
    """Lazily start a local LanguageTool server with generous limits."""
    global _grammar_tool
    if not LANGUAGETOOL_AVAILABLE:
        return None
    if _grammar_tool is None:
        try:
            _grammar_tool = language_tool_python.LanguageTool(
                "en-US", config=LT_CONFIG
            )
        except Exception as exc:  # noqa: BLE001 - report anything that fails
            msg = str(exc)
            if "java" in msg.lower() or "jre" in msg.lower() or "JDK" in msg:
                msg += "\n  [hint] Grammar checking needs Java 8+ installed."
                msg += "  Download from https://adoptium.net"
            elif "download" in msg.lower() or "network" in msg.lower():
                msg += "\n  [hint] First run needs internet to download the"
                msg += " LanguageTool server (~260 MB). It is cached after that."
            print(f"[warning] Grammar checking unavailable: {msg}", file=sys.stderr)
            _grammar_tool = False
    return _grammar_tool or None


def check_spelling(text):
    """Return a list of misspelled words with position and suggestions."""
    if spell_checker is None:
        print("[error] 'pyspellchecker' is not installed.", file=sys.stderr)
        print("        Run: pip install pyspellchecker", file=sys.stderr)
        return []
    return spell_checker.check(text)


def check_grammar(text):
    """Return LanguageTool matches (grammar, style, punctuation)."""
    tool = grammar_tool()
    if not tool:
        return []
    return tool.check(text)


def report(text, use_color=None, no_grammar=False):
    """Print a combined spelling + grammar report for the text."""
    use_color = _use_color(use_color)
    print("=" * 60)
    print(f"TEXT: {text.strip()!r}")
    print("=" * 60)

    # Spelling
    miss = check_spelling(text)
    print(f"\nSPELLING: {len(miss)} issue(s)")
    for item in miss:
        suggestions = ", ".join(item["suggestions"]) or "no suggestions"
        pos = c("yellow", f"pos {item['position']}", use_color)
        print(f"  - {item['word']!r} ({pos}) -> {suggestions}")

    # Grammar
    matches = [] if no_grammar else check_grammar(text)
    print(f"\nGRAMMAR / STYLE: {len(matches)} issue(s)")
    for m in matches:
        excerpt = text[m.offset : m.offset + m.error_length]
        typ = c("cyan", m.rule_issue_type, use_color)
        pos = c("yellow", f"pos {m.offset}", use_color)
        print(f"  [{typ}] {excerpt!r} ({pos})")
        print(f"      {m.message}")
        if m.replacements:
            best = c("green", m.replacements[0], use_color)
            rest = m.replacements[1:3]
            print(f"      Suggestion: {best}" + (f", {', '.join(rest)}" if rest else ""))

    if not miss and not matches:
        print("\nNo issues found - text looks good!")


# --------------------------------------------------------------------------
# Minimal ANSI colouring, auto-disabled on dumb terminals / old Windows.
# --------------------------------------------------------------------------
_COLORS = {
    "red": "\033[91m", "green": "\033[92m", "yellow": "\033[93m",
    "cyan": "\033[96m", "reset": "\033[0m",
}


def c(name, text, use_color):
    if not use_color:
        return text
    return f"{_COLORS[name]}{text}{_COLORS['reset']}"


def _use_color(flag):
    if flag is not None:
        return flag
    if os.name == "nt":
        return os.environ.get("ANSICON") or "WT_SESSION" in os.environ
    return sys.stdout.isatty()


def interactive():
    print("Interactive spelling & grammar checker. Type text (or 'quit').")
    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text.lower() in {"quit", "exit", "q"}:
            break
        if text:
            report(text)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="spellcheck",
        description="Spelling and grammar checker (offline, cross-platform).",
    )
    parser.add_argument("text", nargs="?", help="text to check")
    parser.add_argument("-f", "--file", help="file to check (UTF-8 or locale encoding)")
    parser.add_argument("--no-color", action="store_true", help="disable coloured output")
    parser.add_argument("--color", action="store_true", help="force coloured output")
    parser.add_argument("--no-grammar", action="store_true", help="skip grammar check")
    args = parser.parse_args(argv)

    use_color = False if args.no_color else (True if args.color else None)

    if args.file:
        path = Path(args.file)
        if not path.is_file():
            parser.error(f"file not found: {path}")
        # utf-8 first, fall back to the platform default (cp1252 on Windows)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(errors="replace")
        report(text, use_color=use_color, no_grammar=args.no_grammar)
    elif args.text:
        report(args.text, use_color=use_color, no_grammar=args.no_grammar)
    else:
        interactive()


if __name__ == "__main__":
    main()
