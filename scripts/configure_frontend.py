#!/usr/bin/env python3
"""Point the static frontend (web/) at a separately hosted backend.

    python scripts/configure_frontend.py --api-base https://nyaymitra-demo.onrender.com
    python scripts/configure_frontend.py --same-origin        # backend serves the website itself

Edits two files, nothing else:
  * web/config.js  -> window.NYAYMITRA_CONFIG.apiBase
  * web/_headers   -> Content-Security-Policy connect-src

It does not deploy anything. On the backend you must also set
NYAYMITRA_ALLOWED_ORIGINS=https://<your-frontend-origin> so that CORS allows the calls.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

WEB = Path(__file__).resolve().parent.parent / "web"


def normalise(api_base: str) -> str:
    parsed = urlparse(api_base.strip())
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError("api base must look like https://host[:port]")
    if parsed.path.strip("/") or parsed.query or parsed.fragment:
        raise ValueError("api base must be an origin only (no path such as /api/v1)")
    if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise ValueError("use https for a deployed backend")
    return f"{parsed.scheme}://{parsed.netloc}"


def configure(api_base: str, web: Path = WEB) -> None:
    config = web / "config.js"
    text = config.read_text(encoding="utf-8")
    new, n = re.subn(r'apiBase:\s*"[^"]*"', f'apiBase: "{api_base}"', text)
    if n != 1:
        raise RuntimeError("could not find apiBase in web/config.js")
    config.write_text(new, encoding="utf-8")

    headers = web / "_headers"
    text = headers.read_text(encoding="utf-8")
    connect = "connect-src 'self'" + (f" {api_base}" if api_base else "") + ";"
    new, n = re.subn(r"connect-src [^;]*;", connect, text)
    if n != 1:
        raise RuntimeError("could not find connect-src in web/_headers")
    headers.write_text(new, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--api-base", help="backend origin, e.g. https://nyaymitra-demo.onrender.com")
    group.add_argument("--same-origin", action="store_true", help="backend serves the website itself")
    args = parser.parse_args(argv)
    try:
        api_base = "" if args.same_origin else normalise(args.api_base)
        configure(api_base)
    except (ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"web/config.js apiBase = {api_base!r}; web/_headers connect-src updated.")
    if api_base:
        print("Remember: set NYAYMITRA_ALLOWED_ORIGINS on the backend to this website's origin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
