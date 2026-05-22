from __future__ import annotations

import argparse
import ctypes
import json
import socket
import threading
import time
from pathlib import Path
from queue import Empty, Queue
from typing import Any

import webview


def run_command_server(port: int, command_queue: Queue[dict[str, Any]]) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", port))
        server.listen()

        while True:
            connection, _ = server.accept()
            with connection:
                chunks: list[bytes] = []
                while True:
                    chunk = connection.recv(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)

                payload = b"".join(chunks)
                if not payload:
                    continue

                try:
                    command = json.loads(payload.decode("utf-8"))
                except json.JSONDecodeError:
                    continue

                if isinstance(command, dict):
                    command_queue.put(command)


def process_commands(window: Any, command_queue: Queue[dict[str, Any]]) -> None:
    hide_at: float | None = None

    while True:
        if hide_at is not None and time.time() >= hide_at:
            try:
                window.hide()
            except Exception:
                pass
            hide_at = None

        try:
            command = command_queue.get(timeout=0.05)
        except Empty:
            continue

        action = str(command.get("action", ""))
        args = command.get("args", [])
        if not isinstance(args, list):
            args = []

        try:
            if action == "set_state":
                state = str(args[0]) if args else "idle"
                window.evaluate_js(f"window.jarvisUi.setState({json.dumps(state)})")
            elif action == "set_detail":
                detail = str(args[0]) if args else "En espera"
                window.evaluate_js(f"window.jarvisUi.setDetail({json.dumps(detail)})")
            elif action == "set_camera_preview":
                image_data_url = str(args[0]) if args else ""
                label = str(args[1]) if len(args) > 1 else "VISION FEED"
                window.evaluate_js(
                    "window.jarvisUi.setCameraPreview("
                    f"{json.dumps(image_data_url)}, {json.dumps(label)}"
                    ")"
                )
            elif action == "clear_camera_preview":
                window.evaluate_js("window.jarvisUi.clearCameraPreview()")
            elif action == "set_security_status":
                state = str(args[0]) if args else "unknown"
                label = str(args[1]) if len(args) > 1 else "SIN IDENTIFICAR"
                window.evaluate_js(
                    "window.jarvisUi.setSecurityStatus("
                    f"{json.dumps(state)}, {json.dumps(label)}"
                    ")"
                )
            elif action == "show":
                hide_at = None
                window.show()
            elif action == "hide":
                delay_ms = int(args[0]) if args else 0
                if delay_ms <= 0:
                    window.hide()
                    hide_at = None
                else:
                    hide_at = time.time() + (delay_ms / 1000)
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Jarvis pywebview overlay process")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--html", type=str, required=True)
    parser.add_argument("--width", type=int, default=360)
    parser.add_argument("--height", type=int, default=410)
    parser.add_argument("--margin", type=int, default=28)
    args = parser.parse_args()

    command_queue: Queue[dict[str, Any]] = Queue()
    server_thread = threading.Thread(
        target=run_command_server,
        args=(args.port, command_queue),
        daemon=True,
    )
    server_thread.start()

    html_path = Path(args.html).resolve()
    x, y = bottom_right_position(args.width, args.height, args.margin)
    window = webview.create_window(
        "Jarvis",
        url=html_path.as_uri(),
        width=args.width,
        height=args.height,
        x=x,
        y=y,
        frameless=True,
        on_top=True,
        transparent=True,
        easy_drag=True,
        hidden=True,
    )
    webview.start(process_commands, (window, command_queue))


def bottom_right_position(width: int, height: int, margin: int) -> tuple[int | None, int | None]:
    if not hasattr(ctypes, "windll"):
        return None, None

    user32 = ctypes.windll.user32
    screen_width = int(user32.GetSystemMetrics(0))
    screen_height = int(user32.GetSystemMetrics(1))
    taskbar_offset = 40
    x = max(0, screen_width - width - margin)
    y = max(0, screen_height - height - margin - taskbar_offset)
    return x, y


if __name__ == "__main__":
    main()
