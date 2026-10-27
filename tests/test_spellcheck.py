"""Tests. Spelling tests always run; grammar tests skip if no Java/LanguageTool."""

import subprocess
import sys
from pathlib import Path

import pytest

# Make the src/ package importable when running from a checkout
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

REPO = Path(__file__).parent.parent
SCRIPT = REPO / "spellcheck.py"


# ---------------------------------------------------------------------------
# Core spelling logic
# ---------------------------------------------------------------------------

def test_speller_detects_misspelling():
    from spellcheck_core.speller import SpellCheckerFacade

    checker = SpellCheckerFacade()
    issues = checker.check("I ate a apel yesterday")
    words = [i["word"] for i in issues]
    assert "apel" in words
    assert "yesterday" not in words


def test_speller_suggestions_present():
    from spellcheck_core.speller import SpellCheckerFacade

    checker = SpellCheckerFacade()
    issues = checker.check("yesturday")
    assert issues[0]["suggestions"]


def test_config_values():
    from spellcheck_core.grammar import LT_CONFIG

    assert LT_CONFIG["maxTextLength"] >= 500_000
    assert LT_CONFIG["requestLimit"] >= 1_000


# ---------------------------------------------------------------------------
# CLI behaviour (works on every OS, no Java needed)
# ---------------------------------------------------------------------------

def _run_cli(*args):
    # Explicit encoding: on Windows the parent would otherwise decode the
    # child's UTF-8 output using the legacy cp1252 locale encoding.
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=REPO, timeout=300,
    )


def test_cli_reports_spelling(tmp_path):
    result = _run_cli("I ate a apel yesturday")
    assert result.returncode == 0
    assert "SPELLING" in result.stdout
    assert "apel" in result.stdout


def test_cli_file_mode(tmp_path):
    f = tmp_path / "doc.txt"
    f.write_text("I ate a apel.", encoding="utf-8")
    result = _run_cli("-f", str(f))
    assert result.returncode == 0
    assert "apel" in result.stdout


def test_cli_missing_file_errors_cleanly():
    result = _run_cli("-f", "does-not-exist-xyz.txt")
    assert result.returncode != 0


def test_cli_no_color_flag():
    result = _run_cli("--no-color", "hello worlld")
    assert result.returncode == 0
    assert "\033[" not in result.stdout  # no ANSI escapes


# ---------------------------------------------------------------------------
# Grammar (skipped automatically when Java/LanguageTool unavailable)
# ---------------------------------------------------------------------------

_grammar_state = None  # cached: True / False once we actually tried


def _grammar_available():
    """True only if a local LanguageTool server really starts.

    Having Java on PATH is not enough: on Windows CI the first run must
    download the ~200 MB LanguageTool server and that frequently times out
    or is blocked. Instead of guessing, start the server once (cached) and
    skip the grammar test if that fails, so the platform job stays green.
    """
    global _grammar_state
    if _grammar_state is not None:
        return _grammar_state
    try:
        import shutil

        import language_tool_python

        if shutil.which("java") is None:
            _grammar_state = False
            return _grammar_state
        from spellcheck_core.grammar import LT_CONFIG

        tool = language_tool_python.LanguageTool("en-US", config=LT_CONFIG)
        tool.check("probe")
        tool.close()
        _grammar_state = True
    except Exception:  # noqa: BLE001 - any failure means "skip grammar"
        _grammar_state = False
    return _grammar_state


@pytest.mark.skipif(not _grammar_available(), reason="LanguageTool server not available")
def test_grammar_agreement_error():
    result = _run_cli("I has a apple")
    assert "GRAMMAR" in result.stdout
    assert "agreement" in result.stdout or "have" in result.stdout
