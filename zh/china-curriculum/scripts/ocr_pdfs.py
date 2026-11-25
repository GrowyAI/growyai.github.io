"""OCR selected pages of the local, gitignored MOE curriculum PDFs.

The 2022 standards are scanned images without a text layer.  This script keeps
OCR output under source/extracted/ (also gitignored) and never copies source
files into the public site.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

BASE = Path(__file__).resolve().parents[1]
SOURCE = BASE / "source"
OUT = SOURCE / "extracted" / "ocr"

BOOKS = {
    "chinese": "03-义务教育语文课程标准（2022年版）.pdf",
    "math": "05-义务教育数学课程标准（2022年版）.pdf",
    "english": "06-义务教育英语课程标准（2022年版）.pdf",
    "politics": "02-义务教育道德与法治课程标准（2022年版）.pdf",
    "history": "04-义务教育历史课程标准（2022年版）.pdf",
    "geography": "09-义务教育地理课程标准（2022年版）.pdf",
    "science": "10-义务教育科学课程标准（2022年版）.pdf",
    "physics": "11-义务教育物理课程标准（2022年版）.pdf",
    "chemistry": "12-义务教育化学课程标准（2022年版）.pdf",
    "biology": "13-义务教育生物学课程标准（2022年版）.pdf",
    "information": "14-义务教育信息科技课程标准（2022年版）.pdf",
    "japanese": "07-义务教育日语课程标准（2022年版）.pdf",
    "russian": "08-义务教育俄语课程标准（2022年版）.pdf",
    "pe": "15-义务教育体育与健康课程标准（2022年版）.pdf",
    "arts": "16-义务教育艺术课程标准（2022年版）.pdf",
    "labor": "17-义务教育劳动课程标准（2022年版）.pdf",
}


def parse_pages(spec: str, total: int) -> list[int]:
    pages: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            start, end = int(a), int(b)
            if start < 1 or end > total or start > end:
                raise ValueError(f"bad page range {part!r} for {total} pages")
            pages.update(range(start, end + 1))
        else:
            page = int(part)
            if page < 1 or page > total:
                raise ValueError(f"bad page {page} for {total} pages")
            pages.add(page)
    return sorted(pages)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("book", choices=sorted(BOOKS))
    ap.add_argument("--pages", required=True, help="1-based pages, e.g. 1-12,20")
    ap.add_argument("--scale", type=float, default=1.5)
    args = ap.parse_args()

    pdf = SOURCE / BOOKS[args.book]
    if not pdf.exists():
        raise SystemExit(f"missing source PDF: {pdf}")
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{args.book}.txt"

    doc = pymupdf.open(pdf)
    pages = parse_pages(args.pages, doc.page_count)
    existing: dict[int, str] = {}
    if out.exists():
        current_page = None
        buf: list[str] = []
        for line in out.read_text(encoding="utf-8").splitlines():
            if line.startswith("<!-- PDF_PAGE "):
                if current_page is not None:
                    existing[current_page] = "\n".join(buf).strip()
                current_page = int(line.split()[2])
                buf = []
            elif current_page is not None:
                buf.append(line)
        if current_page is not None:
            existing[current_page] = "\n".join(buf).strip()

    engine = RapidOCR(use_angle_cls=False)
    for page_no in pages:
        if page_no in existing and existing[page_no]:
            print(f"skip page {page_no}", file=sys.stderr)
            continue
        started = time.time()
        pix = doc[page_no - 1].get_pixmap(
            matrix=pymupdf.Matrix(args.scale, args.scale), alpha=False
        )
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        result, _ = engine(np.array(img))
        text = "\n".join(row[1] for row in result) if result else ""
        existing[page_no] = text.strip()
        print(
            f"page {page_no}: {len(text)} chars in {time.time() - started:.1f}s",
            file=sys.stderr,
        )
        # Write after every page so long runs remain resumable.
        with out.open("w", encoding="utf-8") as fh:
            for no in sorted(existing):
                if existing[no]:
                    fh.write(f"<!-- PDF_PAGE {no} -->\n{existing[no]}\n\n")
    doc.close()
    print(f"wrote {out} ({len(existing)} pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
