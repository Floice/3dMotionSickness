from __future__ import annotations

import ctypes
import tkinter as tk
from typing import Iterable

from .models import PatchShape


GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080


class _PatchWindow:
    def __init__(self, master: tk.Tk, shape: PatchShape) -> None:
        self.shape_id = shape.shape_id
        self.kind = shape.kind
        self.window = tk.Toplevel(master)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(bg="black")
        self._region_handle: int | None = None

        self.update(shape)

    def update(self, shape: PatchShape) -> None:
        self.kind = shape.kind
        self.window.geometry(f"{shape.width}x{shape.height}+{shape.x}+{shape.y}")
        self.window.deiconify()
        self.window.lift()
        self._apply_shape(shape.width, shape.height)
        self._apply_clickthrough()

    def hide(self) -> None:
        self.window.withdraw()

    def destroy(self) -> None:
        if self._region_handle:
            ctypes.windll.gdi32.DeleteObject(self._region_handle)
            self._region_handle = None
        if self.window.winfo_exists():
            self.window.destroy()

    def _apply_shape(self, width: int, height: int) -> None:
        self.window.update_idletasks()
        hwnd = self.window.winfo_id()
        gdi32 = ctypes.windll.gdi32
        user32 = ctypes.windll.user32

        if self._region_handle:
            gdi32.DeleteObject(self._region_handle)
            self._region_handle = None

        if self.kind == "circle":
            region = gdi32.CreateEllipticRgn(0, 0, width, height)
            user32.SetWindowRgn(hwnd, region, True)
            self._region_handle = region
        else:
            user32.SetWindowRgn(hwnd, 0, True)

    def _apply_clickthrough(self) -> None:
        self.window.update_idletasks()
        hwnd = self.window.winfo_id()
        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)


class OverlayWindow:
    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self._visible = False
        self._windows: dict[int, _PatchWindow] = {}

    def show(self, shapes: Iterable[PatchShape]) -> None:
        shapes_by_id = {shape.shape_id: shape for shape in shapes}

        for shape_id in list(self._windows):
            if shape_id not in shapes_by_id:
                self._windows.pop(shape_id).destroy()

        for shape in shapes_by_id.values():
            patch_window = self._windows.get(shape.shape_id)
            if patch_window is None:
                patch_window = _PatchWindow(self.master, shape)
                self._windows[shape.shape_id] = patch_window
            else:
                patch_window.update(shape)

        self._visible = True

    def hide(self) -> None:
        for patch_window in self._windows.values():
            patch_window.hide()
        self._visible = False

    def redraw(self, shapes: Iterable[PatchShape]) -> None:
        self.show(shapes)

    def is_visible(self) -> bool:
        return self._visible

    def destroy(self) -> None:
        for patch_window in list(self._windows.values()):
            patch_window.destroy()
        self._windows.clear()
        self._visible = False
