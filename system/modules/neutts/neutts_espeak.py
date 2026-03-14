import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional


def _normalize_path(value: str) -> Optional[Path]:
    if not value:
        return None
    try:
        path = Path(os.path.expandvars(os.path.expanduser(value))).resolve()
        if path.exists():
            return path
    except Exception:
        return None
    return None


def _collect_search_roots() -> List[Path]:
    roots: List[Path] = []

    for env_name in ("ProgramFiles", "ProgramFiles(x86)"):
        env_value = os.environ.get(env_name)
        if env_value:
            roots.extend(
                [
                    Path(env_value) / "eSpeak NG",
                    Path(env_value) / "eSpeak",
                ]
            )

    roots.extend(
        [
            Path(r"C:\Program Files\eSpeak NG"),
            Path(r"C:\Program Files\eSpeak"),
            Path(r"C:\Program Files (x86)\eSpeak NG"),
            Path(r"C:\Program Files (x86)\eSpeak"),
            Path(r"C:\ProgramData\chocolatey\bin"),
        ]
    )

    seen = set()
    unique_roots: List[Path] = []
    for root in roots:
        key = str(root).lower()
        if key not in seen:
            seen.add(key)
            unique_roots.append(root)
    return unique_roots


def _find_binary_from_dir(directory: Path) -> Optional[Path]:
    names = ["espeak-ng.exe", "espeak.exe", "espeak-ng", "espeak"]
    for name in names:
        candidate = directory / name
        if candidate.exists():
            return candidate
    command_line = directory / "command_line"
    if command_line.exists():
        for name in names:
            candidate = command_line / name
            if candidate.exists():
                return candidate
    return None


def _find_library_from_dir(directory: Path) -> Optional[Path]:
    names = ["libespeak-ng.dll", "espeak-ng.dll", "libespeak.dll", "espeak.dll"]
    for name in names:
        candidate = directory / name
        if candidate.exists():
            return candidate
    command_line = directory / "command_line"
    if command_line.exists():
        for name in names:
            candidate = command_line / name
            if candidate.exists():
                return candidate
    return None


def detect_espeak_status(update_env: bool = True) -> Dict[str, Any]:
    binary_path: Optional[Path] = None
    library_path: Optional[Path] = None

    env_binary = _normalize_path(os.environ.get("PHONEMIZER_ESPEAK_PATH", ""))
    env_library = _normalize_path(os.environ.get("PHONEMIZER_ESPEAK_LIBRARY", ""))

    if env_binary and env_binary.is_file():
        binary_path = env_binary
    elif env_binary and env_binary.is_dir():
        binary_path = _find_binary_from_dir(env_binary)

    if env_library and env_library.is_file():
        library_path = env_library

    if not binary_path:
        for name in ("espeak-ng", "espeak"):
            exe = shutil.which(name)
            if exe:
                candidate = _normalize_path(exe)
                if candidate and candidate.is_file():
                    binary_path = candidate
                    break

    if not binary_path or not library_path:
        for root in _collect_search_roots():
            if not binary_path:
                binary_path = _find_binary_from_dir(root)
            if not library_path:
                library_path = _find_library_from_dir(root)
            if binary_path and library_path:
                break

    if binary_path and not library_path:
        library_path = _find_library_from_dir(binary_path.parent)

    if update_env:
        if binary_path:
            os.environ["PHONEMIZER_ESPEAK_PATH"] = str(binary_path)
        if library_path:
            os.environ["PHONEMIZER_ESPEAK_LIBRARY"] = str(library_path)

    detail_path = binary_path or library_path
    return {
        "ok": bool(detail_path),
        "detail": str(detail_path) if detail_path else "",
        "binary": str(binary_path) if binary_path else "",
        "library": str(library_path) if library_path else "",
    }
