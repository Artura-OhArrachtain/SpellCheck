"""HTTP API for the Spellcheck CLI."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
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
        if urlparse(self.path).path == "/health":
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
    parser.add_argument("--host", default="127.0.0.1", help="address to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="port to bind (default: 8000)")
    args = parser.parse_args(argv)

    server = HTTPServer((args.host, args.port), SpellcheckHandler)
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
