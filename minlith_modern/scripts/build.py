"""Build script — создание .exe через PyInstaller."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def build_exe():
    """Собрать .exe из MINLITH Modern."""
    root = Path(__file__).parent
    src = root / "src"
    icon = root / "assets" / "icon.ico"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "MINLITH",
        "--icon", str(icon) if icon.exists() else "",
        "--add-data", f"{root / 'src' / 'gui' / 'styles'};src/gui/styles",
        "--add-data", f"{root / 'src' / 'locale'};src/locale",
        "--hidden-import", "src.charts.built_in",
        "--hidden-import", "src.reports",
        "--noconfirm",
        "--clean",
        str(src / "__main__.py"),
    ]

    # Remove empty icon arg
    if "--icon; " in " ".join(cmd):
        idx = cmd.index("--icon")
        if cmd[idx + 1] == "":
            cmd.pop(idx)
            cmd.pop(idx)

    print(f"Building: {' '.join(cmd[:5])}...")
    result = subprocess.run(cmd, cwd=str(root))
    return result.returncode


if __name__ == "__main__":
    sys.exit(build_exe())
