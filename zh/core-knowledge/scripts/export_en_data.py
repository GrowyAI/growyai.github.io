#!/usr/bin/env python3
"""Export shared Core Knowledge inline data for the English viewer.

The English pages live in en/core-knowledge/ and load data from their own
folder. This keeps the built-in local preview and GitHub Pages working without
cross-directory script access. The Chinese data directory remains the source
of truth; this script only publishes a copy.
"""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "zh" / "core-knowledge" / "data"
DST = ROOT / "en" / "core-knowledge" / "data"
FILES = ("knowledge-inline.js", "image-pilot-inline.js")


def main():
    DST.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        src = SRC / name
        dst = DST / name
        shutil.copyfile(src, dst)
        print("copied {} -> {}".format(src.relative_to(ROOT), dst.relative_to(ROOT)))


if __name__ == "__main__":
    main()
