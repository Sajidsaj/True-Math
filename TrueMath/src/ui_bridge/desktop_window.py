from __future__ import annotations

from src.core.sys_logger import get_logger


logger = get_logger("DesktopWindow")


def launch_desktop_window(url: str, title: str, width: int, height: int, debug: bool = False) -> None:
    try:
        import webview
    except ImportError as exc:
        raise RuntimeError(
            "pywebview is required for desktop mode. Install dependencies from requirements.txt."
        ) from exc

    logger.info("Launching desktop shell window.")
    webview.create_window(
        title=title,
        url=url,
        width=width,
        height=height,
        text_select=True,
        confirm_close=True,
    )
    webview.start(debug=debug)
