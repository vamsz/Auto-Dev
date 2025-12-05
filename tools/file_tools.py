"""
File System Tools for the Self-Healing Agent System.

Provides controlled file operations for the AI agents:
- list_files: Recursive directory listing with smart filtering
- read_file: Read file content with line numbers
- write_file: Safe file writing with backup
"""

import os
from pathlib import Path
from typing import List, Optional


# Directories to ignore when scanning
IGNORE_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".env",
    ".idea",
    ".vscode",
    "dist",
    "build",
    ".eggs",
    "*.egg-info",
}

# File patterns to ignore
IGNORE_FILES = {
    ".DS_Store",
    "Thumbs.db",
    ".gitignore",
    "*.pyc",
    "*.pyo",
    "*.so",
    "*.dylib",
}


def list_files(
    path: str,
    extensions: Optional[List[str]] = None,
    max_depth: Optional[int] = None,
    include_hidden: bool = False
) -> List[str]:
    """
    Recursively list all files in a directory with smart filtering.
    
    Args:
        path: Root directory path to scan
        extensions: Optional list of file extensions to include (e.g., ['.py', '.js'])
        max_depth: Maximum recursion depth (None = unlimited)
        include_hidden: Whether to include hidden files/directories
    
    Returns:
        List of relative file paths from the root directory
    
    Example:
        >>> files = list_files("./my_project", extensions=[".py"])
        >>> print(files)
        ['main.py', 'src/utils.py', 'tests/test_main.py']
    """
    root = Path(path).resolve()
    
    if not root.exists():
        raise FileNotFoundError(f"Directory not found: {path}")
    
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")
    
    files: List[str] = []
    
    def should_ignore_dir(dir_name: str) -> bool:
        """Check if directory should be ignored."""
        if not include_hidden and dir_name.startswith("."):
            return True
        return dir_name in IGNORE_DIRS
    
    def should_ignore_file(file_name: str) -> bool:
        """Check if file should be ignored."""
        if not include_hidden and file_name.startswith("."):
            return True
        return file_name in IGNORE_FILES
    
    def scan_directory(current_path: Path, depth: int = 0):
        """Recursively scan directory."""
        if max_depth is not None and depth > max_depth:
            return
        
        try:
            for entry in current_path.iterdir():
                if entry.is_dir():
                    if not should_ignore_dir(entry.name):
                        scan_directory(entry, depth + 1)
                elif entry.is_file():
                    if should_ignore_file(entry.name):
                        continue
                    
                    # Filter by extension if specified
                    if extensions:
                        if entry.suffix.lower() not in [ext.lower() for ext in extensions]:
                            continue
                    
                    # Store relative path
                    rel_path = entry.relative_to(root)
                    files.append(str(rel_path).replace("\\", "/"))
                    
        except PermissionError:
            # Skip directories we can't access
            pass
    
    scan_directory(root)
    return sorted(files)


def read_file(path: str, with_line_numbers: bool = True) -> str:
    """
    Read the contents of a file, optionally with line numbers.
    
    Adding line numbers helps the LLM reference specific lines when
    discussing code changes.
    
    Args:
        path: Path to the file to read
        with_line_numbers: If True, prepend line numbers to each line
    
    Returns:
        File content as a string, optionally with line numbers
    
    Example:
        >>> content = read_file("./main.py", with_line_numbers=True)
        >>> print(content)
        1: def main():
        2:     print("Hello, World!")
        3: 
        4: if __name__ == "__main__":
        5:     main()
    """
    file_path = Path(path).resolve()
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    if not file_path.is_file():
        raise IsADirectoryError(f"Not a file: {path}")
    
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Try with latin-1 as fallback
        content = file_path.read_text(encoding="latin-1")
    
    if not with_line_numbers:
        return content
    
    # Add line numbers
    lines = content.split("\n")
    width = len(str(len(lines)))  # Calculate padding width
    numbered_lines = [
        f"{i+1:>{width}}: {line}"
        for i, line in enumerate(lines)
    ]
    
    return "\n".join(numbered_lines)


def write_file(
    path: str,
    content: str,
    create_dirs: bool = True,
    backup: bool = False
) -> dict:
    """
    Write content to a file with optional backup.
    
    Args:
        path: Path to the file to write
        content: Content to write to the file
        create_dirs: If True, create parent directories if they don't exist
        backup: If True, create a backup of existing file before overwriting
    
    Returns:
        Dict with operation details:
        {
            "path": str,
            "bytes_written": int,
            "backup_path": str or None,
            "created": bool  # True if file was newly created
        }
    
    Example:
        >>> result = write_file("./output.py", "print('Hello!')")
        >>> print(result)
        {'path': '/full/path/output.py', 'bytes_written': 15, 'backup_path': None, 'created': True}
    """
    file_path = Path(path).resolve()
    
    # Check if file already exists
    file_existed = file_path.exists()
    backup_path = None
    
    # Create parent directories if needed
    if create_dirs and not file_path.parent.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create backup if requested and file exists
    if backup and file_existed:
        backup_path = str(file_path) + ".backup"
        import shutil
        shutil.copy2(file_path, backup_path)
    
    # Write the content
    bytes_written = file_path.write_text(content, encoding="utf-8")
    
    return {
        "path": str(file_path),
        "bytes_written": len(content.encode("utf-8")),
        "backup_path": backup_path,
        "created": not file_existed
    }


def get_file_info(path: str) -> dict:
    """
    Get detailed information about a file.
    
    Args:
        path: Path to the file
    
    Returns:
        Dict with file metadata
    """
    file_path = Path(path).resolve()
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    stat = file_path.stat()
    
    return {
        "path": str(file_path),
        "name": file_path.name,
        "extension": file_path.suffix,
        "size_bytes": stat.st_size,
        "is_file": file_path.is_file(),
        "is_dir": file_path.is_dir(),
        "modified_time": stat.st_mtime,
    }


def delete_file(path: str, missing_ok: bool = True) -> bool:
    """
    Delete a file.
    
    Args:
        path: Path to the file to delete
        missing_ok: If True, don't raise error if file doesn't exist
    
    Returns:
        True if file was deleted, False if it didn't exist
    """
    file_path = Path(path).resolve()
    
    if not file_path.exists():
        if missing_ok:
            return False
        raise FileNotFoundError(f"File not found: {path}")
    
    file_path.unlink()
    return True


# For testing the module directly
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_path = sys.argv[1]
    else:
        test_path = "."
    
    print(f"Listing files in: {test_path}")
    print("-" * 40)
    
    files = list_files(test_path, extensions=[".py"])
    for f in files:
        print(f"  {f}")
    
    print(f"\nTotal: {len(files)} Python files")
