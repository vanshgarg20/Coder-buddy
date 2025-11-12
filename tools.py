# agent/tools.py
from typing import List
import os

def read_file(path: str) -> str:
    """Read a UTF-8 text file and return its full content as a string.
    Args:
        path: Relative or absolute file path.
    Returns:
        The file contents as a string.
    Raises:
        FileNotFoundError: If the path does not exist.
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_file(path: str, content: str) -> str:
    """Write UTF-8 text to a file, creating parent directories as needed.
    Args:
        path: Relative or absolute file path to write.
        content: Text to write.
    Returns:
        The absolute path written to.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return os.path.abspath(path)

def get_current_directory() -> str:
    """Return the absolute path of the current working directory."""
    return os.path.abspath(os.getcwd())

def list_files(directory: str = ".") -> List[str]:
    """List files (not directories) recursively under the given directory.
    Args:
        directory: Directory to list. Defaults to current directory.
    Returns:
        A list of relative file paths found under the directory.
    """
    results: List[str] = []
    for root, _, files in os.walk(directory):
        for name in files:
            results.append(os.path.relpath(os.path.join(root, name), start=directory))
    return results
