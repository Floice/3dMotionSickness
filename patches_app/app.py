from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from .config import ConfigStore
from .editor import EditorSession
from .models import PatchShape
from .overlay import OverlayWindow
from .tray import SystemTrayController


class PatchOverlayApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Patch Overlay Host")

        self.config_store = ConfigStore()
        self.shapes: list[PatchShape] = self.config_store.load_shapes()
        self.overlay = OverlayWindow(self.root)
        self.editor: EditorSession | None = None
        self.tray = SystemTrayController(
            on_edit=self.open_editor,
            on_toggle_overlay=self.toggle_overlay,
            on_exit=self.shutdown,
        )
        self.is_shutting_down = False

        self.root.bind_all("<F8>", lambda _event: self.toggle_overlay())
        self.root.bind_all("<Control-F8>", lambda _event: self.open_editor())
        self.root.bind_all("<Control-Shift-F8>", lambda _event: self.shutdown())

    def start(self) -> None:
        self.tray.start()
        self.root.after(200, self._poll_tray)
        if self.shapes:
            self.overlay.show(self.shapes)
        else:
            self.open_editor()
        self.root.mainloop()

    def _poll_tray(self) -> None:
        if self.is_shutting_down:
            return
        self.tray.poll()
        self.root.after(200, self._poll_tray)

    def open_editor(self) -> None:
        if self.editor is not None:
            self.editor.editor_window.lift()
            self.editor.toolbox.lift()
            return
        self.overlay.hide()
        self.editor = EditorSession(
            master=self.root,
            initial_shapes=self.shapes,
            on_save=self._save_shapes,
            on_cancel=self._editor_cancelled,
        )

    def _save_shapes(self, shapes: list[PatchShape]) -> None:
        self.shapes = shapes
        self.config_store.save_shapes(shapes)
        self.editor = None
        if self.shapes:
            self.overlay.show(self.shapes)
        else:
            messagebox.showinfo("Saved", "No patches saved. The app will stay in the tray.")

    def _editor_cancelled(self) -> None:
        self.editor = None
        if self.shapes:
            self.overlay.show(self.shapes)
        elif not self.is_shutting_down:
            messagebox.showinfo("Info", "No saved patches yet. The app is still running in the tray.")

    def toggle_overlay(self) -> None:
        if not self.shapes:
            self.open_editor()
            return
        if self.overlay.is_visible():
            self.overlay.hide()
        else:
            self.overlay.show(self.shapes)

    def shutdown(self) -> None:
        if self.is_shutting_down:
            return
        self.is_shutting_down = True
        if self.editor is not None:
            self.editor.destroy()
            self.editor = None
        self.overlay.destroy()
        self.tray.stop()
        self.root.after(100, self.root.quit)


def run() -> None:
    app = PatchOverlayApp()
    app.start()
