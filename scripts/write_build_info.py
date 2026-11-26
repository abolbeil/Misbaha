"""Write misbaha/_build_info.py so a build knows which GitHub repository to check for updates.

Uses $GITHUB_REPOSITORY in GitHub Actions, else the 'origin' remote of the local git checkout.
Without either, no file is written and the build simply doesn't check for updates.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, "misbaha", "_build_info.py")


def detect():
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo:
        try:
            url = subprocess.run(["git", "-C", ROOT, "remote", "get-url", "origin"], capture_output=True,
                                 text=True, timeout=10).stdout.strip()
            m = re.search(r"github\.com[:/]([A-Za-z0-9-]+/[A-Za-z0-9._-]+?)(?:\.git)?$", url)
            repo = m.group(1) if m else ""
        except Exception:
            repo = ""
    return repo if re.fullmatch(r"[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}", repo) else ""


if __name__ == "__main__":
    repo = detect()
    if not repo:
        print("build info: no GitHub repository found - this build will not check for updates")
        sys.exit(0)
    with open(TARGET, "w", encoding="utf-8") as f:
        f.write("# Generated at build time by scripts/write_build_info.py - do not edit.\nREPO = %r\n" % repo)
    print("build info: update checks use github.com/%s" % repo)
