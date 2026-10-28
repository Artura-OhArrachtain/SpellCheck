"""Launch the local Spellcheck web app from a desktop menu."""

import json
import subprocess
import sys
import time
import webbrowser
from urllib.error import URLError
from urllib.request import urlopen


HOST = "127.0.0.1"
PORT = 8000
URL = "http://{}:{}/".format(HOST, PORT)


def _server_is_ready():
    try:
        with urlopen("http://{}:{}/health".format(HOST, PORT), timeout=1) as response:
            return json.loads(response.read().decode("utf-8")).get("status") == "ok"
    except (OSError, URLError, ValueError):
        return False


def main():
    if not _server_is_ready():
        process = subprocess.Popen(
            [sys.executable, "-m", "spellcheck_api", "--host", HOST, "--port", str(PORT)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        for _ in range(50):
            if _server_is_ready():
                break
            if process.poll() is not None:
                raise SystemExit("Could not start Spellcheck. Try running spellcheck-server to see the error.")
            time.sleep(0.2)
        else:
            process.terminate()
            raise SystemExit("Spellcheck did not start in time. Try running spellcheck-server manually.")

    if not webbrowser.open(URL):
        print("Spellcheck is running at {}".format(URL))


if __name__ == "__main__":
    main()
