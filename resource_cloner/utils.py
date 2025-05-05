import json
import logging
from pathlib import Path
from typing import Dict, List, Union

logger = logging.getLogger(__name__)


PathLike = Union[str, Path]

# Define a recursive type for JSON-serializable data.
JSONValue = Union[
    str, int, float, bool, None, Dict[str, "JSONValue"], List["JSONValue"]
]
JSONDict = Dict[str, JSONValue]
JSONList = List[JSONValue]
JSONData = Union[JSONDict, JSONList]


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
    log_format = "%(asctime)s | %(levelname)s | %(name)s.%(funcName)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, datefmt=date_format)

    # Console handler.
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler.
    log_dir = Path(log_dir)
    mkdir_safe(log_dir)
    log_path = log_dir / f"{name}.log"
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def mkdir_safe(path: PathLike) -> None:
    """Ensure the directory for a given file or folder path exists.

    If `path` points to a file, its parent directory will be created, but if `path`
    points to a directory, it will be created directly.

    Args:
        path (PathLike): File or directory path to ensure exists.

    Raises:
        `OSError`: If the directory cannot be created.
        `PermissionError`: If the user cannot modify the directory structure.
    """
    path = Path(path)
    # If there's a suffix (e.g., `.log`), treat it as a file path.
    target = path.parent if path.suffix else path
    try:
        print(f"Creating directory: {target}")
        target.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        print(f"Permission denied while creating directory: {exc}")
        raise
    except OSError as exc:
        print(f"Failed to create directory: {exc}")
        raise


def export_to_json(
    data: JSONData,
    filename: PathLike,
    indent: int = 4,
    output_dir: PathLike = "output",
) -> None:
    """Export JSON-serializable data to a file with formatted output.

    Args:
        data: A dict or list that can be serialized to JSON.
        outpath: Path to the output file (`.json` extension will be enforced).
        indent: Indentation level (default: 4).
        output_dir: Directory to save the file in (default: "output").
    """
    outpath = Path(output_dir)
    mkdir_safe(outpath)
    filepath = outpath / filename
    filepath = filepath.with_suffix(".json")
    print(f"Attempting JSON export: {filepath}")
    try:
        filepath.write_text(
            json.dumps(data, indent=indent, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Exported to JSON: {filepath}")
    except (TypeError, ValueError) as exc:
        print(f"Export failed, JSON serialization error: {exc}")
    except OSError as exc:
        print(f"Export filed, file write error: {exc}")
