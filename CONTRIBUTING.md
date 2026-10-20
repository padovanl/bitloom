# Contributing to Bitloom

Thanks for helping. Bitloom is licensed under the GNU AGPL-3.0-or-later with the
additional terms in [NOTICE](NOTICE). By sending a contribution you agree that it
is released under the same terms.

## Before you open a pull request

1. **Open an issue first** for anything larger than a fix, so we can agree on the approach.
2. **Set up a checkout:**

   ```sh
   python3 -m venv .venv
   .venv/bin/pip install -e '.[dev,docs]'
   ```

3. **Run the tests.** They need no Yocto build and finish in a few minutes:

   ```sh
   .venv/bin/python -m pytest -q
   ```

4. **Keep the docs in step with the code.** Every user-visible change updates:
   - the page under [docs/](docs/) that describes it;
   - the README feature list when a feature is added;
   - [README.testbook.md](README.testbook.md) with a manual check on both supported releases;
   - the screenshots, when the UI changed (`tools/capture_docs.py`, `tools/capture_web.py`).

   Then rebuild and check the site:

   ```sh
   .venv/bin/python tools/build_docs.py
   .venv/bin/python tools/check_docs.py
   ```

## Ground rules

- **Every feature works on every runtime:** host, kas, kas-container, a container, and a launcher script.
  If something cannot work on one of them, say so in the UI and in the docs.
- **The web dashboard never builds HTML from strings with `innerHTML`.** Use DOM nodes and `textContent`.
- **No private data in captures.** `tools/terminal_capture.py` replaces your home and checkout paths;
  check any screenshot you add by hand.
- **Commit messages** follow the existing style: `feat:`, `fix:`, `docs:`, `test:`, followed by a sentence in plain words.

## Reporting bugs

Open an issue with:
- the Bitloom version (`bitloom --version`);
- the runtime (host, kas, kas-container, container or launcher script);
- the Yocto release;
- what you did, what you expected and what happened.

Security problems go through [SECURITY.md](SECURITY.md), not public issues.
