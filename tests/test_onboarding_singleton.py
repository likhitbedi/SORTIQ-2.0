"""Regression tests for duplicate first-run dialogs and simplified toolbar state.

These call Tkinter methods with small test doubles, so they work in Windows
CI without opening real windows or requiring a graphical desktop.
"""
from queue import Queue
from unittest.mock import Mock

from sortiq import gui


def test_background_job_poll_does_not_keep_scheduling_first_run_dialog():
    app = Mock()
    app.jobs = Queue()
    app.profile = None
    app.winfo_exists.return_value = True

    gui.SortiqApp._poll_jobs(app)

    # It should schedule its next poll and nothing else.
    app.after.assert_called_once_with(120, app._poll_jobs)


def test_only_one_onboarding_window_at_a_time(monkeypatch):
    created = []

    class Dialog:
        alive = True

        def winfo_exists(self):
            return self.alive

        def lift(self):
            pass

        def focus_force(self):
            pass

    def fake_onboarding(*args, **kwargs):
        dialog = Dialog()
        created.append(dialog)
        return dialog

    monkeypatch.setattr(gui, "Onboarding", fake_onboarding)
    app = Mock()
    app.busy = False
    app.profile = None
    app._setup_window = None

    gui.SortiqApp.setup_assistant(app)
    gui.SortiqApp.setup_assistant(app)
    gui.SortiqApp.setup_assistant(app)
    assert len(created) == 1

    created[0].alive = False
    gui.SortiqApp.setup_assistant(app)
    assert len(created) == 2


def test_classic_toolbar_busy_state_does_not_reference_removed_buttons():
    class App:
        busy = False

        def __init__(self):
            self.message_var = Mock()
            self.auto_button = Mock()
            self.undo_button = Mock()

    app = App()
    gui.SortiqApp._busy(app, True, "Scanning")

    assert app.busy is True
    app.auto_button.configure.assert_called_once_with(state="disabled")
    app.undo_button.configure.assert_called_once_with(state="disabled")
    app.message_var.set.assert_called_once_with("Scanning")
