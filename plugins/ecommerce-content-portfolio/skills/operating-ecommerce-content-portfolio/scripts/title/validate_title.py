#!/usr/bin/env python3
"""Deterministically validate marketplace product-title constraints."""

from __future__ import annotations

import argparse
import json
import unicodedata


CHINESE_RANGES = (
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF),
    (0x20000, 0x2EBEF),
)
CUSTOM_TERMS = ("定制", "定做", "订做", "来样加工", "加工定制", "OEM", "贴牌")
MARKETING_TERMS = (
    "厂家直供",
    "源头厂家",
    "源头工厂",
    "自有工厂",
    "厂家直销",
    "生产厂家",
    "多规格可选",
    "批量供货",
    "现货",
    "批发",
)
EXTREME_TERMS = ("第一", "顶级", "唯一", "100%", "百分之百")


def is_chinese(character: str) -> bool:
    codepoint = ord(character)
    return any(start <= codepoint <= end for start, end in CHINESE_RANGES)


def fullwidth_units(title: str) -> int:
    """Count Chinese as two full-width units and every other character as one."""
    return sum(2 if is_chinese(character) else 1 for character in title)


# Kept for callers of earlier releases.
weighted_length = fullwidth_units


def _unique_matches(title: str, candidates: list[str] | tuple[str, ...]) -> list[str]:
    return [term for term in dict.fromkeys(candidates) if term and term.lower() in title.lower()]


def validate_title(
    title: str,
    *,
    platform: str = "1688",
    listing_type: str = "unknown",
    core_keywords: list[str] | None = None,
    max_fullwidth_units: int | None = None,
    target_minimum: int | None = None,
) -> dict[str, object]:
    platform_key = platform.strip().lower()
    listing_key = listing_type.strip().lower()
    if listing_key == "现货":
        listing_key = "spot"
    elif listing_key == "定制":
        listing_key = "custom"

    # This is the business-wide publication cap. A verified platform rule may
    # be stricter, but no platform output is allowed to exceed this cap.
    if max_fullwidth_units is None:
        max_fullwidth_units = 60

    length = fullwidth_units(title)
    errors: list[str] = []
    warnings: list[str] = []

    if not title.strip():
        errors.append("标题不得为空")
    if length > max_fullwidth_units:
        errors.append(f"超过{max_fullwidth_units}个全角计数单位（当前{length}；纯中文最多30字）")
    if target_minimum is not None and length < target_minimum:
        warnings.append(f"低于建议目标{target_minimum}个全角计数单位，不得为凑长度添加弱相关词")

    custom_matches = _unique_matches(title, CUSTOM_TERMS)
    if listing_key == "spot" and custom_matches:
        errors.append(f"现货商品禁用定制词：{'/'.join(custom_matches)}")
    elif listing_key not in {"spot", "custom"}:
        warnings.append("未确定现货或定制商品，不得直接发布")

    marketing_matches = _unique_matches(title, MARKETING_TERMS)
    if platform_key == "1688" and len(marketing_matches) > 1:
        errors.append(f"营销词超过1个：{'/'.join(marketing_matches)}")

    extreme_matches = _unique_matches(title, EXTREME_TERMS)
    if extreme_matches:
        errors.append(f"包含极限或绝对化用语：{'/'.join(extreme_matches)}")

    core_matches = _unique_matches(title, core_keywords or [])
    if core_keywords and len(core_matches) != 1:
        errors.append(f"核心产品词必须恰好1个，当前匹配：{'/'.join(core_matches) or '无'}")

    if platform_key == "1688":
        space_count = title.count(" ")
        if space_count > 2:
            errors.append(f"空格超过2个：{space_count}")
        forbidden_symbols = sorted(
            {
                character
                for character in title
                if not character.isspace()
                and not character.isalnum()
                and (unicodedata.category(character).startswith("P") or unicodedata.category(character).startswith("S"))
            }
        )
        if forbidden_symbols:
            errors.append(f"1688标题不使用标点或符号：{''.join(forbidden_symbols)}")

    return {
        "title": title,
        "platform": platform,
        "listing_type": listing_key,
        "fullwidth_units": length,
        "weighted_length": length,
        "fullwidth_unit_limit": max_fullwidth_units,
        "pure_chinese_character_limit": max_fullwidth_units // 2,
        "chinese_characters": sum(is_chinese(character) for character in title),
        "spaces": title.count(" "),
        "matched_core_keywords": core_matches,
        "matched_marketing_terms": marketing_matches,
        "errors": errors,
        "warnings": warnings,
        "pass": not errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a domestic marketplace product title")
    parser.add_argument("title")
    parser.add_argument("--platform", default="1688")
    parser.add_argument("--listing-type", default="unknown", choices=("spot", "custom", "unknown"))
    parser.add_argument("--core-keyword", action="append", default=[])
    parser.add_argument("--max-fullwidth-units", "--max-characters", dest="max_fullwidth_units", type=int, default=60)
    parser.add_argument("--target-minimum", type=int)
    args = parser.parse_args()
    result = validate_title(
        args.title,
        platform=args.platform,
        listing_type=args.listing_type,
        core_keywords=args.core_keyword,
        max_fullwidth_units=args.max_fullwidth_units,
        target_minimum=args.target_minimum,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
