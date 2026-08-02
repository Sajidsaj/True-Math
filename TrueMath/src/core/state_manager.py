"""
Module Name: state_manager
Purpose: Handle application epochs and save MCTS graphs safely to prevent data loss.
Responsibilities:
  - Connect to local SQLite database efficiently.
  - Serialize AI tree and state variables every interval.
  - Provide automatic crash recovery interface.
Dependencies: sqlite3, json, zlib (for compression)
Input: Python Dictionaries representing Math state.
Output: Persistent state in SQLite database.
Possible Errors: SQLite lock timeout, Database corruption.
Testing Method: Integration test simulating save/load.
Estimated Complexity: Medium.
Integration Notes: Requires `sys_logger` for internal error reporting.
"""
import sqlite3
import json
import zlib
from typing import Any, Dict, Optional
from contextlib import contextmanager
from src.core.sys_logger import get_logger

logger = get_logger("StateManager")

class EpochStateManager:
    def __init__(self, db_path: str = "truemath_state.db"):
        self.db_path = db_path
        self._initialize_db()

    @contextmanager
    def _get_connection(self):
        """Creates a new SQLite connect context executing high-speed PRAGMAs natively and ensures clean closure."""
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA temp_store = MEMORY")
        conn.execute("PRAGMA cache_size = -64000")  # 64 MB
        try:
            yield conn
        finally:
            conn.close()

    def _initialize_db(self) -> None:
        """Bootstraps the schema for storing epochs."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # We use compression BLOB because math trees can get huge
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS epoch_state (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        epoch_id TEXT UNIQUE NOT NULL,
                        compressed_data BLOB NOT NULL
                    )
                ''')
                conn.commit()
            logger.info(f"Database initialized securely at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize state database: {e}")
            raise

    def save_epoch(self, epoch_id: str, state_data: Dict[str, Any]) -> bool:
        """Compresses and safely writes an AI epoch to disk."""
        try:
            serialized = json.dumps(state_data).encode("utf-8")
            compressed: bytes = zlib.compress(serialized)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO epoch_state (epoch_id, compressed_data) VALUES (?, ?)",
                    (epoch_id, compressed)
                )
                conn.commit()
            logger.debug(f"Epoch {epoch_id} saved. Payload Size (Compressed): {len(compressed)} bytes.")
            return True
        except Exception as e:
            logger.error(f"Failed to save epoch {epoch_id}: {e}", exc_info=True)
            return False

    def load_latest_epoch(self) -> Optional[Dict[str, Any]]:
        """Recovers the most recent state from disk to resume computations."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT epoch_id, compressed_data FROM epoch_state ORDER BY timestamp DESC LIMIT 1")
                row = cursor.fetchone()
                
            if row is None:
                logger.info("No previous epoch state found. System starting fresh.")
                return None
                
            epoch_id, compressed = row
            decompressed = zlib.decompress(compressed).decode("utf-8")
            logger.info(f"Successfully recovered Epoch: {epoch_id} for resumption.")
            return json.loads(decompressed)
        except Exception as e:
            logger.error(f"Critical error loading latest epoch. Check db integrity: {e}", exc_info=True)
            return None
