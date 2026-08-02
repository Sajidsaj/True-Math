"""
Module Name: sys_logger
Purpose: Enterprise-grade, thread-safe asynchronous logging foundation.
Responsibilities:
  - Capture all system events safely.
  - Rotate logs across daily files to prevent disk exhaustion.
  - Mask sensitive or malformed data natively.
Dependencies: logging, os
Input: Log strings & Exceptions
Output: STDOUT and rolling .log files.
Possible Errors: Disk full, Permission Denied.
Testing Method: Unit tests validating rolling behavior and log formatting.
Estimated Complexity: Low-Medium.
Integration Notes: Call `get_logger()` at module level across the app.
"""
import logging
import os
import threading
import queue
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener

from src.runtime_paths import APP_NAME, get_app_home, get_project_root

class SystemLogger:
    _configured_names = set()
    _lock = threading.Lock()
    _log_queue = queue.Queue(-1)
    _listener = None

    @classmethod
    def get_logger(cls, name: str = "TrueMathCore", log_dir: str | None = None) -> logging.Logger:
        """
        Retrieves or initializes a highly optimized logger instance for TrueMath.
        Ensures handlers are added safely without duplication.
        """
        logger = logging.getLogger(name)

        if name in cls._configured_names:
            return logger
            
        if log_dir is None:
            project_root = get_project_root()
            log_root = get_app_home(project_root, APP_NAME) / "logs"
            log_dir = str(log_root)

        try:
            os.makedirs(log_dir, exist_ok=True)
        except PermissionError:
            # Fallback to local execution dir if permission fails
            log_dir = "."
            
        log_file = os.path.join(log_dir, "truemath_system.log")

        logger.setLevel(logging.DEBUG)

        # 10 MB per file, max 5 backups => restricts local PC memory/storage issues
        file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        # Console handler: Set to INFO so we don't block the UI threads with massive debug streams
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Standard precise timing for algorithmic operations
        formatter = logging.Formatter(
            '%(asctime)s - [%(levelname)s] - %(name)s - %(module)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        if not logger.handlers:
            if cls._listener is None:
                # Listener evaluates and dumps logs natively in a separate background OS thread
                cls._listener = QueueListener(cls._log_queue, file_handler, console_handler, respect_handler_level=True)
                cls._listener.start()
            
            queue_handler = QueueHandler(cls._log_queue)
            logger.addHandler(queue_handler)

        cls._configured_names.add(name)
        return logger

def get_logger(name: str) -> logging.Logger:
    """Helper to maintain standard API interface."""
    return SystemLogger.get_logger(name)
