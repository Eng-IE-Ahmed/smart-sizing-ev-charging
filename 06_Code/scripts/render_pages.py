""" render every page of paper_full/manuscript_full.pdf to PNG (paper_full/pages/page_NN.png) for the visual check.

Uses PyMuPDF (pymupdf). Usage: python scripts/render_pages.py --project . [--dpi 110]
"""
import argparse
from pathlib import Path

import pymupdf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--dpi", type=int, default=110)
    a = ap.parse_args()
    root = Path(a.project).resolve()
    out = root / "paper_full" / "pages"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("page_*.png"):
        old.unlink()
    doc = pymupdf.open(root / "paper_full" / "manuscript_full.pdf")
    for i, page in enumerate(doc, start=1):
        page.get_pixmap(dpi=a.dpi).save(out / f"page_{i:02d}.png")
    print(doc.page_count, "pages rendered to", out)


if __name__ == "__main__":
    main()
