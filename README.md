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

## HTTP API

Start the local HTTP server with:

```sh
spellcheck-server --host 127.0.0.1 --port 8000
```

The server provides GET /health and POST /check. The check endpoint accepts
JSON with a required text string and an optional grammar boolean (defaults to
true):

```sh
curl -X POST http://127.0.0.1:8000/check \
  -H 'Content-Type: application/json' \
  -d '{"text":"This are an example sentence.","grammar":false}'
```

The response contains spelling and grammar result arrays. When grammar
checking cannot start, the response includes a warning and still returns
spelling results. The server binds to loopback by default; use --host 0.0.0.0
only when you intend to make it reachable from other machines.

## Development

Install the package and development dependencies, then run the test suite:

```sh
python -m pip install -e ".[dev]"
python -m pytest
```

The grammar tests need Java 8 or newer and may download the LanguageTool server
on their first run.
