"""Spelling checking, wrapped so the CLI works even if pyspellchecker is absent."""

from spellchecker import SpellChecker


class SpellCheckerFacade:
    """Thin wrapper around pyspellchecker returning dicts for the CLI."""

    def __init__(self, language="en"):
        self._spell = SpellChecker(language=language)

    def check(self, text):
        """Return sorted list of {word, position, suggestions} dicts."""
        words = self._spell.split_words(text.lower())
        misspelled = self._spell.unknown(words)
        results = []
        for word in misspelled:
            start = text.lower().find(word)
            results.append({
                "word": word,
                "position": start,
                "suggestions": list(self._spell.candidates(word) or [])[:5],
            })
        return sorted(results, key=lambda r: r["position"])
