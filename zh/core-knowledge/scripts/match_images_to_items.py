"""Match PDF illustrations to individual knowledge items by page coordinates.

Strategy:
  - ignore illustrations reused on 3+ pages (publisher decorations such as
    pencils, music notes, microscope icons);
  - for each remaining image, use its PDF bounding box;
  - locate each item's text on the same page with page.search_for();
  - attach the nearest 1-2 images whose boxes sit close to that text.

Outputs:
  assets/images/*.webp            refreshed thumbnails (60px minimum)
  data/images.json                filtered page gallery (fallback/reference)
  data/images-inline.js           window.PAGE_IMAGES
  data/item-images.json           uid -> [thumbnail paths]
  data/item-images-inline.js      window.ITEM_IMAGES
"""

import collections
import io
import json
import os
import re

import pymupdf as fitz
from PIL import Image

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
OUT_DIR = os.path.join(BASE, "assets", "images")
PDF_DIR = os.path.join(BASE, "source")
PDFS = {
    "preschool": "CK_Sequence2023_PreSchool_W2.pdf",
    "k8": "CK_Sequence2023_GK8_W3.pdf",
}
MIN_DIM = 60
MIN_BYTES = 1500
MAX_DIM = 520
DECORATIVE_PAGE_COUNT = 3
MAX_IMAGES_PER_ITEM = 2
V_GAP_MAX = 70
H_GAP_MAX = 220


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def to_webp(raw, out_path):
    image = Image.open(io.BytesIO(raw))
    if image.width < MIN_DIM or image.height < MIN_DIM:
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


def gap(a0, a1, b0, b1):
    if a1 <= b0:
        return b0 - a1
    if b1 <= a0:
        return a0 - b1
    return 0.0


def find_text_box(page, text):
    text = clean(text)
    queries = []
    for size in (70, 45, 28):
        if len(text) > size:
            q = text[:size]
            if " " in q:
                q = q.rsplit(" ", 1)[0]
            queries.append(q)
    queries.append(text[:22])
    for q in queries:
        if not q:
            continue
        hits = page.search_for(q)
        if hits:
            return hits[0]
    return None


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(DATA, "knowledge.json"), encoding="utf-8") as f:
        knowledge = json.load(f)
    items = knowledge["items"]

    pages = {"preschool": {}, "k8": {}}
    item_images = {}
    reused = {"preschool": {}, "k8": {}}
    image_boxes = {"preschool": {}, "k8": {}}
    thumbnails = {}
    stats = collections.Counter()

    # First pass: collect image instances and identify repeated decorations.
    for doc_name, filename in PDFS.items():
        doc = fitz.open(os.path.join(PDF_DIR, filename))
        for pno in range(doc.page_count):
            page_no = pno + 1
            seen = set()
            for info in doc[pno].get_image_info(xrefs=True):
                xref = info.get("xref")
                if not xref or xref in seen:
                    continue
                if info.get("width", 0) < MIN_DIM or info.get("height", 0) < MIN_DIM:
                    continue
                seen.add(xref)
                reused[doc_name].setdefault(xref, set()).add(page_no)
                image_boxes[doc_name].setdefault(page_no, []).append(
                    (xref, fitz.Rect(info["bbox"]))
                )
        decorative_xrefs = {
            xref for xref, pset in reused[doc_name].items()
            if len(pset) >= DECORATIVE_PAGE_COUNT
        }
        stats["decorative_" + doc_name] = len(decorative_xrefs)

        # Second pass: export thumbnails for non-decorative images.
        for pno in range(doc.page_count):
            page_no = pno + 1
            seen = set()
            page_list = []
            for info in doc[pno].get_image_info(xrefs=True):
                xref = info.get("xref")
                if (not xref or xref in seen or xref in decorative_xrefs
                        or info.get("width", 0) < MIN_DIM
                        or info.get("height", 0) < MIN_DIM):
                    continue
                seen.add(xref)
                key = (doc_name, xref)
                if key not in thumbnails:
                    try:
                        raw = doc.extract_image(xref).get("image", b"")
                    except Exception:
                        continue
                    if not raw or len(raw) < MIN_BYTES:
                        continue
                    name = "%s-img%05d.webp" % (doc_name, xref)
                    rel = "assets/images/" + name
                    try:
                        if not to_webp(raw, os.path.join(BASE, rel.replace("/", os.sep))):
                            continue
                    except Exception:
                        continue
                    thumbnails[key] = rel
                rel = thumbnails[key]
                if rel not in page_list:
                    page_list.append(rel)
            if page_list:
                pages[doc_name][str(page_no)] = page_list
        doc.close()

    # Remove stale thumbnails that are no longer referenced.
    keep = {os.path.basename(rel) for rel in thumbnails.values()}
    for name in os.listdir(OUT_DIR):
        if name.endswith(".webp") and name not in keep:
            os.remove(os.path.join(OUT_DIR, name))

    # Third pass: locate item text and attach nearby images.
    docs = {name: fitz.open(os.path.join(PDF_DIR, filename))
            for name, filename in PDFS.items()}
    for item in items:
        uid = item.get("uid")
        doc_name = item.get("source", {}).get("doc")
        page_no = str(item.get("source", {}).get("page", ""))
        if not uid or doc_name not in PDFS or page_no not in pages[doc_name]:
            continue
        stats["candidates"] += 1

        try:
            page = docs[doc_name][int(page_no) - 1]
        except Exception:
            continue
        text_box = find_text_box(page, item.get("en", ""))
        if text_box is None:
            stats["no_text_box"] += 1
            continue
        stats["text_box_found"] += 1
        scored = []
        for xref, image_box in image_boxes[doc_name].get(int(page_no), []):
            rel = thumbnails.get((doc_name, xref))
            if not rel:
                continue
            v = gap(text_box.y0, text_box.y1, image_box.y0, image_box.y1)
            h = gap(text_box.x0, text_box.x1, image_box.x0, image_box.x1)
            if v <= V_GAP_MAX and h <= H_GAP_MAX:
                scored.append((v + 0.25 * h, rel))
        scored.sort(key=lambda pair: pair[0])
        chosen = []
        for _, rel in scored:
            if rel not in chosen:
                chosen.append(rel)
            if len(chosen) >= MAX_IMAGES_PER_ITEM:
                break
        if chosen:
            item_images[uid] = chosen
            stats["items_with_images"] += 1
    for doc in docs.values():
        doc.close()

    with open(os.path.join(DATA, "images.json"), "w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)
    with open(os.path.join(DATA, "images-inline.js"), "w", encoding="utf-8") as f:
        f.write("window.PAGE_IMAGES = ")
        json.dump(pages, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    with open(os.path.join(DATA, "item-images.json"), "w", encoding="utf-8") as f:
        json.dump(item_images, f, ensure_ascii=False, indent=2)
    with open(os.path.join(DATA, "item-images-inline.js"), "w", encoding="utf-8") as f:
        f.write("window.ITEM_IMAGES = ")
        json.dump(item_images, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")

    print("stats:", dict(stats))
    print("thumbnails:", len(thumbnails), "pages:",
          sum(len(v) for v in pages.values()), "item mappings:", len(item_images))


if __name__ == "__main__":
    main()
