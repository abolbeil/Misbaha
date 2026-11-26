"""Update check: notify-only, at most once a day, never downloads or runs anything.

Security design (audit finding SEC-01):
* Asks exactly one URL: https://api.github.com/repos/<owner>/<repo>/releases/latest (TLS verified).
* The repository is fixed at build time (misbaha/_build_info.py, written by GitHub Actions);
  source runs without it simply don't check.
* Drafts, pre-releases, malformed tags and anything that is not strictly newer are ignored.
* The only action offered is opening the release page on github.com in the browser.
* Runs on a background thread with a 10 s timeout and fails silently (offline / proxy PCs).
* Sends no personal data: a plain GET with "User-Agent: Misbaha/<version>".
"""

import json
import os
import re
import threading
import urllib.request

from PySide6.QtCore import QObject, Signal

from misbaha import __version__
from misbaha.paths import log

API = "https://api.github.com/repos/%s/releases/latest"
MAX_BYTES = 512 * 1024
TIMEOUT = 10
REPO_RE = re.compile(r"^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}$")


def update_repo():
    """'owner/repo' this build checks, or None (no check)."""
    repo = os.environ.get("MISBAHA_UPDATE_REPO")
    if not repo:
        try:
            from misbaha._build_info import REPO as repo      # written by the release build
        except ImportError:
            repo = None
    return repo if repo and REPO_RE.match(repo) else None


def parse_version(s):
    m = re.fullmatch(r"v?(\d{1,4})\.(\d{1,4})(?:\.(\d{1,4}))?", str(s or "").strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)


def evaluate_release(data, repo, current=__version__):
    """Return (version, page_url) if `data` (GitHub API JSON) is a valid newer release, else None."""
    if not isinstance(data, dict) or data.get("draft") or data.get("prerelease"):
        return None
    new = parse_version(data.get("tag_name"))
    cur = parse_version(current)
    if not new or not cur or new <= cur:
        return None
    url = data.get("html_url")
    prefix = "https://github.com/%s/releases/" % repo
    if not isinstance(url, str) or not url.startswith(prefix) or any(c in url for c in "\"'<> \\"):
        return None
    return "%d.%d.%d" % new, url


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):          # the API answers directly; never follow elsewhere
        return None


class UpdateChecker(QObject):
    found = Signal(str, str)            # version, release page URL
    done = Signal(bool, str)            # ok, "" or error text (for "Check now")

    def __init__(self):
        super().__init__()
        self._busy = False

    def check(self):
        repo = update_repo()
        if not repo:
            self.done.emit(False, "no-repo")
            return
        if self._busy:
            return
        self._busy = True
        threading.Thread(target=self._run, args=(repo,), name="misbaha-update", daemon=True).start()

    def _run(self, repo):
        try:
            req = urllib.request.Request(API % repo, headers={
                "Accept": "application/vnd.github+json", "User-Agent": "Misbaha/%s" % __version__})
            opener = urllib.request.build_opener(_NoRedirect)
            with opener.open(req, timeout=TIMEOUT) as r:
                if r.status != 200 or not r.geturl().startswith("https://api.github.com/"):
                    raise ValueError("unexpected response %s" % r.status)
                body = r.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError("response too large")
            res = evaluate_release(json.loads(body.decode("utf-8")), repo)
            if res:
                self.found.emit(*res)
            self.done.emit(True, "")
        except Exception as e:
            log("update check failed: %s" % e)
            self.done.emit(False, str(e))
        finally:
            self._busy = False
