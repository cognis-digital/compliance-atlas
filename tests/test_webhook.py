"""Tests for integrations/webhook.py — error handling and edge cases."""
from __future__ import annotations
import io
import json
import sys
import urllib.error
import urllib.request
from unittest import mock

import pytest

# Make the integrations package importable from the repo root.
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from integrations.webhook import _validate_url, _validate_headers, main  # noqa: E402


# ---------------------------------------------------------------------------
# Unit tests for helpers
# ---------------------------------------------------------------------------


class TestValidateUrl:
    def test_empty_string_is_invalid(self):
        assert _validate_url("") is not None

    def test_whitespace_only_is_invalid(self):
        assert _validate_url("   ") is not None

    def test_missing_scheme_is_invalid(self):
        assert _validate_url("example.com/path") is not None

    def test_ftp_scheme_is_invalid(self):
        assert _validate_url("ftp://example.com") is not None

    def test_http_is_valid(self):
        assert _validate_url("http://example.com") is None

    def test_https_is_valid(self):
        assert _validate_url("https://example.com/hook") is None


class TestValidateHeaders:
    def test_empty_list_is_valid(self):
        assert _validate_headers([]) is None

    def test_well_formed_header_is_valid(self):
        assert _validate_headers(["Authorization: Bearer token"]) is None

    def test_header_without_colon_is_invalid(self):
        assert _validate_headers(["BearerToken"]) is not None

    def test_mixed_valid_invalid_reports_error(self):
        assert _validate_headers(["X-Good: val", "BadHeader"]) is not None


# ---------------------------------------------------------------------------
# Integration tests via main() with mocked I/O
# ---------------------------------------------------------------------------


VALID_JSON = json.dumps({"tool": "compliance-atlas", "findings": [], "score": 0})


def _run_main(argv: list[str], stdin_text: str | bytes | None = None) -> int:
    """Run main() with patched sys.argv and sys.stdin, return exit code."""
    if stdin_text is None:
        stdin_text = VALID_JSON

    if isinstance(stdin_text, str):
        stdin_bytes = stdin_text.encode("utf-8")
    else:
        stdin_bytes = stdin_text

    with mock.patch("sys.argv", ["webhook.py"] + argv):
        with mock.patch("sys.stdin", new=mock.MagicMock()) as mock_stdin:
            mock_stdin.buffer = io.BytesIO(stdin_bytes)
            return main()


def test_missing_url_raises_systemexit():
    """argparse exits with code 2 when --url is absent."""
    with mock.patch("sys.argv", ["webhook.py"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 2


def test_bad_url_scheme_returns_2():
    code = _run_main(["--url", "ftp://evil.com"])
    assert code == 2


def test_empty_stdin_returns_2(capsys):
    code = _run_main(["--url", "https://example.com/hook"], stdin_text=b"")
    assert code == 2
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower()


def test_non_json_stdin_returns_2(capsys):
    code = _run_main(
        ["--url", "https://example.com/hook"],
        stdin_text="not json at all!!!",
    )
    assert code == 2
    captured = capsys.readouterr()
    assert "json" in captured.err.lower()


def test_malformed_header_returns_2(capsys):
    code = _run_main(
        ["--url", "https://example.com/hook", "--header", "BadHeaderNoColon"]
    )
    assert code == 2
    captured = capsys.readouterr()
    assert "header" in captured.err.lower()


def test_negative_timeout_returns_2(capsys):
    code = _run_main(["--url", "https://example.com/hook", "--timeout", "-1"])
    assert code == 2
    captured = capsys.readouterr()
    assert "timeout" in captured.err.lower()


def test_http_error_returns_1(capsys):
    """A 4xx/5xx response from the server should exit 1, not crash."""
    http_err = urllib.error.HTTPError(
        url="https://example.com/hook",
        code=403,
        msg="Forbidden",
        hdrs={},  # type: ignore[arg-type]
        fp=None,
    )
    with mock.patch("urllib.request.urlopen", side_effect=http_err):
        code = _run_main(["--url", "https://example.com/hook"])
    assert code == 1
    captured = capsys.readouterr()
    assert "403" in captured.err


def test_network_error_returns_1(capsys):
    """A connection failure should exit 1 with a clear message."""
    url_err = urllib.error.URLError(reason="Connection refused")
    with mock.patch("urllib.request.urlopen", side_effect=url_err):
        code = _run_main(["--url", "https://example.com/hook"])
    assert code == 1
    captured = capsys.readouterr()
    assert "network" in captured.err.lower()


def test_successful_post_returns_0():
    """A successful POST should return 0."""
    mock_response = mock.MagicMock()
    mock_response.__enter__ = mock.MagicMock(return_value=mock_response)
    mock_response.__exit__ = mock.MagicMock(return_value=False)
    mock_response.status = 200

    with mock.patch("urllib.request.urlopen", return_value=mock_response):
        code = _run_main(["--url", "https://example.com/hook"])
    assert code == 0
