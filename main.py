"""SORTIQ Windows entry point. Supports a non-GUI release smoke-test."""
from __future__ import annotations
import sys


def self_test():
    # Validate import paths of the packaged app without loading or downloading a model.
    import fastembed
    from sortiq.autopilot import create_profile, HybridClassifier
    from pathlib import Path
    profile = create_profile("I study MBA college marketing and finance and research astrology planetary placements.")
    assert "College / Marketing & Branding" in profile["categories"]
    result = HybridClassifier(profile).classify(Path("sample.txt"),
        "Marketing branding segmentation brand equity consumer positioning advertising customer campaigns")
    assert result.status == "Ready", result.explanation
    print("SORTIQ 2.0 packaged self-test passed.")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        from sortiq.gui import main
        main()
