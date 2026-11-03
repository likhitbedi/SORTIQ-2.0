"""SORTIQ Windows entry point and packaged self-tests."""
from __future__ import annotations

import os
import sys


def ensure_windowed_stdio() -> None:
    """Protect third-party libraries in PyInstaller --windowed applications.

    On Windows a no-console process can have sys.stdout and sys.stderr = None.
    FastEmbed, ONNX, model download helpers or their loggers may write to them
    while the model initializes; keep writable streams available.
    """
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))


def self_test() -> None:
    # Verify the packaged code path without downloading an AI model.
    import fastembed
    from sortiq.autopilot import create_profile, HybridClassifier
    from pathlib import Path
    profile = create_profile(
        "I study MBA college marketing and finance and research astrology planetary placements."
    )
    assert "College / Marketing & Branding" in profile["categories"]
    result = HybridClassifier(profile).classify(
        Path("sample.txt"),
        "Marketing branding segmentation brand equity consumer positioning advertising customer campaigns"
    )
    assert result.status == "Ready", result.explanation
    print("SORTIQ 2.0 packaged self-test passed.")


def ai_self_test() -> None:
    """Verify installed AI inference offline on a clean Windows build runner.

    No user documents are accessed. Tracebacks are saved for console-free CI.
    """
    from pathlib import Path
    import traceback
    try:
        from sortiq.autopilot import LocalSemanticModel
        import socket
        os.environ["HF_HUB_OFFLINE"] = "1"
        original_connect = socket.socket.connect
        def refuse_network(self, address):
            raise RuntimeError(f"Unexpected network access during offline AI test: {address}")
        socket.socket.connect = refuse_network
        try:
            model = LocalSemanticModel()
            if not model.start():
                raise RuntimeError(model.error or "Bundled AI unavailable")
            vectors = model.embed([
                "Marketing segmentation positioning brand equity research and consumer behavior."
            ])
        finally:
            socket.socket.connect = original_connect
        if len(vectors) != 1 or len(vectors[0]) != 384:
            raise RuntimeError("Bundled AI model did not generate 384-dimensional vectors")
        print("SORTIQ model inference verified offline")
    except Exception:
        runner_temp = os.environ.get("RUNNER_TEMP")
        if runner_temp:
            Path(runner_temp, "SORTIQ-ai-smoke-error.txt").write_text(
                traceback.format_exc(), encoding="utf-8")
        raise


if __name__ == "__main__":
    # This must happen BEFORE importing the GUI or AI dependencies.
    ensure_windowed_stdio()
    if "--ai-self-test" in sys.argv:
        ai_self_test()
    elif "--self-test" in sys.argv:
        self_test()
    else:
        from sortiq.gui import main
        main()
