import os
import sys
from pathlib import Path
import webview

from .web_api import WebApi

def run_gui():
    # Resolve web directory
    web_dir = Path(__file__).parent / "web"
    index_html = web_dir / "index.html"

    if not index_html.exists():
        raise FileNotFoundError(f"Web interface files not found: {index_html}")

    api = WebApi()

    # Create PyWebView native macOS WebKit window
    window = webview.create_window(
        title="novelturk-dl",
        url=str(index_html.resolve()),
        js_api=api,
        width=1100,
        height=720,
        min_size=(860, 520),
        background_color="#090a0f",
        easy_drag=False
    )

    api.set_window(window)
    webview.start(debug=False)

if __name__ == "__main__":
    run_gui()
