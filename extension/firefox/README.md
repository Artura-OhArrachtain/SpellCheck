# Firefox extension

This popup sends text to the local Spellcheck API at `http://127.0.0.1:8000`.
Start the Linux desktop app or run `spellcheck-server` before checking text.
The extension only requests access to that local API and does not read page
content.

## Load temporarily in Firefox

1. Install the Python package and start the Spellcheck server.
2. Open `about:debugging#/runtime/this-firefox` in Firefox.
3. Select **Load Temporary Add-on…** and choose `manifest.json` from this folder.
4. Pin the Spellcheck toolbar button, then open it to check text.

Temporary add-ons are removed when Firefox closes. Permanent installation
requires signing the add-on through Mozilla Add-ons; the manifest includes the
Firefox identifier and no-data-collection declaration needed for that flow.
