from __future__ import annotations

import queue
import threading
from typing import Callable

import pywintypes
import win32api
import win32con
import win32gui


WM_TRAYICON = win32con.WM_USER + 20
ID_EDIT = 1024
ID_TOGGLE = 1025
ID_EXIT = 1026


class SystemTrayController:
    def __init__(
        self,
        on_edit: Callable[[], None],
        on_toggle_overlay: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None:
        self.on_edit = on_edit
        self.on_toggle_overlay = on_toggle_overlay
        self.on_exit = on_exit
        self.command_queue: queue.Queue[str] = queue.Queue()
        self._thread: threading.Thread | None = None
        self.hwnd: int | None = None
        self._class_name = "PatchOverlayTrayWindow"

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self.hwnd:
            win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)
        self.hwnd = None

    def poll(self) -> None:
        while True:
            try:
                command = self.command_queue.get_nowait()
            except queue.Empty:
                break

            if command == "edit":
                self.on_edit()
            elif command == "toggle":
                self.on_toggle_overlay()
            elif command == "exit":
                self.on_exit()

    def _run(self) -> None:
        message_map = {
            WM_TRAYICON: self._on_tray_event,
            win32con.WM_DESTROY: self._on_destroy,
        }

        wc = win32gui.WNDCLASS()
        wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = self._class_name
        wc.lpfnWndProc = message_map
        try:
            class_atom = win32gui.RegisterClass(wc)
        except pywintypes.error:
            class_atom = win32gui.GetClassInfo(wc.hInstance, self._class_name)[0]

        style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
        self.hwnd = win32gui.CreateWindow(
            class_atom,
            self._class_name,
            style,
            0,
            0,
            win32con.CW_USEDEFAULT,
            win32con.CW_USEDEFAULT,
            0,
            0,
            wc.hInstance,
            None,
        )
        self._create_icon()
        win32gui.PumpMessages()

    def _create_icon(self) -> None:
        if self.hwnd is None:
            return
        hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
        notify_id = (
            self.hwnd,
            0,
            win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP,
            WM_TRAYICON,
            hicon,
            "Patch Overlay",
        )
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, notify_id)
        try:
            win32gui.Shell_NotifyIcon(
                win32gui.NIM_SETVERSION,
                (self.hwnd, 0, win32gui.NOTIFYICON_VERSION_4),
            )
        except Exception:
            pass

    def _show_menu(self) -> None:
        if self.hwnd is None:
            return
        menu = win32gui.CreatePopupMenu()
        win32gui.AppendMenu(menu, win32con.MF_STRING, ID_EDIT, "编辑贴片")
        win32gui.AppendMenu(menu, win32con.MF_STRING, ID_TOGGLE, "显示/隐藏贴片")
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, ID_EXIT, "退出")
        pos = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(self.hwnd)
        command_id = win32gui.TrackPopupMenu(
            menu,
            win32con.TPM_LEFTALIGN | win32con.TPM_BOTTOMALIGN | win32con.TPM_RETURNCMD,
            pos[0],
            pos[1],
            0,
            self.hwnd,
            None,
        )
        win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)

        if command_id == ID_EDIT:
            self.command_queue.put("edit")
        elif command_id == ID_TOGGLE:
            self.command_queue.put("toggle")
        elif command_id == ID_EXIT:
            self.command_queue.put("exit")

    def _on_tray_event(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        if lparam == win32con.WM_LBUTTONDBLCLK:
            self.command_queue.put("edit")
        elif lparam == win32con.WM_RBUTTONUP:
            self._show_menu()
        elif lparam == win32con.WM_LBUTTONUP:
            self.command_queue.put("toggle")
        return 0

    def _on_destroy(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (hwnd, 0))
        win32gui.PostQuitMessage(0)
        return 0
