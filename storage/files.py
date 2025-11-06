from pathlib import Path

TEMP_DIR = Path("temp")


def ensure_dirs() -> None:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
