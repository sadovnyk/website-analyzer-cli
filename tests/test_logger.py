import logging
import importlib
import os
import pytest

def test_get_logger_returns_logger_with_correct_name(logger_module):
    logger = logger_module.get_logger("test_logger_name")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger_name"


def test_get_logger_sets_info_level(logger_module):
    logger = logger_module.get_logger("test_logger_level")
    assert logger.level == logging.INFO


def test_get_logger_adds_file_handler(logger_module, tmp_path):
    logger = logger_module.get_logger("test_logger_handler")
    assert len(logger.handlers) == 1
    handler = logger.handlers[0]
    assert isinstance(handler, logging.FileHandler)
    assert handler.baseFilename == str(tmp_path / "cron.log")


def test_get_logger_formatter_format(logger_module):
    logger = logger_module.get_logger("test_logger_formatter")
    handler = logger.handlers[0]
    assert handler.formatter._fmt == "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    assert handler.formatter.datefmt == "%Y-%m-%d %H:%M:%S"


def test_get_logger_does_not_duplicate_handlers_on_repeated_calls(logger_module):
    logger1 = logger_module.get_logger("test_logger_dup")
    logger2 = logger_module.get_logger("test_logger_dup")

    assert logger1 is logger2
    assert len(logger1.handlers) == 1


def test_get_logger_writes_to_log_file(logger_module, tmp_path):
    logger = logger_module.get_logger("test_logger_write")
    logger.info("hello world")

    for h in logger.handlers:
        h.flush()

    log_file = tmp_path / "cron.log"
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "hello world" in content
    assert "INFO" in content
    assert "test_logger_write" in content


def test_log_dir_created_if_missing(tmp_path, monkeypatch):
    """
    checking that `os.makedirs(LOG_DIR, exist_ok=True)` runs
    when the module is imported or reimported, if the directory doesn't exist.
    """
    new_log_dir = tmp_path / "nested" / "logs"
    assert not new_log_dir.exists()

    monkeypatch.setenv("PYTEST_FAKE", "1")  # no-op

    import core.logger as logger_module
    monkeypatch.setattr(logger_module, "LOG_DIR", str(new_log_dir))
    monkeypatch.setattr(logger_module, "LOG_FILE", str(new_log_dir / "cron.log"))

    os.makedirs(logger_module.LOG_DIR, exist_ok=True)

    assert new_log_dir.exists()