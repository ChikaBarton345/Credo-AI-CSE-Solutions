import json
from pathlib import Path
from typing import Dict, List, Union

# Define a recursive type for JSON-serializable data.
JSONValue = Union[
    str, int, float, bool, None, Dict[str, "JSONValue"], List["JSONValue"]
]
JSONDict = Dict[str, JSONValue]
JSONList = List[JSONValue]
JSONData = Union[JSONDict, JSONList]


def mkdir_safe(path: Union[str, Path]) -> None:
    """Ensure the directory for a given file or folder path exists.

    If `path` points to a file, its parent directory will be created, but if `path`
    points to a directory, it will be created directly.

    Args:
        path (Union[str, Path]): File or directory path to ensure exists.

    Raises:
        `OSError`: If the directory cannot be created.
        `PermissionError`: If the user cannot modify the directory structure.
    """
    path = Path(path)
    target = path.parent if path.is_file() else path
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
    filename: Union[str, Path],
    indent: int = 4,
    output_dir: Union[str, Path] = "output",
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
