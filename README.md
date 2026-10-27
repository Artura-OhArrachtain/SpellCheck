# Spellcheck CLI

An offline-capable command-line spelling and grammar checker for Python 3.8 and
newer. Spelling checks use `pyspellchecker`. Grammar and style checks use a
local LanguageTool server started by `language-tool-python` and require Java
8 or newer. On first use, LanguageTool downloads its server files; they are
cached for later runs.

## Install

Install the package from PyPI:

```sh
python -m pip install spellcheck-cli
```

The package includes both spelling and grammar dependencies. To run spelling
checks without grammar support, install `pyspellchecker` and run the source
script, or pass `--no-grammar` to the CLI.

## Usage

Check text directly:

```sh
spellcheck "This are an example sentence."
```

Check a UTF-8 text file:

```sh
spellcheck --file document.txt
```

Run interactively by starting `spellcheck` without arguments. Use `--no-color`
to disable colored output, `--color` to force it, or `--no-grammar` to skip
grammar and style checks.

## Development

Install the package and development dependencies, then run the test suite:

```sh
python -m pip install -e ".[dev]"
python -m pytest
```

The grammar tests need Java 8 or newer and may download the LanguageTool server
on their first run.
