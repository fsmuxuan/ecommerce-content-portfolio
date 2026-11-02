#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


DOCUMENT_EXTENSIONS = {
    ".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".xlsx", ".xls", ".pdf", ".docx"
}
IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif", ".bmp", ".tif", ".tiff", ".heic", ".heif"
}
BROWSER_READY_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"}
ROLE_KEYWORDS = {
    "use_effect": ("效果", "完工", "场景", "应用", "案例", "hero", "effect", "application", "case"),
    "installation": ("安装", "现场", "施工", "install", "site"),
    "accessory": ("配件", "五金", "电机", "滑轮", "accessory", "motor", "pulley"),
    "production": ("生产", "车间", "工厂", "仓库", "production", "factory", "workshop", "warehouse"),
    "packaging": ("包装", "打包", "发货", "物流", "packing", "package", "shipping"),
    "detail": ("细节", "近景", "材质", "纹理", "detail", "close", "material", "texture"),
}


def existing_directory(value: str, label: str) -> Path:
    path = Path(value).expanduser()
    if not path.exists():
        raise ValueError(f"{label} does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"{label} is not a directory: {path}")
    return path.resolve()


def visible_files(root: Path) -> list[Path]:
    return sorted(
        path for path in root.rglob("*")
        if path.is_file() and not any(part.startswith(".") for part in path.relative_to(root).parts)
    )


def role_hints(path: Path) -> list[str]:
    name = path.stem.lower()
    return [role for role, keywords in ROLE_KEYWORDS.items() if any(keyword in name for keyword in keywords)]


def record(path: Path, root: Path) -> dict[str, object]:
    return {
        "relative_path": path.relative_to(root).as_posix(),
        "extension": path.suffix.lower(),
        "size_bytes": path.stat().st_size,
    }


def build_manifest(product_dir: Path, image_dir: Path) -> dict[str, object]:
    product_documents = [
        record(path, product_dir)
        for path in visible_files(product_dir)
        if path.suffix.lower() in DOCUMENT_EXTENSIONS
    ]
    images = []
    for path in visible_files(image_dir):
        extension = path.suffix.lower()
        if extension not in IMAGE_EXTENSIONS:
            continue
        item = record(path, image_dir)
        item.update({
            "browser_ready": extension in BROWSER_READY_EXTENSIONS,
            "role_hints_from_filename_only": role_hints(path),
            "visual_review_required": True,
        })
        images.append(item)
    return {
        "product_library_dir": str(product_dir),
        "image_dir": str(image_dir),
        "summary": {
            "product_documents": len(product_documents),
            "image_candidates": len(images),
            "conversion_required": sum(not bool(item["browser_ready"]) for item in images),
        },
        "product_documents": product_documents,
        "image_candidates": images,
        "notice": "Filename role hints are inventory aids only; visually inspect every selected image.",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inventory product-library documents and product-image candidates.")
    parser.add_argument("--product-library-dir", required=True)
    parser.add_argument("--image-dir", required=True)
    parser.add_argument("--output", help="Optional UTF-8 JSON output path; stdout is always emitted.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        product_dir = existing_directory(args.product_library_dir, "product_library_dir")
        image_dir = existing_directory(args.image_dir, "image_dir")
        manifest = build_manifest(product_dir, image_dir)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    encoded = json.dumps(manifest, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
