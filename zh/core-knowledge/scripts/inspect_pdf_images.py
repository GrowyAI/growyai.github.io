"""Report embedded image counts and sizes in the source PDFs."""

import os

import pymupdf as fitz

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(BASE, "source")
PDFS = {
    "preschool": "CK_Sequence2023_PreSchool_W2.pdf",
    "k8": "CK_Sequence2023_GK8_W3.pdf",
}

for name, filename in PDFS.items():
    path = os.path.join(SOURCE_DIR, filename)
    doc = fitz.open(path)
    total = 0
    pages_with_images = 0
    sizes = []
    examples = []
    for pno in range(doc.page_count):
        page = doc[pno]
        images = page.get_image_info(xrefs=True)
        if images:
            pages_with_images += 1
        for img in images:
            width = img.get("width", 0)
            height = img.get("height", 0)
            sizes.append(width * height)
            total += 1
            if len(examples) < 8:
                examples.append((pno + 1, img.get("xref", 0), "?", width, height, 0))
    print("%s: pages=%d images=%d pages_with_images=%d" % (name, doc.page_count, total, pages_with_images))
    if sizes:
        sizes.sort()
        print("  pixel median=%d max=%d" % (sizes[len(sizes) // 2], sizes[-1]))
    for row in examples:
        print("  page %d xref %d %s %dx%d bytes=%d" % row)
    doc.close()
