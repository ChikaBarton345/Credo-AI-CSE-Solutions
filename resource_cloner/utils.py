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
    target = path.parent if path.suffix else path
    target.mkdir(parents=True, exist_ok=True)


def export_to_json(data: JSONData, outpath: Union[str, Path], indent: int = 4) -> bool:
    """Export formatted JSON to a file.

    Args:
        data: JSON-serializable data to write.
        outpath: Target output destination.
        indent: Indentation level (default: 4).

    Returns:
        bool: True if successful, False otherwise.
    """
    outpath = Path(outpath).with_suffix(".json")
    mkdir_safe(outpath)

    try:
        outpath.write_text(json.dumps(data, indent=indent), encoding="utf-8")
        print(f"Formatted JSON exported to: {outpath}")
        return True
    except (TypeError, ValueError) as exc:
        print(f"JSON serialization error: {exc}")
    except OSError as exc:
        print(f"File write error: {exc}")

    return False
