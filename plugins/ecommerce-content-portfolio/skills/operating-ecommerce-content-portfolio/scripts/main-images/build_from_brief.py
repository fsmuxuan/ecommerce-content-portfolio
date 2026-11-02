#!/usr/bin/env python3
"""Render a validated five-card brief with one primary image per card."""

from __future__ import annotations

import argparse
import html
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "assets" / "main-images" / "platform-five-image-master.html"
ORDER = ["product-overview", "usage-scene", "product-detail", "sku-colors", "white-product"]
NAMES = ["01_产品整体展示", "02_真实使用场景", "03_产品细节", "04_颜色与SKU选型", "05_白底产品图"]
FORBIDDEN = ("痛点", "核心卖点", "采购成本", "利润率", "100%", "最好", "最高级", "国家级")


def validate(brief: dict):
    cards = brief.get("cards")
    if not isinstance(cards, list) or [card.get("id") for card in cards] != ORDER:
        raise ValueError(f"cards must follow this exact order: {ORDER}")
    for index, card in enumerate(cards):
        if not isinstance(card.get("image"), str) or not card["image"].strip():
            raise ValueError(f"card {card.get('id')} requires one image")
        if index < 4 and len(card.get("title", "")) > 22:
            raise ValueError(f"card {card['id']} title is too long")
        if len(card.get("subtitle", "")) > 46:
            raise ValueError(f"card {card['id']} subtitle is too long")
    if cards[4].get("title") or cards[4].get("subtitle"):
        raise ValueError("white-product card must have no copy")
    visible = json.dumps(brief, ensure_ascii=False)
    for token in FORBIDDEN:
        if token in visible:
            raise ValueError(f"forbidden public token: {token}")


def source_path(value: str, image_dir: Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else image_dir / path


def copy_image(value: str, image_dir: Path, assets: Path, card_id: str) -> str:
    source = source_path(value, image_dir).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    assets.mkdir(parents=True, exist_ok=True)
    suffix = source.suffix.lower() or ".png"
    target = assets / f"{card_id}{suffix}"
    shutil.copy2(source, target)
    return target.name


def img(name: str, position: str) -> str:
    return f'<img class="primary-photo" style="object-position:{html.escape(position, quote=True)}" src="assets/{html.escape(name, quote=True)}" alt="真实产品图">'


def render_cards(brief: dict, copied: dict[str, str]) -> str:
    cards = {card["id"]: card for card in brief["cards"]}
    rendered = []
    for index, card_id in enumerate(ORDER[:3]):
        card = cards[card_id]
        english = ""
        if index == 0 and brief.get("product_name_en"):
            english = f'<div class="english">{html.escape(brief["product_name_en"])}</div>'
        rendered.append(
            f'<section class="platform-card {card_id}-card" data-platform-card="{card_id}" data-export-section="{index + 1:02d}-{card_id}" data-export-name="{NAMES[index]}">'
            f'{img(copied[card_id], card.get("object_position", "center center"))}<div class="photo-shade"></div>'
            f'<div class="copy">{english}<h2 class="title">{html.escape(card.get("title", ""))}</h2><p class="subtitle">{html.escape(card.get("subtitle", ""))}</p></div></section>'
        )
    sku = cards["sku-colors"]
    systems = "".join(
        f'<div class="system"><strong>{html.escape(str(item[0]))}</strong><span>{html.escape(str(item[1]))}</span></div>'
        for item in sku.get("systems", [])[:4]
    )
    chips = "".join(
        f'<div class="chip"><div class="swatch" style="background:{html.escape(str(item[1]), quote=True)}"></div>{html.escape(str(item[0]))}</div>'
        for item in sku.get("chips", [])[:8]
    )
    rendered.append(
        f'<section class="platform-card sku-card" data-platform-card="sku-colors" data-export-section="04-sku-colors" data-export-name="{NAMES[3]}">'
        f'{img(copied["sku-colors"], sku.get("object_position", "30% center"))}<div class="photo-shade"></div>'
        f'<div class="sku-panel"><h2 class="title">{html.escape(sku.get("title", ""))}</h2><p class="subtitle">{html.escape(sku.get("subtitle", ""))}</p><div class="system-list">{systems}</div><div class="chip-title">可选规格 / OPTIONS</div><div class="chips">{chips}</div></div></section>'
    )
    rendered.append(
        f'<section class="platform-card white-card" data-platform-card="white-product" style="background:#FFFFFF" data-export-section="05-white-product" data-export-name="{NAMES[4]}">'
        f'{img(copied["white-product"], "center center")}</section>'
    )
    return "\n".join(rendered)


def build(brief_path: Path, image_dir: Path, output_dir: Path) -> Path:
    brief_path = brief_path.resolve()
    image_dir = image_dir.resolve()
    output_dir = output_dir.resolve()
    if not image_dir.is_dir():
        raise NotADirectoryError(image_dir)
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    validate(brief)
    output_dir.mkdir(parents=True, exist_ok=True)
    assets = output_dir / "assets"
    copied = {card["id"]: copy_image(card["image"], image_dir, assets, card["id"]) for card in brief["cards"]}
    theme = {"deep": "#07343D", "accent": "#DDF34D", "paper": "#F7FAF8", "ink": "#12343A", **brief.get("theme", {})}
    rendered = TEMPLATE.read_text(encoding="utf-8")
    rendered = rendered.replace("{{PAGE_TITLE}}", html.escape(brief.get("product_name_cn", "平台主图五张")))
    for key in ("deep", "accent", "paper", "ink"):
        rendered = rendered.replace("{{" + key.upper() + "}}", theme[key])
    rendered = rendered.replace("{{CARDS}}", render_cards(brief, copied))
    html_path = output_dir / "platform-main-images.html"
    html_path.write_text(rendered, encoding="utf-8")
    shutil.copy2(brief_path, output_dir / "product-main-image-brief.json")
    manifest = {"brief": str(brief_path), "image_dir": str(image_dir), "order": ORDER, "copied_assets": copied}
    (output_dir / "input-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return html_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", type=Path, required=True)
    parser.add_argument("--image-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(build(args.brief, args.image_dir, args.output_dir))


if __name__ == "__main__":
    main()
