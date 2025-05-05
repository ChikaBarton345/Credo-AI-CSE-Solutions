import json
from pathlib import Path
from typing import Dict, List, Union

from logging_config import setup_logger

PathLike = Union[str, Path]

# Define a recursive type for JSON-serializable data.
JSONValue = Union[
    str, int, float, bool, None, Dict[str, "JSONValue"], List["JSONValue"]
]
JSONDict = Dict[str, JSONValue]
JSONList = List[JSONValue]
JSONData = Union[JSONDict, JSONList]


LOGGER = setup_logger(Path(__file__).stem)


def mkdir_safe(path: PathLike) -> None:
    """Ensure the directory for a given file or folder path exists.

    If `path` points to something that looks like a file, its parent
    directory will be created, but if `path` points to a directory, it will be created
    directly.

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
        LOGGER.info(f"Creating directory (exists ok): {target}")
        target.mkdir(parents=True, exist_ok=True)
    except PermissionError as err:
        LOGGER.error(f"Permission denied while creating directory: {target}\n{err}")
        raise
    except OSError as err:
        LOGGER.error(f"Failed to create directory: {target}\n{err}")
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
    LOGGER.info(f"Attempting JSON export: {filepath.as_posix()}")
    try:
        filepath.write_text(
            json.dumps(data, indent=indent, ensure_ascii=False),
            encoding="utf-8",
        )
        LOGGER.info(f"Exported to JSON: {filepath.as_posix()}")
    except (TypeError, ValueError) as exc:
        LOGGER.error(f"Export failed, JSON serialization error: {exc}")
    except OSError as exc:
        LOGGER.error(f"Export filed, file write error: {exc}")
