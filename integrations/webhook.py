#!/usr/bin/env python3
"""Minimal, dependency-free webhook forwarder for Cognis findings.

Reads JSON findings on stdin and POSTs them to a URL (SIEM/Slack/Jira bridge).
Usage:  <tool> scan . --format json | python integrations/webhook.py --url URL

Exit codes:
  0  success
  1  network / server error
  2  bad arguments or malformed input
"""
from __future__ import annotations
import argparse
import json
import sys
import urllib.error
import urllib.request


def _die(msg: str, code: int = 2) -> int:
    """Print *msg* to stderr and return *code*."""
    print(f"error: {msg}", file=sys.stderr)
    return code


def _validate_url(url: str) -> str | None:
    """Return an error string if *url* is not usable, else None."""
    if not url or not url.strip():
        return "URL must not be empty"
    if not url.startswith(("http://", "https://")):
        return f"URL must start with http:// or https:// (got: {url!r})"
    return None


def _validate_headers(headers: list[str]) -> str | None:
    """Return an error string if any header string has no ':' separator."""
    for h in headers:
        if ":" not in h:
            return (
                f"--header value must be in 'Key: Value' form (got: {h!r})"
            )
    return None


def main() -> int:  # noqa: D103
    ap = argparse.ArgumentParser(
        description="POST Cognis findings JSON to a webhook URL."
    )
    ap.add_argument("--url", required=True, help="Destination URL (http/https)")
    ap.add_argument(
        "--header",
        action="append",
        default=[],
        help="Extra request header in 'Key: Value' form (repeatable)",
    )
    ap.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Request timeout in seconds (default: 15)",
    )
    args = ap.parse_args()

    # --- validate URL ---
    url_err = _validate_url(args.url)
    if url_err:
        return _die(url_err)

    # --- validate headers ---
    hdr_err = _validate_headers(args.header)
    if hdr_err:
        return _die(hdr_err)

    # --- validate timeout ---
    if args.timeout <= 0:
        return _die("--timeout must be a positive number")

    # --- read stdin ---
    try:
        raw = sys.stdin.buffer.read()
    except Exception as exc:  # pragma: no cover
        return _die(f"failed to read stdin: {exc}")

    if not raw.strip():
        return _die("stdin is empty — nothing to POST")

    # --- validate JSON ---
    try:
        raw_text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return _die(f"stdin is not valid UTF-8: {exc}")

    try:
        json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return _die(f"stdin is not valid JSON: {exc}")

    payload = raw_text.encode("utf-8")

    # --- build and send request ---
    req = urllib.request.Request(args.url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    for h in args.header:
        k, _, v = h.partition(":")
        req.add_header(k.strip(), v.strip())

    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as r:
            print(f"posted {len(payload)} bytes -> {r.status}")
        return 0
    except urllib.error.HTTPError as exc:
        return _die(f"HTTP {exc.code} from server: {exc.reason}", code=1)
    except urllib.error.URLError as exc:
        return _die(f"network error: {exc.reason}", code=1)
    except OSError as exc:
        return _die(f"connection error: {exc}", code=1)


if __name__ == "__main__":
    sys.exit(main())
