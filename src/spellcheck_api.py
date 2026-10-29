"""HTTP API for the Spellcheck CLI."""

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from urllib.parse import urlparse

from spellcheck_core.grammar import LT_CONFIG
from spellcheck_core.speller import SpellCheckerFacade

try:
    import language_tool_python
except ImportError:  # Grammar support is optional at runtime.
    language_tool_python = None


MAX_REQUEST_BYTES = 1_000_000
_checker = SpellCheckerFacade()
_grammar_tool = None
_lock = Lock()

HTML_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Spellcheck</title>
  <style>
    :root { color-scheme: light dark; font: 16px/1.5 system-ui, sans-serif; }
    body { max-width: 850px; margin: 0 auto; padding: 2rem 1rem; }
    h1 { margin-bottom: .25rem; }
    .muted { opacity: .72; margin-top: 0; }
    textarea { box-sizing: border-box; width: 100%; min-height: 210px; padding: 1rem;
      border: 1px solid #8888; border-radius: 10px; font: inherit; }
    .controls { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; margin: 1rem 0; }
    button { border: 0; border-radius: 8px; padding: .7rem 1.1rem; font: inherit;
      font-weight: 650; cursor: pointer; background: #2463eb; color: white; }
    button:disabled { opacity: .6; cursor: wait; }
    #status { min-height: 1.5em; }
    .warning { padding: .75rem; border-left: 4px solid #d89000; background: #d8900018; }
    .group { margin-top: 1.5rem; }
    .item { padding: .8rem 1rem; margin: .5rem 0; border: 1px solid #8885; border-radius: 8px; }
    .item strong { display: block; }
    @media (max-width: 540px) { body { padding: 1rem .75rem; } }
  </style>
</head>
<body>
  <main>
    <h1>Spellcheck</h1>
    <p class="muted">Check spelling and grammar using your configured Spellcheck server.</p>
    <form id="check-form">
      <label for="text">Text to check</label>
      <textarea id="text" maxlength="500000" placeholder="Paste or type your text here…" required></textarea>
      <div class="controls">
        <label><input id="grammar" type="checkbox" checked> Check grammar and style</label>
        <button id="submit" type="submit">Check text</button>
      </div>
    </form>
    <p id="status" role="status" aria-live="polite"></p>
    <div id="results"></div>
  </main>
  <script>
    const form = document.querySelector('#check-form');
    const button = document.querySelector('#submit');
    const status = document.querySelector('#status');
    const results = document.querySelector('#results');

    function section(title, items, describe) {
      const group = document.createElement('section');
      group.className = 'group';
      const heading = document.createElement('h2');
      heading.textContent = title + ' (' + items.length + ')';
      group.append(heading);
      if (!items.length) {
        const empty = document.createElement('p');
        empty.textContent = 'No issues found.';
        group.append(empty);
      }
      items.forEach(item => {
        const copy = describe(item);
        const card = document.createElement('article');
        card.className = 'item';
        const title = document.createElement('strong');
        title.textContent = copy.title;
        card.append(title);
        const detail = document.createElement('span');
        detail.textContent = copy.detail;
        card.append(detail);
        group.append(card);
      });
      results.append(group);
    }

    form.addEventListener('submit', async event => {
      event.preventDefault();
      const text = document.querySelector('#text').value;
      if (!text.trim()) { status.textContent = 'Enter some text to check.'; return; }
      button.disabled = true;
      status.textContent = 'Checking…';
      results.replaceChildren();
      try {
        const response = await fetch('/check', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, grammar: document.querySelector('#grammar').checked })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'The check failed.');
        if (data.warning) {
          const warning = document.createElement('p');
          warning.className = 'warning';
          warning.textContent = data.warning;
          results.append(warning);
        }
        section('Spelling', data.spelling, item => ({
          title: item.word + ' (position ' + item.position + ')',
          detail: 'Suggestions: ' + (item.suggestions.join(', ') || 'none')
        }));
        if (document.querySelector('#grammar').checked) {
          section('Grammar and style', data.grammar, item => ({
            title: item.issue_type + ' (position ' + item.offset + ')',
            detail: item.message + (item.replacements.length ? ' Suggestions: ' + item.replacements.join(', ') : '')
          }));
        }
        status.textContent = 'Check complete.';
      } catch (error) {
        status.textContent = error.message;
      } finally {
        button.disabled = false;
      }
    });
  </script>
</body>
</html>""".encode("utf-8")


def check_text(text, grammar=True):
    """Check text and return a JSON-serializable result."""
    with _lock:
        spelling = _checker.check(text)
        grammar_results = []
        warning = None
        if grammar:
            if language_tool_python is None:
                warning = "Grammar support is unavailable; install language-tool-python."
            else:
                global _grammar_tool
                try:
                    if _grammar_tool is None:
                        _grammar_tool = language_tool_python.LanguageTool(
                            "en-US", config=LT_CONFIG
                        )
                    grammar_results = [
                        {
                            "offset": match.offset,
                            "length": match.error_length,
                            "message": match.message,
                            "issue_type": match.rule_issue_type,
                            "replacements": match.replacements,
                        }
                        for match in _grammar_tool.check(text)
                    ]
                except Exception as exc:
                    warning = "Grammar support is unavailable: {}".format(str(exc))
                    _grammar_tool = None

    result = {"spelling": spelling, "grammar": grammar_results}
    if warning:
        result["warning"] = warning
    return result


class SpellcheckHandler(BaseHTTPRequestHandler):
    server_version = "SpellcheckAPI/1.0"

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(HTML_PAGE)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(HTML_PAGE)
        elif path == "/health":
            self._send_json(200, {"status": "ok"})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if urlparse(self.path).path != "/check":
            self._send_json(404, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "invalid Content-Length"})
            return
        if length <= 0:
            self._send_json(400, {"error": "request body is required"})
            return
        if length > MAX_REQUEST_BYTES:
            self._send_json(413, {"error": "request body is too large"})
            return

        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"error": "body must be valid UTF-8 JSON"})
            return
        if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
            self._send_json(400, {"error": "JSON body must include a string 'text'"})
            return
        if not isinstance(payload.get("grammar", True), bool):
            self._send_json(400, {"error": "'grammar' must be a boolean"})
            return

        self._send_json(200, check_text(payload["text"], payload.get("grammar", True)))

    def log_message(self, format, *args):
        # Keep request text and other request details out of default logs.
        return


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the Spellcheck HTTP API.")
    azure_app_service = bool(os.environ.get("WEBSITE_SITE_NAME"))
    default_host = "0.0.0.0" if azure_app_service else "127.0.0.1"
    default_port = int(os.environ.get("PORT", "8000"))
    parser.add_argument("--host", default=default_host, help="address to bind")
    parser.add_argument("--port", type=int, default=default_port, help="port to bind")
    args = parser.parse_args(argv)

    server = ThreadingHTTPServer((args.host, args.port), SpellcheckHandler)
    print("Spellcheck API listening on http://{}:{}".format(*server.server_address))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if _grammar_tool is not None:
            _grammar_tool.close()


if __name__ == "__main__":
    main()
