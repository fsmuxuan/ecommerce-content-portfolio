#!/usr/bin/env python3
"""Inventory product knowledge and real images using only standard Python."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
KNOWLEDGE_EXTENSIONS = {".md", ".txt", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".json"}


def image_size(path: Path):
    try:
        data = path.read_bytes()
        if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
            return list(struct.unpack(">II", data[16:24]))
        if data.startswith(b"\xff\xd8"):
            index = 2
            while index + 9 < len(data):
                if data[index] != 0xFF:
                    index += 1
                    continue
                marker = data[index + 1]
                index += 2
                if marker in (0xD8, 0xD9):
                    continue
                length = int.from_bytes(data[index:index + 2], "big")
                if marker in range(0xC0, 0xC4):
                    return [int.from_bytes(data[index + 5:index + 7], "big"), int.from_bytes(data[index + 3:index + 5], "big")]
                index += length
    except OSError:
        return None
    return None


def default_output(image_dir: Path) -> Path:
    return image_dir.parent / "主图输出" / f"{image_dir.name}_平台主图五张"


def audit(product_library: Path, image_dir: Path, output_dir: Path | None = None) -> Path:
    product_library = product_library.resolve()
    image_dir = image_dir.resolve()
    if not product_library.is_dir():
        raise NotADirectoryError(product_library)
    if not image_dir.is_dir():
        raise NotADirectoryError(image_dir)
    output_dir = (output_dir or default_output(image_dir)).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    knowledge = sorted(path for path in product_library.rglob("*") if path.is_file() and path.suffix.lower() in KNOWLEDGE_EXTENSIONS)
    images = sorted(path for path in image_dir.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)
    report = {
        "product_library": str(product_library),
        "image_dir": str(image_dir),
        "recommended_output_dir": str(output_dir),
        "knowledge_file_count": len(knowledge),
        "image_file_count": len(images),
        "knowledge_files": [str(path.relative_to(product_library)) for path in knowledge],
        "images": [
            {"path": str(path.relative_to(image_dir)), "bytes": path.stat().st_size, "pixel_size": image_size(path)}
            for path in images
        ],
    }
    target = output_dir / "00_input-audit.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--product-library", type=Path, required=True)
    parser.add_argument("--image-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    print(audit(args.product_library, args.image_dir, args.output_dir))


if __name__ == "__main__":
    main()
