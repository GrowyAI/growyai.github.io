"""Extract and downscale embedded PDF illustrations for the HTML viewer.

Images are associated by PDF page, not by individual knowledge item, because
the PDFs do not tag figures to specific bullets. Output:
  assets/images/*.webp   thumbnails
  data/images.json       doc -> page -> [image paths]
  data/images-inline.js  window.PAGE_IMAGES for offline file:// viewing
"""

import io
import json
import os

import pymupdf as fitz
from PIL import Image

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(BASE, "source")
OUT_DIR = os.path.join(BASE, "assets", "images")
DATA_OUT = os.path.join(BASE, "data", "images.json")
INLINE_OUT = os.path.join(BASE, "data", "images-inline.js")
PDFS = {
    "preschool": "CK_Sequence2023_PreSchool_W2.pdf",
    "k8": "CK_Sequence2023_GK8_W3.pdf",
}
MAX_DIM = 520


def to_webp(raw, out_path):
    image = Image.open(io.BytesIO(raw))
    if image.width < 100 or image.height < 100:
        return False
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        image = background
    else:
        image = image.convert("RGB")
    image.thumbnail((MAX_DIM, MAX_DIM), Image.LANCZOS)
    image.save(out_path, "WEBP", quality=72, method=2)
    return True


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    mapping = {"preschool": {}, "k8": {}}
    seen = {}

    for doc_name, filename in PDFS.items():
        doc = fitz.open(os.path.join(SOURCE_DIR, filename))
        for pno in range(doc.page_count):
            page_no = str(pno + 1)
            page = doc[pno]
            refs = []
            for info in page.get_image_info(xrefs=True):
                xref = info.get("xref")
                width = info.get("width", 0)
                height = info.get("height", 0)
                if not xref or width < 100 or height < 100:
                    continue
                if xref not in refs:
                    refs.append(xref)
            for xref in refs:
                if xref in seen:
                    rel = seen[xref]
                    if rel is None:
                        continue
                else:
                    try:
                        extracted = doc.extract_image(xref)
                        raw = extracted.get("image", b"")
                    except Exception:
                        seen[xref] = None
                        continue
                    if not raw or len(raw) < 2000:
                        seen[xref] = None
                        continue
                    name = "%s-img%05d.webp" % (doc_name, xref)
                    out_path = os.path.join(OUT_DIR, name)
                    try:
                        ok = to_webp(raw, out_path)
                    except Exception:
                        ok = False
                    if not ok:
                        seen[xref] = None
                        continue
                    rel = "assets/images/" + name
                    seen[xref] = rel
                page_list = mapping[doc_name].setdefault(page_no, [])
                if rel not in page_list:
                    page_list.append(rel)
        doc.close()

    with open(DATA_OUT, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    with open(INLINE_OUT, "w", encoding="utf-8") as f:
        f.write("window.PAGE_IMAGES = ")
        json.dump(mapping, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")

    total = sum(len(v) for doc in mapping.values() for v in doc.values())
    print("extracted %d image references, %d files" % (total, len([x for x in seen.values() if x])))
    for name, pages in mapping.items():
        print(name, "pages with images:", len(pages))


if __name__ == "__main__":
    main()
