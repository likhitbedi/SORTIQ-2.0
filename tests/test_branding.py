"""Maker credit is visible in SORTIQ and its Windows setup wizard."""
from pathlib import Path
from sortiq import __author__, __version__, MAKER_CREDIT

ROOT = Path(__file__).resolve().parents[1]


def test_author():
    assert __author__ == "Likhit Bedi"
    assert __version__ == "2.0.3-beta"
    assert MAKER_CREDIT == "Made by Likhit Bedi"


def test_main_window_and_about_credit():
    text = (ROOT / "sortiq" / "gui.py").read_text(encoding="utf-8")
    assert "text=MAKER_CREDIT" in text
    assert 'self.title(f"SORTIQ Classic - File Organizer v{__version__} | {MAKER_CREDIT}")' in text
    assert "{MAKER_CREDIT}\\n\\n" in text


def test_setup_welcome_and_publisher_credit():
    text = (ROOT / "installer" / "SORTIQ_Setup.iss").read_text(encoding="utf-8")
    assert "AppPublisher=Likhit Bedi" in text
    assert "WizardForm.WelcomeLabel2.Caption" in text
    assert "'Made by Likhit Bedi'" in text
    assert '#define AppVersion "2.0.3-beta"' in text
    assert "OutputBaseFilename=SORTIQ_2.0.3_Beta_Setup" in text
