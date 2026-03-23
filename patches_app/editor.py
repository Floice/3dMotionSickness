from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Callable

from .models import PatchShape


HANDLE_SIZE = 6


class EditorSession:
    def __init__(
        self,
        master: tk.Tk,
        initial_shapes: list[PatchShape],
        on_save: Callable[[list[PatchShape]], None],
        on_cancel: Callable[[], None],
    ) -> None:
        self.master = master
        self.on_save = on_save
        self.on_cancel = on_cancel
        self.shapes = [shape.normalized() for shape in initial_shapes]
        self.next_shape_id = max((shape.shape_id for shape in self.shapes), default=0) + 1

        self.editor_window = tk.Toplevel(master)
        self.editor_window.title("Patch Editor")
        self.editor_window.state("zoomed")
        self.editor_window.attributes("-topmost", True)
        self.editor_window.configure(bg="#f1f1f1")
        self.editor_window.protocol("WM_DELETE_WINDOW", self._cancel)

        self.toolbox = tk.Toplevel(master)
        self.toolbox.title("Controls")
        self.toolbox.attributes("-topmost", True)
        self.toolbox.resizable(False, False)
        self.toolbox.protocol("WM_DELETE_WINDOW", self._cancel)

        self.canvas = tk.Canvas(
            self.editor_window,
            bg="#f8f8f8",
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self.status_var = tk.StringVar(
            value="左键选中并拖动，拖拽四角手柄可缩放。"
        )
        self._build_toolbox()

        self.selected_id: int | None = self.shapes[0].shape_id if self.shapes else None
        self.drag_state: dict[str, int | str | None] | None = None

        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.editor_window.bind("<Delete>", self._delete_selected)
        self.editor_window.bind("<Escape>", lambda _event: self._cancel())

        self.editor_window.after(50, self._place_toolbox)
        self._redraw()

    def _build_toolbox(self) -> None:
        container = tk.Frame(self.toolbox, padx=12, pady=12)
        container.pack(fill="both", expand=True)

        tk.Label(
            container,
            text="贴片编辑",
            font=("Microsoft YaHei UI", 11, "bold"),
        ).pack(anchor="w")

        tk.Button(
            container,
            text="新增矩形",
            width=18,
            command=lambda: self._add_shape("rectangle"),
        ).pack(fill="x", pady=(10, 6))
        tk.Button(
            container,
            text="新增圆形",
            width=18,
            command=lambda: self._add_shape("circle"),
        ).pack(fill="x", pady=6)
        tk.Button(
            container,
            text="删除选中",
            width=18,
            command=self._delete_selected,
        ).pack(fill="x", pady=6)
        tk.Button(
            container,
            text="保存并后台运行",
            width=18,
            command=self._save,
        ).pack(fill="x", pady=(18, 6))
        tk.Button(
            container,
            text="取消",
            width=18,
            command=self._cancel,
        ).pack(fill="x", pady=6)

        tk.Label(
            container,
            textvariable=self.status_var,
            justify="left",
            wraplength=200,
            fg="#444444",
        ).pack(anchor="w", pady=(18, 0))

    def _place_toolbox(self) -> None:
        self.toolbox.geometry("+30+30")

    def _add_shape(self, kind: str) -> None:
        screen_width = self.editor_window.winfo_screenwidth()
        screen_height = self.editor_window.winfo_screenheight()
        shape = PatchShape(
            shape_id=self.next_shape_id,
            kind=kind,
            x=max(40, screen_width // 2 - 100),
            y=max(40, screen_height // 2 - 60),
            width=220,
            height=120,
        )
        self.next_shape_id += 1
        self.shapes.append(shape)
        self.selected_id = shape.shape_id
        self.status_var.set("已新增贴片，拖动或缩放后点击保存。")
        self._redraw()

    def _shape_at(self, x: int, y: int) -> PatchShape | None:
        for shape in reversed(self.shapes):
            if shape.x <= x <= shape.x + shape.width and shape.y <= y <= shape.y + shape.height:
                return shape
        return None

    def _get_selected(self) -> PatchShape | None:
        if self.selected_id is None:
            return None
        for shape in self.shapes:
            if shape.shape_id == self.selected_id:
                return shape
        return None

    def _handle_hit(self, shape: PatchShape, x: int, y: int) -> str | None:
        handles = {
            "nw": (shape.x, shape.y),
            "ne": (shape.x + shape.width, shape.y),
            "sw": (shape.x, shape.y + shape.height),
            "se": (shape.x + shape.width, shape.y + shape.height),
        }
        for name, (hx, hy) in handles.items():
            if abs(x - hx) <= HANDLE_SIZE * 2 and abs(y - hy) <= HANDLE_SIZE * 2:
                return name
        return None

    def _on_press(self, event: tk.Event) -> None:
        shape = self._shape_at(event.x, event.y)
        if not shape:
            self.selected_id = None
            self.drag_state = None
            self._redraw()
            return

        self.selected_id = shape.shape_id
        handle = self._handle_hit(shape, event.x, event.y)
        if handle:
            mode = "resize"
            anchor = handle
            self.status_var.set("正在缩放贴片。")
        else:
            mode = "move"
            anchor = None
            self.status_var.set("正在移动贴片。")

        self.drag_state = {
            "mode": mode,
            "anchor": anchor,
            "start_x": event.x,
            "start_y": event.y,
            "orig_x": shape.x,
            "orig_y": shape.y,
            "orig_w": shape.width,
            "orig_h": shape.height,
        }
        self._redraw()

    def _on_drag(self, event: tk.Event) -> None:
        shape = self._get_selected()
        if not shape or not self.drag_state:
            return

        dx = event.x - int(self.drag_state["start_x"])
        dy = event.y - int(self.drag_state["start_y"])
        if self.drag_state["mode"] == "move":
            shape.x = max(0, int(self.drag_state["orig_x"]) + dx)
            shape.y = max(0, int(self.drag_state["orig_y"]) + dy)
        else:
            self._resize_shape(shape, dx, dy, str(self.drag_state["anchor"]))
        self._redraw()

    def _resize_shape(self, shape: PatchShape, dx: int, dy: int, anchor: str) -> None:
        x = int(self.drag_state["orig_x"])
        y = int(self.drag_state["orig_y"])
        w = int(self.drag_state["orig_w"])
        h = int(self.drag_state["orig_h"])

        if "w" in anchor:
            new_x = x + dx
            new_w = w - dx
        else:
            new_x = x
            new_w = w + dx

        if "n" in anchor:
            new_y = y + dy
            new_h = h - dy
        else:
            new_y = y
            new_h = h + dy

        if new_w < 20:
            if "w" in anchor:
                new_x -= 20 - new_w
            new_w = 20
        if new_h < 20:
            if "n" in anchor:
                new_y -= 20 - new_h
            new_h = 20

        shape.x = max(0, new_x)
        shape.y = max(0, new_y)
        shape.width = new_w
        shape.height = new_h

    def _on_release(self, _event: tk.Event) -> None:
        if self.drag_state:
            self.status_var.set("调整完成，可以继续编辑或保存。")
        self.drag_state = None

    def _delete_selected(self, _event: tk.Event | None = None) -> None:
        if self.selected_id is None:
            return
        self.shapes = [shape for shape in self.shapes if shape.shape_id != self.selected_id]
        self.selected_id = self.shapes[-1].shape_id if self.shapes else None
        self.status_var.set("已删除选中贴片。")
        self._redraw()

    def _save(self) -> None:
        if not self.shapes:
            proceed = messagebox.askyesno(
                "无贴片",
                "当前没有任何贴片。保存后只会驻留托盘，是否继续？",
                parent=self.toolbox,
            )
            if not proceed:
                return
        self.on_save([shape.normalized() for shape in self.shapes])
        self.destroy()

    def _cancel(self) -> None:
        self.on_cancel()
        self.destroy()

    def destroy(self) -> None:
        if self.toolbox.winfo_exists():
            self.toolbox.destroy()
        if self.editor_window.winfo_exists():
            self.editor_window.destroy()

    def _draw_shape(self, shape: PatchShape) -> None:
        x1, y1 = shape.x, shape.y
        x2, y2 = shape.x + shape.width, shape.y + shape.height
        if shape.kind == "circle":
            item = self.canvas.create_oval(
                x1, y1, x2, y2,
                fill="black",
                outline="#00a2ff" if shape.shape_id == self.selected_id else "#222222",
                width=3 if shape.shape_id == self.selected_id else 1,
            )
        else:
            item = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill="black",
                outline="#00a2ff" if shape.shape_id == self.selected_id else "#222222",
                width=3 if shape.shape_id == self.selected_id else 1,
            )
        self.canvas.tag_raise(item)

        if shape.shape_id == self.selected_id:
            for hx, hy in (
                (x1, y1),
                (x2, y1),
                (x1, y2),
                (x2, y2),
            ):
                self.canvas.create_rectangle(
                    hx - HANDLE_SIZE,
                    hy - HANDLE_SIZE,
                    hx + HANDLE_SIZE,
                    hy + HANDLE_SIZE,
                    fill="white",
                    outline="#00a2ff",
                    width=2,
                )

    def _redraw(self) -> None:
        self.canvas.delete("all")
        self.canvas.create_text(
            24,
            20,
            anchor="nw",
            text="编辑模式：贴片会按实际屏幕坐标保存。黑色区域就是最终遮挡区域。",
            fill="#555555",
            font=("Microsoft YaHei UI", 12),
        )
        for shape in self.shapes:
            self._draw_shape(shape)
