"""Guard against missing stdout/stderr in windowed Windows executables."""
import os
import sys

from main import ensure_windowed_stdio


def test_windowed_console_streams_are_restored(monkeypatch):
    original_stdout, original_stderr = sys.stdout, sys.stderr
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    try:
        ensure_windowed_stdio()
        assert sys.stdout is not None
        assert sys.stderr is not None
        sys.stdout.write("model init message")
        sys.stderr.write("model init error")
        sys.stdout.flush()
        sys.stderr.flush()
    finally:
        replacement_stdout = sys.stdout
        replacement_stderr = sys.stderr
        monkeypatch.setattr(sys, "stdout", original_stdout)
        monkeypatch.setattr(sys, "stderr", original_stderr)
        replacement_stdout.close()
        replacement_stderr.close()


def test_existing_output_streams_remain_untouched():
    before = (sys.stdout, sys.stderr)
    ensure_windowed_stdio()
    assert (sys.stdout, sys.stderr) == before
