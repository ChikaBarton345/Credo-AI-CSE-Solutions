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
    """Ensure the parent folder (for a file) or the folder (for a directory) exists."""
    path = Path(path)
    target = path.parent if path.is_file() else path
    target.mkdir(parents=True, exist_ok=True)


def export_to_json(
    data: JSONData,
    filename: Union[str, Path],
    indent: int = 4,
    output_dir: Union[str, Path] = "output",
) -> bool:
    """Export formatted JSON to a file.

    Args:
        data: JSON-serializable data to write.
        outpath: Target output destination.
        indent: Indentation level (default: 4).
        output_dir: Directory to save the file in (default is 'output').

    Returns:
        bool: True if successful, False otherwise.
    """
    outpath = Path(output_dir)
    mkdir_safe(outpath)
    filepath = outpath / filename
    filepath = filepath.with_suffix(".json")

    try:
        filepath.write_text(json.dumps(data, indent=indent), encoding="utf-8")
        print(f"Formatted JSON exported to: {filepath}")
        return True
    except (TypeError, ValueError) as exc:
        print(f"JSON serialization error: {exc}")
    except OSError as exc:
        print(f"File write error: {exc}")

    return False
