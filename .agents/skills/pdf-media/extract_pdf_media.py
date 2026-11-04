#!/usr/bin/env python3
"""Extrae las imágenes de un PDF a docs/media/<slug>/ y escribe un manifest.json.

Uso:
  extract_pdf_media.py <fichero.pdf> [--slug NOMBRE] [--out docs/media] [--min-size 80]
                       [--render-pages 3,5-6] [--dpi 150]

Requiere poppler (pdfimages, pdftoppm, pdftotext). Solo stdlib de Python.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "pdf"


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def parse_pages(spec: str):
    pages = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        a, _, b = part.partition("-")
        pages.update(range(int(a), int(b or a) + 1))
    return sorted(pages)


def list_images(pdf: Path):
    """Filas de `pdfimages -list`: page, num, type, width, height."""
    rows = []
    for line in run(["pdfimages", "-list", str(pdf)]).splitlines()[2:]:
        f = line.split()
        if len(f) >= 5 and f[0].isdigit():
            rows.append({"page": int(f[0]), "num": int(f[1]), "type": f[2],
                         "width": int(f[3]), "height": int(f[4])})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--slug")
    ap.add_argument("--out", type=Path, default=Path("docs/media"))
    ap.add_argument("--min-size", type=int, default=80,
                    help="descarta imágenes con ancho o alto menor (iconos, filetes)")
    ap.add_argument("--render-pages", default="",
                    help="páginas a renderizar enteras (figuras vectoriales), p. ej. 3,5-6")
    ap.add_argument("--dpi", type=int, default=150)
    args = ap.parse_args()

    for tool in ("pdfimages", "pdftoppm", "pdfinfo"):
        if not shutil.which(tool):
            sys.exit(f"Falta '{tool}' (instala poppler: pacman -S poppler / apt install poppler-utils)")
    if not args.pdf.is_file():
        sys.exit(f"No existe: {args.pdf}")

    slug = args.slug or slugify(args.pdf.stem)
    dest = args.out / slug
    dest.mkdir(parents=True, exist_ok=True)
    tmp = dest / ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()

    pages = int(re.search(r"Pages:\s+(\d+)", run(["pdfinfo", str(args.pdf)])).group(1))
    rows = list_images(args.pdf)
    run(["pdfimages", "-png", "-p", str(args.pdf), str(tmp / "img")])

    manifest, seen, per_page = [], {}, {}
    skipped = {"small": 0, "mask": 0, "duplicate": 0}
    for row in rows:
        src = tmp / f"img-{row['page']:03d}-{row['num']:03d}.png"
        if not src.exists():
            continue
        if row["type"] in ("smask", "mask"):
            skipped["mask"] += 1
        elif min(row["width"], row["height"]) < args.min_size:
            skipped["small"] += 1
        else:
            digest = hashlib.sha1(src.read_bytes()).hexdigest()
            if digest in seen:
                skipped["duplicate"] += 1
            else:
                per_page[row["page"]] = per_page.get(row["page"], 0) + 1
                name = f"{slug}-p{row['page']:02d}-{per_page[row['page']]:02d}.png"
                shutil.move(src, dest / name)
                seen[digest] = name
                manifest.append({"file": name, "page": row["page"], "kind": "image",
                                 "width": row["width"], "height": row["height"]})
    for page in parse_pages(args.render_pages):
        if not 1 <= page <= pages:
            sys.exit(f"Página fuera de rango: {page} (el PDF tiene {pages})")
        run(["pdftoppm", "-png", "-r", str(args.dpi), "-f", str(page), "-l", str(page),
             "-singlefile", str(args.pdf), str(dest / f"{slug}-p{page:02d}-page")])
        manifest.append({"file": f"{slug}-p{page:02d}-page.png", "page": page, "kind": "page-render"})
    shutil.rmtree(tmp, ignore_errors=True)

    manifest.sort(key=lambda m: (m["page"], m["file"]))
    (dest / "manifest.json").write_text(
        json.dumps({"source": args.pdf.name, "pages": pages, "images": manifest}, indent=2, ensure_ascii=False) + "\n")

    print(f"{args.pdf.name}: {pages} orrialde, {len(manifest)} irudi -> {dest}/")
    print(f"descartadas: {skipped['small']} pequeñas, {skipped['mask']} máscaras, {skipped['duplicate']} duplicadas")
    for m in manifest:
        print(f"  p{m['page']:>3}  {m['file']}")
    if not manifest:
        print("Sin imágenes raster: si las figuras son vectoriales usa --render-pages N")


if __name__ == "__main__":
    main()
