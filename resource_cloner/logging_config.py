import logging
from pathlib import Path
from typing import Union

PathLike = Union[str, Path]

old_factory = logging.getLogRecordFactory()


def record_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)
    record.fullname = f"{record.name}.{record.funcName}"
    return record


logging.setLogRecordFactory(record_factory)


def setup_logger(
    name: str, level: int = logging.INFO, log_dir: PathLike = "logs"
) -> logging.Logger:
    """Configure and return a logger with both console and file output.

    The logger will format messages with timestamp, module.function name, log level,
    and the message itself.

    Args:
        name (str): The name of the logger, usually `Path(__file__).stem` from the
            calling module.
        level (int): The logging level threshold. Only messages at this level
            or higher will be logged. Defaults to `logging.INFO`.
        log_dir (PathLike): Directory to store log files. Defaults to "logs".

            Common log levels include:
                - logging.DEBUG: Detailed info, useful for debugging.
                - logging.INFO: General information about program execution.
                - logging.WARNING: Something unexpected happened, but program continues.
                - logging.ERROR: A serious error occurred, affecting functionality.
                - logging.CRITICAL: A severe error that may prevent the program from
                    running.

    Returns:
        logging.Logger: A configured logger instance.

    Example:
        >>> logger = setup_logger(__name__, level=logging.DEBUG)
        >>> logger.info("Script started.")
        >>> logger.error("Something went wrong.")
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # Prevent duplicate handlers.

    # Define a format string for human-readable logging.

    log_format = "%(asctime)s | %(levelname)-8s | %(fullname)-50s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, datefmt=date_format)

    # Console handler.
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler.
    log_dir = Path(log_dir)
    # Avoid a circular import with inline `mkdir_safe` logic.
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "resource_cloner.log"
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger
