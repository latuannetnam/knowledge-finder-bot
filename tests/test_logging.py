"""Tests for logging configuration."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from knowledge_finder_bot.main import configure_logging


def test_configure_logging_console_only(tmp_path):
    """Test that configure_logging works in console-only mode."""
    # Clear any existing handlers
    logging.root.handlers.clear()
    
    # Configure logging without file
    configure_logging(log_level="DEBUG", log_file="")
    
    # Should have exactly one handler (console)
    assert len(logging.root.handlers) == 1
    assert isinstance(logging.root.handlers[0], logging.StreamHandler)
    assert not isinstance(logging.root.handlers[0], RotatingFileHandler)
    assert logging.root.level == logging.DEBUG


def test_configure_logging_with_file(tmp_path):
    """Test that configure_logging adds RotatingFileHandler when log_file is set."""
    # Clear any existing handlers
    logging.root.handlers.clear()
    
    # Configure logging with file
    log_file = tmp_path / "test.log"
    configure_logging(
        log_level="INFO",
        log_file=str(log_file),
        log_file_max_bytes=5_000_000,
        log_file_backup_count=3,
    )
    
    # Should have exactly two handlers (console + file)
    assert len(logging.root.handlers) == 2
    
    # First handler should be console StreamHandler
    assert isinstance(logging.root.handlers[0], logging.StreamHandler)
    assert not isinstance(logging.root.handlers[0], RotatingFileHandler)
    
    # Second handler should be RotatingFileHandler
    assert isinstance(logging.root.handlers[1], RotatingFileHandler)
    file_handler = logging.root.handlers[1]
    assert file_handler.maxBytes == 5_000_000
    assert file_handler.backupCount == 3
    
    # Log level should be set
    assert logging.root.level == logging.INFO
    
    # Log file should exist
    assert log_file.exists()


def test_configure_logging_creates_directory(tmp_path):
    """Test that configure_logging creates parent directories if they don't exist."""
    # Clear any existing handlers
    logging.root.handlers.clear()
    
    # Configure logging with nested path
    log_file = tmp_path / "logs" / "nested" / "test.log"
    assert not log_file.parent.exists()
    
    configure_logging(log_level="WARNING", log_file=str(log_file))
    
    # Directory should be created
    assert log_file.parent.exists()
    assert log_file.exists()
    
    # Should have two handlers
    assert len(logging.root.handlers) == 2
    assert isinstance(logging.root.handlers[1], RotatingFileHandler)


def test_configure_logging_writes_to_file(tmp_path):
    """Test that configure_logging actually writes logs to the file."""
    # Clear any existing handlers
    logging.root.handlers.clear()
    
    # Configure logging with file
    log_file = tmp_path / "app.log"
    configure_logging(log_level="INFO", log_file=str(log_file))
    
    # Get a logger and write a message
    import structlog
    logger = structlog.get_logger()
    logger.info("test_message", key="value")
    
    # Force flush
    for handler in logging.root.handlers:
        handler.flush()
    
    # File should contain the log message
    log_content = log_file.read_text(encoding="utf-8")
    assert len(log_content) > 0
    # When log_file is set, we use JSONRenderer, so it should be JSON format
    assert "test_message" in log_content or "event" in log_content
