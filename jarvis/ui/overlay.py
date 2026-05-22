from __future__ import annotations

import atexit
import json
import socket
import subprocess
import sys
import threading
import time
from queue import Empty, Queue
from pathlib import Path
from typing import Any

try:
    import webview  # type: ignore[import-not-found]
except ImportError:
    webview = None


class OverlayUI:
    def __init__(self) -> None:
        self._state = "idle"
        self._detail = "En espera"
        self._window: Any | None = None
        self._html_path = Path(__file__).with_name("index.html")
        self._backend = "pywebview" if webview is not None else "tkinter"
        self._thread: threading.Thread | None = None
        self._webview_process: subprocess.Popen | None = None
        self._webview_port: int | None = None
        self._tk_root = None
        self._tk_label = None
        self._tk_detail_label = None
        self._tk_title_label = None
        self._tk_frame = None
        self._tk_canvas = None
        self._tk_bar_canvas = None
        self._tk_status_dot = None
        self._tk_bars = []
        self._visible = False
        self._hide_after_id = None
        self._command_queue: Queue[tuple[str, tuple[Any, ...]]] = Queue()
        self._window_width = 520
        self._window_height = 680
        self._window_margin = 28
        atexit.register(self.close)

    def start(self) -> None:
        if self._backend == "pywebview":
            self._start_pywebview_process()
            return

        if self._thread is not None:
            return

        self._thread = threading.Thread(target=self._start_tkinter, daemon=True)
        self._thread.start()

    def set_state(self, state: str) -> None:
        self._state = state
        self._dispatch("set_state", state)
        if state != "idle":
            self.show()
        else:
            self.clear_camera_preview()
            self.hide(delay_ms=2200)

    def set_detail(self, text: str) -> None:
        self._detail = text.strip() or "En espera"
        self._dispatch("set_detail", self._detail)

    def set_camera_preview(self, image_data_url: str, label: str = "VISION FEED") -> None:
        self._dispatch("set_camera_preview", image_data_url, label)

    def clear_camera_preview(self) -> None:
        self._dispatch("clear_camera_preview")

    def set_security_status(self, state: str, label: str) -> None:
        self._dispatch("set_security_status", state, label)

    def show(self) -> None:
        self._visible = True
        self._dispatch("show")

    def hide(self, delay_ms: int = 0) -> None:
        self._visible = False
        self._dispatch("hide", delay_ms)

    def activate(self, state: str, detail: str) -> None:
        self.set_detail(detail)
        self.set_state(state)

    def close(self) -> None:
        if self._webview_process is None:
            return
        if self._webview_process.poll() is not None:
            return

        self._webview_process.terminate()
        try:
            self._webview_process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._webview_process.kill()

    def _dispatch(self, action: str, *args: Any) -> None:
        if self._backend == "pywebview":
            self._send_webview_command(action, *args)
            return

        self._command_queue.put((action, args))

    def _apply_state(self, state: str) -> None:
        palettes = {
            "idle": {"frame": "#06111c", "ring": "#2dd4ff", "orb": "#37c8ff", "text": "#dffbff"},
            "listening": {"frame": "#041b26", "ring": "#22d3ee", "orb": "#51f3ff", "text": "#dcfcff"},
            "thinking": {"frame": "#140b28", "ring": "#8b5cf6", "orb": "#a78bfa", "text": "#efe7ff"},
            "speaking": {"frame": "#06261f", "ring": "#00f5a0", "orb": "#44ffbf", "text": "#e6fff5"},
        }
        palette = palettes.get(state, palettes["idle"])

        if self._backend == "tkinter" and self._tk_root is not None:
            self._tk_root.configure(bg=palette["frame"])
            if self._tk_frame is not None:
                self._tk_frame.configure(bg=palette["frame"], highlightbackground=palette["ring"])
            if self._tk_canvas is not None:
                self._tk_canvas.configure(bg=palette["frame"], highlightthickness=0)
                self._tk_canvas.itemconfig("ring", outline=palette["ring"])
                self._tk_canvas.itemconfig("soft_ring", outline=palette["ring"])
                self._tk_canvas.itemconfig("orb", fill=palette["orb"], outline=palette["ring"])
                self._tk_canvas.itemconfig("dot", fill=palette["ring"])
                self._tk_canvas.itemconfig("scan", fill=palette["ring"])
            if self._tk_bar_canvas is not None:
                self._tk_bar_canvas.configure(bg=palette["frame"], highlightthickness=0)
                self._tk_bar_canvas.itemconfig("bar", fill=palette["ring"])
            if self._tk_label is not None:
                self._tk_label.config(text=state.upper(), fg=palette["text"], bg=palette["frame"])
            if self._tk_detail_label is not None:
                self._tk_detail_label.config(fg=palette["text"], bg=palette["frame"])
            if self._tk_title_label is not None:
                self._tk_title_label.config(fg=palette["ring"], bg=palette["frame"])
            if self._tk_status_dot is not None:
                self._tk_status_dot.configure(bg=palette["frame"], highlightthickness=0)
                self._tk_status_dot.itemconfig("dot", fill=palette["ring"])
        elif self._backend == "pywebview" and self._window is not None:
            try:
                self._window.evaluate_js(f"window.jarvisUi.setState({json.dumps(state)})")
            except Exception:
                pass

    @property
    def state(self) -> str:
        return self._state

    def _start_pywebview_process(self) -> None:
        if webview is None:
            return

        if self._webview_process is not None and self._webview_process.poll() is None:
            return

        self._webview_port = self._find_free_port()
        command = [
            sys.executable,
            "-m",
            "jarvis.ui.webview_overlay",
            "--port",
            str(self._webview_port),
            "--html",
            str(self._html_path),
            "--width",
            str(self._window_width),
            "--height",
            str(self._window_height),
            "--margin",
            str(self._window_margin),
        ]
        self._webview_process = subprocess.Popen(
            command,
            cwd=str(Path.cwd()),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        self._wait_for_webview_server()

    def _send_webview_command(self, action: str, *args: Any) -> None:
        if self._webview_port is None:
            return

        payload = json.dumps({"action": action, "args": list(args)}, ensure_ascii=False).encode("utf-8")
        for _ in range(3):
            try:
                with socket.create_connection(("127.0.0.1", self._webview_port), timeout=0.2) as connection:
                    connection.sendall(payload)
                return
            except OSError:
                time.sleep(0.05)

    def _wait_for_webview_server(self) -> None:
        if self._webview_port is None:
            return

        deadline = time.time() + 3
        while time.time() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", self._webview_port), timeout=0.2):
                    return
            except OSError:
                time.sleep(0.05)

    def _find_free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            return int(probe.getsockname()[1])

    def _start_tkinter(self) -> None:
        import tkinter as tk

        root = tk.Tk()
        root.title("Jarvis")
        self._apply_tk_geometry(root)
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg="#040d19")
        root.withdraw()

        frame = tk.Frame(root, bg="#06111c", highlightthickness=1, highlightbackground="#2dd4ff")
        frame.place(relx=0.5, rely=0.5, anchor="center", width=318, height=360)

        title = tk.Label(
            frame,
            text="JARVIS",
            fg="#58e1ff",
            bg="#06111c",
            font=("Bahnschrift", 18, "bold"),
        )
        title.place(x=24, y=24, anchor="w")

        status_dot = tk.Canvas(frame, width=16, height=16, bg="#06111c", highlightthickness=0)
        status_dot.place(x=268, y=24, anchor="center")
        status_dot.create_oval(3, 3, 13, 13, fill="#2dd4ff", outline="", tags="dot")

        canvas = tk.Canvas(frame, width=240, height=240, bg="#06111c", highlightthickness=0)
        canvas.place(relx=0.5, y=162, anchor="center")
        canvas.create_oval(25, 25, 215, 215, outline="#1d6f85", width=1, tags="soft_ring")
        canvas.create_oval(44, 44, 196, 196, outline="#58e1ff", width=2, tags="ring")
        canvas.create_oval(76, 76, 164, 164, outline="#1d6f85", width=1, tags="soft_ring")
        canvas.create_oval(88, 88, 152, 152, fill="#37c8ff", outline="#58e1ff", width=2, tags="orb")
        canvas.create_rectangle(38, 119, 202, 121, fill="#58e1ff", outline="", tags="scan")
        for x, y in [(120, 30), (190, 68), (198, 170), (120, 212), (44, 168), (52, 72)]:
            canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill="#58e1ff", outline="", tags="dot")

        bar_canvas = tk.Canvas(frame, width=210, height=38, bg="#06111c", highlightthickness=0)
        bar_canvas.place(relx=0.5, y=270, anchor="center")
        bars = []
        for index in range(10):
            x = 24 + index * 18
            bar = bar_canvas.create_rectangle(x, 14, x + 5, 24, fill="#58e1ff", outline="", tags="bar")
            bars.append(bar)

        label = tk.Label(
            frame,
            text=self._state.upper(),
            fg="#dffbff",
            bg="#06111c",
            font=("Bahnschrift", 13, "bold"),
        )
        label.place(x=24, y=50, anchor="w")

        detail_label = tk.Label(
            frame,
            text=self._detail,
            fg="#dffbff",
            bg="#06111c",
            font=("Segoe UI", 10),
            wraplength=260,
            justify="center",
        )
        detail_label.place(relx=0.5, y=318, anchor="center")

        self._tk_root = root
        self._tk_frame = frame
        self._tk_label = label
        self._tk_detail_label = detail_label
        self._tk_title_label = title
        self._tk_canvas = canvas
        self._tk_bar_canvas = bar_canvas
        self._tk_status_dot = status_dot
        self._tk_bars = bars

        root.after(50, self._process_tk_commands)
        root.after(200, self._pulse_tkinter)
        root.mainloop()

    def _pulse_tkinter(self) -> None:
        if self._tk_root is None:
            return

        if self._visible and self._tk_canvas is not None:
            speed = 7 if self._state in {"listening", "speaking"} else 3
            phase = int(time.time() * speed) % 6
            scale_map = [0, 2, 4, 2, 0, -2]
            pulse = scale_map[phase]
            outer = 44 - pulse
            inner = 88 - pulse // 2
            self._tk_canvas.coords("ring", outer, outer, 240 - outer, 240 - outer)
            self._tk_canvas.coords("orb", inner, inner, 240 - inner, 240 - inner)
            scan_y = 68 + ((phase * 18) % 104)
            self._tk_canvas.coords("scan", 38, scan_y, 202, scan_y + 2)

            if self._tk_bar_canvas is not None and self._tk_bars:
                active = self._state in {"listening", "speaking"}
                heights = [10, 18, 26, 14, 30, 22, 12, 24, 16, 28] if active else [8, 12, 10, 14, 9, 13, 10, 12, 8, 11]
                for index, bar in enumerate(self._tk_bars):
                    height = heights[(index + phase) % len(heights)]
                    x = 24 + index * 18
                    center = 19
                    self._tk_bar_canvas.coords(bar, x, center - height // 2, x + 5, center + height // 2)
        self._tk_root.after(250, self._pulse_tkinter)

    def _process_tk_commands(self) -> None:
        if self._tk_root is None:
            return

        while True:
            try:
                action, args = self._command_queue.get_nowait()
            except Empty:
                break

            if action == "set_state":
                self._apply_state(args[0])
            elif action == "set_detail" and self._tk_detail_label is not None:
                self._tk_detail_label.config(text=args[0])
            elif action == "show":
                if self._hide_after_id is not None:
                    self._tk_root.after_cancel(self._hide_after_id)
                    self._hide_after_id = None
                self._apply_tk_geometry(self._tk_root)
                self._tk_root.deiconify()
                self._tk_root.lift()
                self._tk_root.attributes("-topmost", True)
                self._visible = True
            elif action == "hide":
                delay_ms = int(args[0]) if args else 0
                if self._hide_after_id is not None:
                    self._tk_root.after_cancel(self._hide_after_id)
                    self._hide_after_id = None
                if delay_ms <= 0:
                    self._tk_root.withdraw()
                    self._visible = False
                else:
                    self._hide_after_id = self._tk_root.after(delay_ms, self._hide_now)

        self._tk_root.after(50, self._process_tk_commands)

    def _hide_now(self) -> None:
        if self._tk_root is None:
            return
        self._tk_root.withdraw()
        self._visible = False
        self._hide_after_id = None

    def _apply_tk_geometry(self, root: Any) -> None:
        root.update_idletasks()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = max(0, screen_width - self._window_width - self._window_margin)
        y = max(0, screen_height - self._window_height - self._window_margin - 40)
        root.geometry(f"{self._window_width}x{self._window_height}+{x}+{y}")
