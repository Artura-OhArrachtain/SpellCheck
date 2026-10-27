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
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, cwd=REPO, timeout=120,
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

def _grammar_available():
    try:
        import language_tool_python  # noqa: F401
    except ImportError:
        return False
    import shutil
    return shutil.which("java") is not None


@pytest.mark.skipif(not _grammar_available(), reason="Java/LanguageTool not available")
def test_grammar_agreement_error():
    result = _run_cli("I has a apple")
    assert "GRAMMAR" in result.stdout
    assert "agreement" in result.stdout or "have" in result.stdout
