#!/usr/bin/env python3
"""Run fisheye testing and generate the single-file HTML report for this batch."""

from pathlib import Path
import subprocess
import shutil
import sys

BATCH_DIR = Path(__file__).resolve().parent
ROOT = BATCH_DIR.parents[3]
BATCH_ID = BATCH_DIR.name


def main() -> None:
    report_dir = BATCH_DIR / "report"
    if report_dir.exists():
        shutil.rmtree(report_dir)
    subprocess.run([sys.executable, str(ROOT / "tools" / "fisheye" / "make_report.py"), BATCH_ID], check=True)
    subprocess.run([sys.executable, str(ROOT / "tools" / "fisheye" / "make_html_report.py"), BATCH_ID], check=True)


if __name__ == "__main__":
    main()
