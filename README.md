# Spellcheck

A command-line spelling and grammar checker with an optional local HTTP API,
for Python 3.8 and newer. Spelling checks use `pyspellchecker`. Grammar and
style checks use a local LanguageTool server started by
`language-tool-python`; they require Java 8 or newer. On first use,
LanguageTool downloads its server files, which are cached for later runs.

## Install

Requires Python 3.8 or newer. Install from PyPI on Windows:

```powershell
py -m pip install spellcheck-cli
```

On macOS or Linux:

```sh
python3 -m pip install spellcheck-cli
```

These commands install the CLI and HTTP server commands. If your system blocks
global package installs, create and activate a virtual environment first, then
run the same pip command inside it. Java 8 or newer is only needed for grammar
checks; spelling works without Java, and grammar can be skipped with
`--no-grammar` for text and file checks.

## Usage

Check text directly:

```sh
spellcheck "This are an example sentence."
```

Check a UTF-8 text file:

```sh
spellcheck --file document.txt
```

Run interactively by starting `spellcheck` without arguments. For text and
file checks, use `--no-color` to disable colored output, `--color` to force it,
or `--no-grammar` to skip grammar and style checks.

## HTTP API

Start the local server with:

```sh
spellcheck-server --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in a browser to use the
simple interface: paste text, choose whether to check grammar, and view issues
and suggestions. The interface calls the local API; no separate frontend setup
is needed.

The server provides `GET /health`, which returns `{"status":"ok"}`, and
`POST /check`. The check endpoint accepts a JSON object with a required `text`
string and an optional `grammar` boolean (defaults to `true`):

```sh
curl -X POST http://127.0.0.1:8000/check \
  -H 'Content-Type: application/json' \
  -d '{"text":"This are an example sentence.","grammar":false}'
```

The response contains `spelling` and `grammar` arrays. Each spelling result
has `word`, `position`, and `suggestions`; each grammar result has `offset`,
`length`, `message`, `issue_type`, and `replacements`. If grammar checking
cannot start, `grammar` is empty and the response includes a `warning`; spelling
results are still returned. Invalid requests return an error with HTTP 400,
unknown paths return 404, and request bodies are limited to 1 MB.

The server binds to `127.0.0.1` by default and does not provide authentication
or browser cross-origin access. Use `--host 0.0.0.0` only when you intend to
make it reachable from other machines and have secured access separately.

## Linux desktop app

From the project directory, install this version for your user:

```sh
python3 -m pip install --user .
```

This installs a **Spellcheck** launcher in the Linux application menu. It
starts the local server and opens the interface in your browser. You can also
start it from a terminal with `spellcheck-desktop`.

## Azure App Service

The GitHub Actions workflow in
[`python-app.yml`](.github/workflows/python-app.yml) deploys this project as a
single **Linux Python Web App** after CI passes on pushes to `main`. This app
serves both the HTTP API and its browser interface; the interface's JavaScript
runs in the browser and does not need a separate Node.js app or runtime.
Create a Linux Web App using the Python 3.12 stack. Configure a federated
identity in Microsoft Entra for this repository's `main` branch, then add
these GitHub Actions repository secrets:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `AZURE_RESOURCE_GROUP`
- `AZURE_WEBAPP_NAME`

The identity needs permission to configure and deploy the target Web App. The
workflow configures the Web App for Python 3.12, enables App Service build
automation, and sets the server startup command. The server binds to the App
Service host and port automatically; on a local machine it continues to bind
to `127.0.0.1` by default. See Microsoft's
[OIDC setup guide](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect)
for the identity and federated credential setup. Spelling works in the Python
runtime. Grammar checks also require Java 8 or newer; if Java is unavailable
in the App Service environment, the API returns spelling results and a grammar
availability warning.

## Firefox extension

The extension is in `extension/firefox`. Start the Linux app (or
`spellcheck-server`), then follow the temporary installation steps in
[`extension/firefox/README.md`](extension/firefox/README.md). A Mozilla-signed
add-on is required for permanent installation.

## Development

Install the package and development dependencies, then run the test suite:

```sh
python -m pip install -e ".[dev]"
python -m pytest
```

The grammar tests need Java 8 or newer and may download the LanguageTool server
on their first run.
