from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    outputs = root / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    stdout = (outputs / "streamlit.launch.out.log").open("ab")
    stderr = (outputs / "streamlit.launch.err.log").open("ab")
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app/streamlit_app.py",
            "--server.headless=true",
            "--server.port=8501",
            "--browser.gatherUsageStats=false",
        ],
        cwd=root,
        stdout=stdout,
        stderr=stderr,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
        close_fds=True,
    )
    (outputs / "streamlit.pid").write_text(str(process.pid), encoding="ascii")
    time.sleep(2)
    return process.poll() or 0


if __name__ == "__main__":
    raise SystemExit(main())
