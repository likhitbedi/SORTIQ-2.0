"""One-time, low-friction profile setup. AI and tokenizer are already included in the Windows installer."""
from __future__ import annotations
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from .autopilot import create_profile, save_profile

EXAMPLE = ("I'm an MBA student studying marketing, finance, operations and analytics. "
           "I also run a Vedic astrology consultancy where I research planetary "
           "placements, manage client reports, develop a CRM and run a WordPress website. "
           "My folders contain PDFs, presentations, Word documents, spreadsheets and software projects.")


class Onboarding(tk.Toplevel):
    def __init__(self, parent, on_saved, current_description: str = ""):
        super().__init__(parent)
        self.on_saved = on_saved
        self.title("SORTIQ 2.0 — Personalize your AI organizer")
        self.geometry("780x690")
        self.minsize(650, 620)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        wrap = ttk.Frame(self, padding=(16,12,16,9))
        wrap.pack(fill="both", expand=True)
        ttk.Label(wrap, text="Welcome to SORTIQ", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(wrap, text="Tell SORTIQ what you do. You won't need to label individual files.",
                  font=("Segoe UI", 10)).pack(anchor="w", pady=(3,9))
        ttk.Label(wrap, text="1. What is your work, business, or study about?", font=("Segoe UI", 11,"bold")).pack(anchor="w")
        ttk.Label(wrap, text="Describe subjects, typical documents, and any important projects.").pack(anchor="w", pady=(2, 6))
        self.description = tk.Text(wrap, height=5, wrap="word", font=("Segoe UI",10), undo=True)
        self.description.pack(fill="x")
        if current_description:
            self.description.insert("1.0", current_description)
        else:
            tk.Label(wrap, text="Example: " + EXAMPLE[:150] + "...", wraplength=690, justify="left",
                     fg="#636363").pack(anchor="w", pady=(4,0))
        ttk.Label(wrap, text="2. Which folder(s) may SORTIQ inspect?", font=("Segoe UI", 11,"bold")).pack(anchor="w", pady=(9,3))
        self.folders: list[str] = list(parent.folders)
        self.folder_list = tk.Listbox(wrap, height=3, exportselection=False)
        self.folder_list.pack(fill="x")
        self._refresh()
        line = ttk.Frame(wrap)
        line.pack(fill="x", pady=(4,3))
        ttk.Button(line, text="+ Add Folder", command=self.add_folder).pack(side="left")
        ttk.Button(line, text="Remove", command=self.remove_folder).pack(side="left", padx=6)
        ttk.Label(wrap, text="3. Organized library destination", font=("Segoe UI", 11, "bold")).pack(anchor="w",pady=(8,3))
        destination = ttk.Frame(wrap);destination.pack(fill="x")
        self.destination_var = tk.StringVar(value=parent.destination_var.get())
        ttk.Entry(destination, textvariable=self.destination_var).pack(side="left",fill="x",expand=True)
        ttk.Button(destination, text="Browse...", command=self.choose_destination).pack(side="left",padx=(6,0))
        ttk.Label(wrap, text="4. On-device AI — included with SORTIQ", font=("Segoe UI", 11, "bold")).pack(anchor="w",pady=(9,4))
        note = ("The AI model is already installed. No internet or extra download is needed. "
                "Documents are analyzed on this PC. Unreadable or uncertain files stay untouched.")
        tk.Label(wrap, text=note, wraplength=695, justify="left", fg="#555555").pack(anchor="w",pady=4)
        ttk.Label(wrap,text="Safety: automatically COPY confidently classified files. Original files stay untouched.",
                  foreground="#166b42").pack(anchor="w",pady=(7,3))
        actions = ttk.Frame(wrap)
        actions.pack(fill="x", side="bottom", pady=(5,0))
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(actions, text="Save & Organize Automatically", command=self.finish).pack(side="right",padx=7)
        ttk.Button(actions, text="Save Setup Only", command=lambda: self.finish(start=False)).pack(side="right")

    def _refresh(self):
        self.folder_list.delete(0,"end")
        for folder in self.folders:self.folder_list.insert("end",folder)

    def add_folder(self):
        name = filedialog.askdirectory(parent=self, title="Choose a source folder for SORTIQ")
        if name:
            name=str(Path(name).resolve())
            if name not in self.folders:self.folders.append(name)
            self._refresh()

    def remove_folder(self):
        selection = self.folder_list.curselection()
        if selection:
            self.folders.pop(selection[0]);self._refresh()

    def choose_destination(self):
        name = filedialog.askdirectory(parent=self, title="Choose where organized copies should go")
        if name: self.destination_var.set(str(Path(name).resolve()))

    def finish(self, start: bool = True):
        try:
            description=self.description.get("1.0","end").strip()
            profile=create_profile(description)
            if not self.folders:
                messagebox.showerror("Choose a folder","Add at least one folder first.", parent=self);return
            if not self.destination_var.get().strip():
                raise ValueError("Choose a destination folder for organized copies")
            save_profile(profile)
        except (ValueError,OSError) as exc:
            messagebox.showerror("Could not save setup",str(exc),parent=self);return
        self.destroy()
        self.on_saved(profile,self.folders,start,self.destination_var.get().strip())
