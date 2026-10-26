#!/usr/bin/env python3
"""
Self-Bootstrapping Launcher for Zalo Attendance System (Milestone 3).

Features:
- Validates Python version (>= 3.10 recommended, >= 3.9 required)
- Auto-detects free port starting at 8000 (fallback up to 8080)
- Launches browser to http://127.0.0.1:<port>/
- Boots Uvicorn ASGI server with main:app
- Parses CLI arguments: --host, --port, --no-browser, --reload
"""

import os
import sys
import time
import socket
import argparse
import threading
import webbrowser

# Validate Python version
MIN_VERSION = (3, 10)
if sys.version_info < (3, 9):
    print(f"[FATAL] Python >= 3.9 is strictly required. Detected {sys.version.split()[0]}.")
    sys.exit(1)
elif sys.version_info < MIN_VERSION:
    print(f"[WARN] Recommended Python version is >= 3.10. Running with {sys.version.split()[0]}.")

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Checks whether a TCP port is currently bound/in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def find_free_port(host: str = "127.0.0.1", start_port: int = 8000, max_port: int = 8080) -> int:
    """Finds an available TCP port in the specified range."""
    for p in range(start_port, max_port + 1):
        if not is_port_in_use(p, host):
            # Double check with bind attempt
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind((host, p))
                    return p
            except OSError:
                continue
    return start_port


def print_banner(host: str, port: int):
    """Displays terminal welcome banner."""
    print("=" * 72)
    print("      ZALO ATTENDANCE BOT - BÓC TÁCH & ĐIỀN EXCEL TỰ ĐỘNG")
    print("=" * 72)
    print(f"  ➜ Dashboard URL  : http://{host}:{port}/")
    print(f"  ➜ API Docs (UI)  : http://{host}:{port}/docs")
    print(f"  ➜ Python Runtime : {sys.executable}")
    print(f"  ➜ Working Dir    : {PROJECT_ROOT}")
    print("-" * 72)
    print("  Nhấn Ctrl+C để dừng máy chủ.")
    print("=" * 72)


def open_browser(url: str, delay_seconds: float = 0.8):
    """Opens default browser after a short delay."""
    time.sleep(delay_seconds)
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"[INFO] Could not auto-open browser: {e}")


def main():
    parser = argparse.ArgumentParser(description="Zalo Attendance Bot Launcher")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Initial port to bind (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch browser")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on code change")

    args = parser.parse_args()

    # Check dependencies
    try:
        import uvicorn
        import fastapi
        import openpyxl
        import pydantic
    except ImportError as e:
        print(f"[FATAL] Missing required dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        sys.exit(1)

    # Resolve free port
    chosen_port = args.port
    if is_port_in_use(chosen_port, args.host):
        print(f"[INFO] Port {chosen_port} is busy. Probing for free port...")
        chosen_port = find_free_port(args.host, start_port=chosen_port + 1, max_port=8080)
        print(f"[INFO] Selected available port: {chosen_port}")

    app_url = f"http://{args.host}:{chosen_port}/"
    print_banner(args.host, chosen_port)

    # Launch browser in background thread
    if not args.no_browser:
        threading.Thread(target=open_browser, args=(app_url,), daemon=True).start()

    # Run Uvicorn server
    uvicorn.run("main:app", host=args.host, port=chosen_port, reload=args.reload)


if __name__ == "__main__":
    main()
