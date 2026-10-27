#!/usr/bin/env python3
"""Thin CLI wrapper: `spellcheck` command (installed via pyproject entry point)."""

import sys

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


def main():
    # Reuse the standalone script's logic
    import spellcheck

    return spellcheck.main()


if __name__ == "__main__":
    sys.exit(main())
