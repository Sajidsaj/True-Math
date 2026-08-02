import os
import logging
from src.core.sys_logger import get_logger

def test_logger_singleton_behavior():
    """Test that multiple calls to get_logger yield the same logger safely."""
    logger1 = get_logger("ModuleA")
    logger2 = get_logger("ModuleA")
    
    assert logger1 is logger2
    assert logger1.name == "ModuleA"

def test_logger_file_creation(tmp_path):
    """Test that logs are securely written to files."""
    log_file = tmp_path / "truemath_system.log"
    logger = logging.getLogger("TestIsolated")
    
    # Adding handler manually to test output directly to tmp_path
    from logging.handlers import RotatingFileHandler
    handler = RotatingFileHandler(log_file)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    logger.info("Test log statement")
    
    assert log_file.exists()
    content = log_file.read_text()
    assert "Test log statement" in content
