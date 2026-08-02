"""
main.py — TrueMath Application Entry Point
-------------------------------------------
Run this file to start the entire autonomous math research engine:
  python main.py
"""
import os
import sys
import time
import webbrowser

# Ensure the project root is on sys.path so `import config` works
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from src.core.sys_logger import get_logger
from src.core.orchestrator import TrueMathOrchestrator
from src.ui_bridge.dashboard_server import DashboardServer
from src.ui_bridge.desktop_window import launch_desktop_window

logger = get_logger("Main")


def _run_headless_loop() -> None:
    if config.BROWSER_AUTO_OPEN:
        webbrowser.open(f"http://{config.DASHBOARD_HOST}:{config.DASHBOARD_PORT}")
    else:
        logger.info("Browser auto-open disabled for headless/session automation mode.")

    if config.AUTO_EXIT_AFTER_SECONDS > 0:
        logger.info(f"Auto-exit armed for {config.AUTO_EXIT_AFTER_SECONDS}s.")
        time.sleep(config.AUTO_EXIT_AFTER_SECONDS)
        return

    while True:
        time.sleep(1)


def main() -> None:
    config.ensure_runtime_dirs()
    config.validate_runtime()

    logger.info("=" * 60)
    logger.info(f"  {config.APP_NAME} v{config.APP_VERSION}")
    logger.info("  Starting up — all systems warming.")
    logger.info("=" * 60)

    logger.info("Using cloud LLM providers (Groq / OpenRouter) — no local model to warm up.")

    brain     = TrueMathOrchestrator()
    dashboard = DashboardServer(
        asset_dir=config.DASHBOARD_ASSET_DIR,
        port=config.DASHBOARD_PORT,
        host=config.DASHBOARD_HOST,
        runtime_config={
            "appVersion": config.APP_VERSION,
            "ipcHost": config.IPC_HOST,
            "ipcPort": config.IPC_PORT,
            "ipcPath": "/ws",
        },
    )

    try:
        brain.start()
        dashboard.start()

        dashboard_url = f"http://{config.DASHBOARD_HOST}:{config.DASHBOARD_PORT}"

        logger.info(
            f"Dashboard : {dashboard_url}\n"
            f"IPC WS    : ws://{config.IPC_HOST}:{config.IPC_PORT}\n"
            "Press Ctrl+C to shut down gracefully."
        )

        if config.DESKTOP_MODE:
            launch_desktop_window(
                url=dashboard_url,
                title=f"{config.APP_NAME} {config.APP_VERSION}",
                width=config.DESKTOP_WIDTH,
                height=config.DESKTOP_HEIGHT,
                debug=config.DESKTOP_DEBUG,
            )
        else:
            _run_headless_loop()

    except KeyboardInterrupt:
        logger.info("Ctrl+C received — shutting down.")
    finally:
        brain.stop()
        dashboard.stop()
        logger.info("TrueMath Engine cleanly stopped. Goodbye.")


if __name__ == "__main__":
    main()
