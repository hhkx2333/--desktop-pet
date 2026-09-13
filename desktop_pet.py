from __future__ import annotations

import argparse
import ctypes
import json
import math
import os
import random
import time
import tkinter as tk
from pathlib import Path

from PIL import Image, ImageTk


CELL_W = 192
CELL_H = 208
KEY_COLOR = (0, 255, 0)
KEY_HEX = "#00ff00"

ANIMATIONS = {
    "idle": {"row": 0, "frames": 6, "durations": [280, 110, 110, 140, 140, 320]},
    "running-right": {"row": 1, "frames": 8, "durations": [120] * 7 + [220]},
    "running-left": {"row": 2, "frames": 8, "durations": [120] * 7 + [220]},
    "waving": {"row": 3, "frames": 4, "durations": [140, 140, 140, 280]},
    "jumping": {"row": 4, "frames": 5, "durations": [140, 140, 140, 140, 280]},
    "failed": {"row": 5, "frames": 8, "durations": [140] * 7 + [240]},
    "waiting": {"row": 6, "frames": 6, "durations": [150] * 5 + [260]},
    "running": {"row": 7, "frames": 6, "durations": [120] * 5 + [220]},
    "review": {"row": 8, "frames": 6, "durations": [150] * 5 + [280]},
}

LOOK_DIRECTIONS = [
    0.0, 22.5, 45.0, 67.5, 90.0, 112.5, 135.0, 157.5,
    180.0, 202.5, 225.0, 247.5, 270.0, 292.5, 315.0, 337.5,
]


class EriiDesktopPet:
    def __init__(self, atlas_path: Path) -> None:
        self.root = tk.Tk()
        self.root.title("绘梨衣")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=KEY_HEX)
        try:
            self.root.wm_attributes("-transparentcolor", KEY_HEX)
            self.root.wm_attributes("-toolwindow", True)
        except tk.TclError:
            pass

        self.canvas = tk.Canvas(
            self.root,
            width=CELL_W,
            height=CELL_H,
            bg=KEY_HEX,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()

        self.atlas = Image.open(atlas_path).convert("RGBA")
        if self.atlas.size != (CELL_W * 8, CELL_H * 11):
            raise ValueError(f"Unexpected atlas size: {self.atlas.size}")

        self.frames: dict[str, list[ImageTk.PhotoImage]] = {}
        self.look_frames: list[ImageTk.PhotoImage] = []
        self._load_frames()

        self.image_item = self.canvas.create_image(0, 0, anchor="nw")
        self.current_state = "idle"
        self.frame_index = 0
        self.loops_remaining: int | None = None
        self.drag_origin: tuple[int, int, int, int] | None = None
        self.dragged = False
        self.always_on_top = True
        self.random_actions = True
        self.next_random_action = time.monotonic() + random.uniform(6.0, 11.0)

        self.menu = tk.Menu(self.root, tearoff=False)
        self.menu.add_command(label="挥手", command=lambda: self.play("waving"))
        self.menu.add_command(label="跳一下", command=lambda: self.play("jumping"))
        self.menu.add_command(label="向左散步", command=lambda: self.play("running-left", loops=2))
        self.menu.add_command(label="向右散步", command=lambda: self.play("running-right", loops=2))
        self.menu.add_separator()
        self.menu.add_command(label="等待", command=lambda: self.play("waiting", loops=2))
        self.menu.add_command(label="专注", command=lambda: self.play("running", loops=2))
        self.menu.add_command(label="检查", command=lambda: self.play("review", loops=2))
        self.menu.add_command(label="有点难过", command=lambda: self.play("failed"))
        self.menu.add_command(label="回到待机", command=self.go_idle)
        self.menu.add_separator()
        self.menu.add_checkbutton(
            label="始终置顶",
            command=self.toggle_topmost,
            variable=tk.BooleanVar(value=True),
        )
        self.menu.add_checkbutton(
            label="随机小动作",
            command=self.toggle_random_actions,
            variable=tk.BooleanVar(value=True),
        )
        self.menu.add_separator()
        self.menu.add_command(label="退出绘梨衣", command=self.close)

        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.end_drag)
        self.canvas.bind("<Double-Button-1>", lambda _event: self.play("waving"))
        self.canvas.bind("<MouseWheel>", lambda _event: self.play("jumping"))
        self.canvas.bind("<Button-3>", self.show_menu)

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._place_initially()
        self._tick()

    def _make_photo(self, frame: Image.Image) -> ImageTk.PhotoImage:
        rgba = frame.convert("RGBA")
        pixels = []
        for red, green, blue, alpha in rgba.getdata():
            if alpha <= 12:
                pixels.append((*KEY_COLOR, 255))
            else:
                pixels.append((red, green, blue, 255))
        keyed = Image.new("RGBA", rgba.size)
        keyed.putdata(pixels)
        return ImageTk.PhotoImage(keyed)

    def _crop_cell(self, row: int, column: int) -> Image.Image:
        left = column * CELL_W
        top = row * CELL_H
        return self.atlas.crop((left, top, left + CELL_W, top + CELL_H))

    def _load_frames(self) -> None:
        for state, spec in ANIMATIONS.items():
            self.frames[state] = [
                self._make_photo(self._crop_cell(spec["row"], column))
                for column in range(spec["frames"])
            ]
        for index in range(16):
            row = 9 if index < 8 else 10
            column = index if index < 8 else index - 8
            self.look_frames.append(self._make_photo(self._crop_cell(row, column)))

    def _place_initially(self) -> None:
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        # Start in the center so mixed-DPI or multi-monitor taskbar geometry
        # cannot place the borderless window just outside the visible desktop.
        x = max(0, (screen_w - CELL_W) // 2)
        y = max(0, (screen_h - CELL_H) // 2)
        self.root.geometry(f"{CELL_W}x{CELL_H}+{x}+{y}")
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)

    def play(self, state: str, loops: int = 1) -> None:
        if state not in ANIMATIONS:
            return
        self.current_state = state
        self.frame_index = 0
        self.loops_remaining = None if state == "idle" else max(1, loops)
        self.next_random_action = time.monotonic() + random.uniform(7.0, 13.0)

    def go_idle(self) -> None:
        self.current_state = "idle"
        self.frame_index = 0
        self.loops_remaining = None

    def _look_frame(self) -> ImageTk.PhotoImage | None:
        if self.current_state != "idle" or self.drag_origin is not None:
            return None
        pointer_x = self.root.winfo_pointerx()
        pointer_y = self.root.winfo_pointery()
        center_x = self.root.winfo_rootx() + CELL_W / 2
        center_y = self.root.winfo_rooty() + CELL_H / 2
        dx = pointer_x - center_x
        dy = pointer_y - center_y
        distance = math.hypot(dx, dy)
        if distance < 75 or distance > 900:
            return None
        degrees = (math.degrees(math.atan2(dx, -dy)) + 360.0) % 360.0
        index = int((degrees + 11.25) // 22.5) % 16
        return self.look_frames[index]

    def _move_for_walk(self) -> None:
        if self.current_state not in ("running-left", "running-right"):
            return
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        step = -8 if self.current_state == "running-left" else 8
        max_x = max(0, self.root.winfo_screenwidth() - CELL_W)
        new_x = min(max(x + step, 0), max_x)
        self.root.geometry(f"+{new_x}+{y}")
        if new_x in (0, max_x):
            self.go_idle()

    def _maybe_random_action(self) -> None:
        if not self.random_actions or self.current_state != "idle":
            return
        now = time.monotonic()
        if now < self.next_random_action:
            return
        choice = random.choices(
            ["waving", "jumping", "running-left", "running-right", "review"],
            weights=[4, 2, 2, 2, 1],
            k=1,
        )[0]
        loops = 2 if choice.startswith("running-") else 1
        self.play(choice, loops=loops)

    def _tick(self) -> None:
        self._maybe_random_action()
        look = self._look_frame()
        photos = self.frames[self.current_state]
        photo = look if look is not None else photos[self.frame_index]
        self.canvas.itemconfigure(self.image_item, image=photo)
        self.canvas.image = photo

        self._move_for_walk()
        spec = ANIMATIONS[self.current_state]
        delay = spec["durations"][self.frame_index]
        self.frame_index += 1
        if self.frame_index >= len(photos):
            self.frame_index = 0
            if self.loops_remaining is not None:
                self.loops_remaining -= 1
                if self.loops_remaining <= 0:
                    self.go_idle()
        self.root.after(delay, self._tick)

    def start_drag(self, event: tk.Event) -> None:
        self.drag_origin = (event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y())
        self.dragged = False

    def drag(self, event: tk.Event) -> None:
        if self.drag_origin is None:
            return
        start_x, start_y, window_x, window_y = self.drag_origin
        dx = event.x_root - start_x
        dy = event.y_root - start_y
        self.dragged = self.dragged or abs(dx) + abs(dy) > 4
        max_x = max(0, self.root.winfo_screenwidth() - CELL_W)
        max_y = max(0, self.root.winfo_screenheight() - CELL_H)
        x = min(max(window_x + dx, 0), max_x)
        y = min(max(window_y + dy, 0), max_y)
        self.root.geometry(f"+{x}+{y}")

    def end_drag(self, _event: tk.Event) -> None:
        self.drag_origin = None

    def show_menu(self, event: tk.Event) -> None:
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def toggle_topmost(self) -> None:
        self.always_on_top = not self.always_on_top
        self.root.attributes("-topmost", self.always_on_top)

    def toggle_random_actions(self) -> None:
        self.random_actions = not self.random_actions
        self.next_random_action = time.monotonic() + random.uniform(6.0, 11.0)

    def close(self) -> None:
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def self_test(atlas_path: Path) -> int:
    atlas = Image.open(atlas_path).convert("RGBA")
    errors = []
    if atlas.size != (1536, 2288):
        errors.append(f"atlas size is {atlas.size}, expected (1536, 2288)")
    checked = 0
    for state, spec in ANIMATIONS.items():
        for column in range(spec["frames"]):
            cell = atlas.crop((column * CELL_W, spec["row"] * CELL_H, (column + 1) * CELL_W, (spec["row"] + 1) * CELL_H))
            if cell.getbbox() is None:
                errors.append(f"blank frame: {state}/{column}")
            checked += 1
    for index in range(16):
        row = 9 if index < 8 else 10
        column = index if index < 8 else index - 8
        cell = atlas.crop((column * CELL_W, row * CELL_H, (column + 1) * CELL_W, (row + 1) * CELL_H))
        if cell.getbbox() is None:
            errors.append(f"blank look frame: {LOOK_DIRECTIONS[index]}")
        checked += 1
    print(json.dumps({"ok": not errors, "atlas": str(atlas_path), "framesChecked": checked, "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="绘梨衣独立 Windows 桌面宠物")
    parser.add_argument("--self-test", action="store_true", help="验证图集和动画帧后退出")
    args = parser.parse_args()
    atlas_path = Path(__file__).resolve().with_name("spritesheet.webp")
    if args.self_test:
        return self_test(atlas_path)
    mutex_name = "Local\\EriiDesktopPet.Singleton"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if ctypes.windll.kernel32.GetLastError() == 183:
        ctypes.windll.kernel32.CloseHandle(mutex)
        return 0
    try:
        EriiDesktopPet(atlas_path).run()
        return 0
    finally:
        ctypes.windll.kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    raise SystemExit(main())
