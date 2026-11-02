#!/usr/bin/env python3
"""Browser-level smoke test for the vendored main-image and detail exporters."""

from __future__ import annotations

import base64
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
APP_NODE = Path("/Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node")


def run(command: list[str]) -> None:
    result = subprocess.run(command, text=True, capture_output=True, check=False, timeout=55)
    if result.returncode:
        raise RuntimeError(f"Command failed: {command}\nstdout={result.stdout}\nstderr={result.stderr}")


def main() -> int:
    node = shutil.which("node") or (str(APP_NODE) if APP_NODE.is_file() else None)
    if not node:
        raise RuntimeError("Node runtime not found")
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        images = root / "images"
        images.mkdir()
        roles = ["product-overview", "usage-scene", "product-detail", "sku-colors", "white-product"]
        cards = []
        for index, role in enumerate(roles, start=1):
            image = images / f"image-{index}.png"
            image.write_bytes(png)
            cards.append({
                "id": role,
                "title": "" if role == "white-product" else "测试产品",
                "subtitle": "" if role == "white-product" else "真实素材",
                "image": image.name,
            })
        brief = root / "brief.json"
        brief.write_text(json.dumps({"product_name_cn": "测试产品", "product_name_en": "Test Product", "cards": cards}, ensure_ascii=False), encoding="utf-8")
        main_output = root / "main-output"
        run([
            "python3", str(SKILL_ROOT / "scripts" / "main-images" / "build_from_brief.py"),
            "--brief", str(brief), "--image-dir", str(images), "--output-dir", str(main_output),
        ])
        run([
            node, str(SKILL_ROOT / "scripts" / "main-images" / "export_main_images.js"),
            "--html", str(main_output / "platform-main-images.html"), "--output-dir", str(main_output),
        ])
        main_report = json.loads((main_output / "export-report.json").read_text(encoding="utf-8"))
        if any(len(main_report["profiles"][key]) != 5 for key in ("1500x1500", "1000x1000", "800x800")):
            raise RuntimeError("Main-image export count mismatch")

        detail_html = root / "detail.html"
        sections = "".join(f'<section data-export-section="{index:02d}-module" style="width:750px;height:120px;background:#{index}{index}{index};">模块 {index}</section>' for index in range(1, 9))
        detail_html.write_text(f'<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;padding:0}}*{{box-sizing:border-box}}</style></head><body><main data-export-width="750" style="width:750px">{sections}</main></body></html>', encoding="utf-8")
        detail_output = root / "detail-output"
        run([
            node, str(SKILL_ROOT / "scripts" / "detail-page" / "export_detail_page.js"),
            "--html", str(detail_html), "--output-dir", str(detail_output),
        ])
        detail_report = json.loads((detail_output / "export-report.json").read_text(encoding="utf-8"))
        if detail_report["targetPixelWidth"] != 1500 or detail_report["moduleCount"] != 8:
            raise RuntimeError("Detail export contract mismatch")
    print("Browser smoke test passed: 15 main images and 9 detail PNG files met the export contract.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
