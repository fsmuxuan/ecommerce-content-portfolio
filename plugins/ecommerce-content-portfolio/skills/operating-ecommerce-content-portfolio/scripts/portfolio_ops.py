#!/usr/bin/env python3
"""Persistent portfolio registry, de-duplication, asset warnings, and feedback reports."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from statistics import median


SCHEMA_VERSION = "1.0"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif", ".bmp", ".tif", ".tiff", ".heic", ".heif"}
KEYWORD_EXTENSIONS = {".md", ".txt", ".csv", ".xlsx", ".xls", ".json", ".yaml", ".yml"}
MAIN_ROLES = ["product-overview", "usage-scene", "product-detail", "sku-colors", "white-product"]
DETAIL_MODULES = [
    "01-application-solution",
    "02-product-definition",
    "03-advantages",
    "04-specifications-options",
    "05-supply-customization",
    "06-applications-projects",
    "07-packing-leadtime-service",
    "08-structured-inquiry",
]
CHINESE_RANGES = (
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF),
    (0x20000, 0x2EBEF),
)
TITLE_FULLWIDTH_UNIT_LIMIT = 60
DETAIL_EVIDENCE_ROLES = {
    "quality-detail": ("product-detail",),
    "factory-workshop": ("production",),
    "professional-packaging": ("packaging",),
    "buyer-matched-scenes": ("application", "usage-scene"),
}
ANGLE_ROTATION = ["scene", "structure", "selection", "supply", "procurement", "application", "detail", "service-boundary"]
FEEDBACK_COLUMNS = [
    "product_id", "version_id", "platform", "period_start", "period_end", "impressions", "clicks",
    "inquiries", "valid_inquiries", "quotes", "orders", "revenue", "notes",
]


def iso_now() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def append_jsonl(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
        if isinstance(item, dict):
            rows.append(item)
    return rows


def existing_dir(value: str, label: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        raise ValueError(f"{label} is not a directory: {path}")
    return path


def existing_keyword_source(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"keyword_library does not exist: {path}")
    if path.is_file() and path.suffix.lower() not in KEYWORD_EXTENSIONS:
        raise ValueError(f"unsupported keyword file: {path}")
    return path


def hub_path(value: str | None) -> Path:
    return Path(value).expanduser().resolve() if value else (Path.cwd() / "电商内容运营中枢").resolve()


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value)).lower()
    return "".join(char for char in value if char.isalnum())


def similarity(a: str, b: str) -> float:
    left, right = normalize_text(a), normalize_text(b)
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def is_chinese(character: str) -> bool:
    codepoint = ord(character)
    return any(start <= codepoint <= end for start, end in CHINESE_RANGES)


def title_fullwidth_units(title: str) -> int:
    return sum(2 if is_chinese(character) else 1 for character in title)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_id(value: str, fallback: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().lower()
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", "-", normalized, flags=re.UNICODE).strip("-")
    return (normalized[:48] or fallback).strip("-")


def default_config() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "method_version": "1.0.0",
        "created_at": iso_now(),
        "policies": {
            "near_duplicate_similarity": 0.86,
            "asset_yellow_unused_candidates": 2,
            "global_transfer_min_products": 2,
            "global_transfer_min_versions": 2,
            "require_human_approval_for_method_upgrade": True,
        },
    }


def ensure_hub(root: Path) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    for name in ("products", "reports", "upgrade-proposals", "approved-upgrades"):
        (root / name).mkdir(exist_ok=True)
    config_path = root / "hub-config.json"
    config = read_json(config_path)
    if config is None:
        config = default_config()
        write_json(config_path, config)
    index_path = root / "products-index.json"
    if not index_path.exists():
        write_json(index_path, {"schema_version": SCHEMA_VERSION, "products": []})
    feedback_path = root / "feedback-template.csv"
    if not feedback_path.exists():
        with feedback_path.open("w", encoding="utf-8-sig", newline="") as handle:
            csv.writer(handle).writerow(FEEDBACK_COLUMNS)
    return config


def inventory_keyword_source(source: Path) -> dict:
    if source.is_file():
        files = [source]
        root = source.parent
    else:
        root = source
        files = sorted(path for path in source.rglob("*") if path.is_file() and path.suffix.lower() in KEYWORD_EXTENSIONS)
    return {
        "source": str(source),
        "file_count": len(files),
        "files": [str(path.relative_to(root)) for path in files],
    }


def inventory_images(image_root: Path, previous: dict | None) -> dict:
    old_by_hash = {item.get("sha256"): item for item in (previous or {}).get("assets", []) if item.get("sha256")}
    assets = []
    for path in sorted(image_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        digest = sha256_file(path)
        old = old_by_hash.get(digest, {})
        assets.append({
            "asset_id": digest[:16],
            "sha256": digest,
            "relative_path": path.relative_to(image_root).as_posix(),
            "extension": path.suffix.lower(),
            "bytes": path.stat().st_size,
            "roles": old.get("roles", []),
            "reviewed": bool(old.get("reviewed", False)),
            "eligible": bool(old.get("eligible", True)),
            "privacy_ok": bool(old.get("privacy_ok", False)),
            "product_consistency_ok": bool(old.get("product_consistency_ok", False)),
            "notes": old.get("notes", ""),
            "used_count": int(old.get("used_count", 0)),
            "role_usage": old.get("role_usage", {}),
            "last_used_at": old.get("last_used_at"),
        })
    current_hashes = {item["sha256"] for item in assets}
    missing = [item for digest, item in old_by_hash.items() if digest not in current_hashes]
    return {
        "schema_version": SCHEMA_VERSION,
        "image_root": str(image_root),
        "updated_at": iso_now(),
        "instructions": "Agent must visually inspect each asset, then set roles, reviewed, privacy_ok, and product_consistency_ok. Filenames are not proof.",
        "assets": assets,
        "missing_from_source": missing,
    }


def update_index(root: Path, profile: dict) -> None:
    index_path = root / "products-index.json"
    index = read_json(index_path, {"schema_version": SCHEMA_VERSION, "products": []})
    products = [item for item in index.get("products", []) if item.get("product_id") != profile["product_id"]]
    products.append({
        "product_id": profile["product_id"],
        "product_name": profile["product_name"],
        "platform": profile["platform"],
        "listing_type": profile["listing_type"],
        "updated_at": profile["updated_at"],
    })
    index["products"] = sorted(products, key=lambda item: item["product_id"])
    write_json(index_path, index)


def register_product(args: argparse.Namespace) -> int:
    root = hub_path(args.hub)
    ensure_hub(root)
    product_library = existing_dir(args.product_library, "product_library")
    keyword_library = existing_keyword_source(args.keyword_library)
    image_dir = existing_dir(args.image_dir, "image_dir")
    product_name = args.product_name or product_library.name
    fallback = hashlib.sha256(str(product_library).encode("utf-8")).hexdigest()[:10]
    product_id = args.product_id or safe_id(product_name, fallback)
    product_dir = root / "products" / product_id
    product_dir.mkdir(parents=True, exist_ok=True)
    profile_path = product_dir / "profile.json"
    old_profile = read_json(profile_path, {})
    profile = {
        "schema_version": SCHEMA_VERSION,
        "product_id": product_id,
        "product_name": product_name,
        "platform": args.platform,
        "listing_type": args.listing_type,
        "product_library": str(product_library),
        "keyword_library": str(keyword_library),
        "image_dir": str(image_dir),
        "created_at": old_profile.get("created_at", iso_now()),
        "updated_at": iso_now(),
        "fact_isolation": "Product facts, claims, images, and certifications may not transfer to another product.",
    }
    write_json(profile_path, profile)
    catalog_path = product_dir / "asset-catalog.json"
    catalog = inventory_images(image_dir, read_json(catalog_path, {}))
    write_json(catalog_path, catalog)
    keyword_inventory = inventory_keyword_source(keyword_library)
    write_json(product_dir / "keyword-inventory.json", keyword_inventory)
    history = read_jsonl(product_dir / "content-history.jsonl")
    update_index(root, profile)
    context = {
        "hub_root": str(root),
        "product_dir": str(product_dir),
        "profile": profile,
        "keyword_inventory": keyword_inventory,
        "asset_summary": {
            "total": len(catalog["assets"]),
            "reviewed": sum(bool(item["reviewed"]) for item in catalog["assets"]),
            "eligible": sum(bool(item["eligible"]) for item in catalog["assets"]),
        },
        "previous_versions": len(history),
        "next_step": "Visually review asset-catalog.json, then run plan.",
    }
    write_json(product_dir / "run-context.json", context)
    print(json.dumps(context, ensure_ascii=False, indent=2))
    return 0


def locate_product(root: Path, product_id: str) -> tuple[Path, dict, dict, list[dict]]:
    product_dir = root / "products" / product_id
    profile = read_json(product_dir / "profile.json")
    catalog = read_json(product_dir / "asset-catalog.json")
    if profile is None or catalog is None:
        raise ValueError(f"Unknown product_id: {product_id}")
    return product_dir, profile, catalog, read_jsonl(product_dir / "content-history.jsonl")


def used_asset_roles(history: list[dict]) -> Counter:
    counter = Counter()
    for version in history:
        for card in version.get("main_images", []):
            digest = card.get("asset_sha256")
            role = card.get("role")
            if digest and role:
                counter[(digest, role)] += 1
    return counter


def asset_status(catalog: dict, history: list[dict], yellow_limit: int) -> dict:
    usage = used_asset_roles(history)
    coverage = {}
    for role in MAIN_ROLES:
        candidates = [item for item in catalog["assets"] if role in item.get("roles", []) and item.get("reviewed") and item.get("eligible") and item.get("privacy_ok") and item.get("product_consistency_ok")]
        unused = [item for item in candidates if usage[(item["sha256"], role)] == 0]
        if not candidates:
            level = "red"
        elif len(unused) < yellow_limit:
            level = "yellow"
        else:
            level = "green"
        coverage[role] = {
            "level": level,
            "eligible_candidates": len(candidates),
            "unused_candidates": len(unused),
            "unused_paths": [item["relative_path"] for item in unused],
        }
    detail_coverage = {}
    for evidence, accepted_roles in DETAIL_EVIDENCE_ROLES.items():
        candidates = [
            item for item in catalog["assets"]
            if any(role in item.get("roles", []) for role in accepted_roles)
            and item.get("reviewed") and item.get("eligible")
            and item.get("privacy_ok") and item.get("product_consistency_ok")
        ]
        detail_coverage[evidence] = {
            "level": "red" if not candidates else ("yellow" if len(candidates) < yellow_limit else "green"),
            "eligible_candidates": len(candidates),
            "candidate_paths": [item["relative_path"] for item in candidates],
            "accepted_roles": list(accepted_roles),
        }
    unreviewed = [item["relative_path"] for item in catalog["assets"] if not item.get("reviewed")]
    return {"coverage": coverage, "detail_evidence": detail_coverage, "unreviewed": unreviewed}


def next_angle(history: list[dict]) -> str:
    counts = Counter(item.get("strategy_angle") for item in history if item.get("strategy_angle"))
    return min(ANGLE_ROTATION, key=lambda angle: (counts[angle], ANGLE_ROTATION.index(angle)))


def shooting_brief(product_name: str, status: dict) -> str:
    labels = {
        "product-overview": ("产品整体图", "完整产品或完整项目，主体清晰，占画面主要面积，避免杂物遮挡"),
        "usage-scene": ("真实使用场景", "展示产品如何被使用以及周边环境，不伪造项目归属"),
        "product-detail": ("结构与细节近景", "对焦材质、连接、纹理、工艺或可见机构；不要只拍远景"),
        "sku-colors": ("规格与选项", "把真实型号、尺寸、颜色或配件选择拍清楚，并与知识库口径对应"),
        "white-product": ("纯白底产品图", "同一真实产品，正面或三分之二角度，白底无文案，保持实物一致"),
    }
    lines = [f"# {product_name} 素材余量与补拍清单", "", "## 本次状态", ""]
    for role in MAIN_ROLES:
        item = status["coverage"][role]
        label, advice = labels[role]
        state = {"red": "红色：必要素材缺失", "yellow": "黄色：未使用素材不多", "green": "绿色：目前充足"}[item["level"]]
        lines.append(f"- {label}：{state}；可用 {item['eligible_candidates']} 张，未使用 {item['unused_candidates']} 张。")
        if item["level"] != "green":
            lines.append(f"  补拍要求：{advice}。建议至少补充 3 张不同角度。")
    detail_labels = {
        "quality-detail": ("品质细节证据", "至少拍 3 张近景：材质表面、连接/收边/工艺；对焦清晰，不用远景代替"),
        "factory-workshop": ("厂家生产车间", "至少拍 3 张连续工序或生产环境，须能核实是本企业且不暴露客户/员工隐私"),
        "professional-packaging": ("专业包装与发货", "至少拍 3 张：内层保护、外箱/托盘固定、成品待发；不要展示地址和客户信息"),
        "buyer-matched-scenes": ("客户使用场景", "至少拍 3 个买家常见场景，完整展示产品与环境关系；不同项目不得拼成同一案例"),
    }
    lines.extend(["", "## 详情页成交证据素材"])
    for evidence, item in status["detail_evidence"].items():
        label, advice = detail_labels[evidence]
        state = {"red": "红色：本次不可展示为已具备优势", "yellow": "黄色：可用图片偏少，下一版前应补拍", "green": "绿色：可支撑图片优先展示"}[item["level"]]
        lines.append(f"- {label}：{state}；已确认可用 {item['eligible_candidates']} 张。")
        if item["level"] != "green":
            lines.append(f"  补拍要求：{advice}。")
    if status["unreviewed"]:
        lines.extend(["", "## 待人工视觉确认", "", f"还有 {len(status['unreviewed'])} 张图片未完成角色、隐私和产品一致性确认，不能计入正式素材余量。"])
    lines.extend(["", "## 通用拍摄边界", "", "不得出现未经允许的客户名称、车牌、地址、聊天记录或第三方标识；不得用相邻产品冒充目标产品。", ""])
    return "\n".join(lines)


def plan_run(args: argparse.Namespace) -> int:
    root = hub_path(args.hub)
    config = ensure_hub(root)
    product_dir, profile, catalog, history = locate_product(root, args.product_id)
    yellow = int(config["policies"]["asset_yellow_unused_candidates"])
    status = asset_status(catalog, history, yellow)
    previous_titles = []
    for item in history:
        previous_titles.extend(title.get("text", "") if isinstance(title, dict) else str(title) for title in item.get("titles", []))
    plan = {
        "schema_version": SCHEMA_VERSION,
        "created_at": iso_now(),
        "product_id": profile["product_id"],
        "product_name": profile["product_name"],
        "platform": profile["platform"],
        "listing_type": profile["listing_type"],
        "strategy_angle_recommendation": next_angle(history),
        "previous_version_count": len(history),
        "previous_titles": previous_titles,
        "asset_status": status,
        "gates": {
            "listing_type_confirmed": profile["listing_type"] in {"spot", "custom"},
            "all_assets_reviewed": not bool(status["unreviewed"]),
            "required_main_image_roles_available": all(item["eligible_candidates"] > 0 for item in status["coverage"].values()),
            "detail_evidence_gaps": [name for name, item in status["detail_evidence"].items() if item["level"] != "green"],
        },
        "content_separation": {
            "titles": "Test distinct search intent, not word-order variants.",
            "main_images": "Recognition, scene, visible detail, choices, pure white product.",
            "detail_page": "Expand buyer decisions without repeating main-image headlines verbatim.",
        },
    }
    output = Path(args.output).expanduser().resolve() if args.output else product_dir / "current-run"
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "00_run-plan.json", plan)
    (output / "02_素材余量与补拍清单.md").write_text(shooting_brief(profile["product_name"], status), encoding="utf-8")
    print(json.dumps({"run_plan": str(output / "00_run-plan.json"), "shooting_brief": str(output / "02_素材余量与补拍清单.md"), "gates": plan["gates"]}, ensure_ascii=False, indent=2))
    return 0


def title_texts(manifest: dict) -> list[str]:
    result = []
    for title in manifest.get("titles", []):
        result.append(str(title.get("text", "")) if isinstance(title, dict) else str(title))
    return [item.strip() for item in result if item.strip()]


def card_copy(card: dict) -> str:
    return " ".join(str(card.get(key, "")) for key in ("headline", "title", "subline", "subtitle") if card.get(key)).strip()


def detail_copy(module: dict) -> str:
    values = [module.get("headline", ""), module.get("summary", "")]
    values.extend(module.get("claims", []) if isinstance(module.get("claims"), list) else [])
    return " ".join(str(item) for item in values if item).strip()


def resolve_asset_digest(image_value: str, profile: dict, catalog: dict) -> str | None:
    value = str(image_value or "")
    by_relative = {item["relative_path"]: item["sha256"] for item in catalog["assets"]}
    if value in by_relative:
        return by_relative[value]
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path(profile["image_dir"]) / path
    if path.is_file():
        return sha256_file(path)
    return None


def validate_delivery(manifest: dict, profile: dict, catalog: dict, history: list[dict], threshold: float) -> dict:
    errors, warnings = [], []
    if manifest.get("product_id") != profile["product_id"]:
        errors.append("manifest product_id does not match registered product")
    if manifest.get("platform") != profile["platform"]:
        warnings.append("manifest platform differs from registered default")
    if manifest.get("listing_type") not in {"spot", "custom"}:
        errors.append("listing_type must be spot or custom before delivery")
    if not manifest.get("version_id"):
        errors.append("version_id is required")
    if not manifest.get("strategy_angle"):
        errors.append("strategy_angle is required")
    if not manifest.get("fact_source_files"):
        errors.append("fact_source_files is required; keyword sources alone are not product proof")

    titles = title_texts(manifest)
    if not titles:
        errors.append("at least one title is required")
    all_previous = []
    for item in history:
        all_previous.extend(title_texts(item))
    for index, title in enumerate(titles):
        units = title_fullwidth_units(title)
        if units > TITLE_FULLWIDTH_UNIT_LIMIT:
            errors.append(f"title exceeds {TITLE_FULLWIDTH_UNIT_LIMIT} full-width units ({units}; pure Chinese max 30): {title}")
        for other in titles[:index]:
            score = similarity(title, other)
            if score >= threshold:
                errors.append(f"current titles are near duplicates ({score:.2f}): {title} || {other}")
        for previous in all_previous:
            score = similarity(title, previous)
            if normalize_text(title) == normalize_text(previous):
                errors.append(f"title exactly repeats history: {title}")
            elif score >= threshold:
                warnings.append(f"title resembles history ({score:.2f}): {title} || {previous}")

    cards = manifest.get("main_images", [])
    roles = [card.get("role") for card in cards if isinstance(card, dict)]
    if roles != MAIN_ROLES:
        errors.append(f"main_images must use exact role order: {MAIN_ROLES}")
    if cards and (card_copy(cards[-1]) or cards[-1].get("headline") or cards[-1].get("title")):
        errors.append("white-product card must contain no copy")
    current_digests = []
    previous_usage = used_asset_roles(history)
    for card in cards:
        digest = resolve_asset_digest(card.get("image_path", ""), profile, catalog)
        if not digest:
            errors.append(f"cannot resolve real image for role {card.get('role')}: {card.get('image_path')}")
            continue
        card["asset_sha256"] = digest
        if digest in current_digests:
            errors.append(f"same real image reused across current main-image roles: {card.get('image_path')}")
        current_digests.append(digest)
        if previous_usage[(digest, card.get("role"))] > 0:
            warnings.append(f"image repeats the same historical role: {card.get('role')} / {card.get('image_path')}")

    modules = manifest.get("detail_modules", [])
    module_ids = [module.get("module_id") for module in modules if isinstance(module, dict)]
    if module_ids != DETAIL_MODULES:
        errors.append(f"detail_modules must use exact module order: {DETAIL_MODULES}")
    main_copies = []
    for card in cards:
        for key in ("headline", "title", "subline", "subtitle"):
            if card.get(key):
                main_copies.append(str(card[key]))
    for module in modules:
        parts = [module.get("headline", ""), module.get("summary", "")]
        if isinstance(module.get("claims"), list):
            parts.extend(module["claims"])
        for part in [str(item) for item in parts if item]:
            for main_copy in main_copies:
                score = similarity(part, main_copy)
                if score >= threshold:
                    warnings.append(f"detail copy repeats main-image copy ({score:.2f}): {module.get('module_id')} / {part}")

    required_outputs = ["titles", "main_image_html", "main_image_export_report", "detail_html", "detail_export_report"]
    outputs = manifest.get("outputs", {})
    for key in required_outputs:
        value = outputs.get(key)
        if not value:
            errors.append(f"missing output path: {key}")
        elif not Path(str(value)).expanduser().exists():
            errors.append(f"output does not exist: {key}={value}")

    return {
        "schema_version": SCHEMA_VERSION,
        "checked_at": iso_now(),
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "summary": {"titles": len(titles), "main_images": len(cards), "detail_modules": len(modules)},
        "normalized_manifest": manifest,
    }


def record_delivery(args: argparse.Namespace) -> int:
    root = hub_path(args.hub)
    config = ensure_hub(root)
    product_dir, profile, catalog, history = locate_product(root, args.product_id)
    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict):
        raise ValueError(f"invalid manifest: {manifest_path}")
    threshold = float(config["policies"]["near_duplicate_similarity"])
    report = validate_delivery(manifest, profile, catalog, history, threshold)
    report_path = manifest_path.parent / "validation-report.json"
    write_json(report_path, {key: value for key, value in report.items() if key != "normalized_manifest"})
    if args.commit and report["valid"]:
        version_id = manifest["version_id"]
        if any(item.get("version_id") == version_id for item in history):
            raise ValueError(f"version_id already recorded: {version_id}")
        normalized_manifest = report["normalized_manifest"]
        normalized_manifest["recorded_at"] = iso_now()
        append_jsonl(product_dir / "content-history.jsonl", normalized_manifest)
        by_hash = {item["sha256"]: item for item in catalog["assets"]}
        for card in normalized_manifest.get("main_images", []):
            item = by_hash.get(card.get("asset_sha256"))
            if not item:
                continue
            role = card.get("role")
            item["used_count"] = int(item.get("used_count", 0)) + 1
            role_usage = item.setdefault("role_usage", {})
            role_usage[role] = int(role_usage.get(role, 0)) + 1
            item["last_used_at"] = normalized_manifest["recorded_at"]
        catalog["updated_at"] = iso_now()
        write_json(product_dir / "asset-catalog.json", catalog)
    print(json.dumps({"validation_report": str(report_path), "valid": report["valid"], "committed": bool(args.commit and report["valid"]), "errors": report["errors"], "warnings": report["warnings"]}, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 2


def parse_number(row: dict, key: str) -> float:
    raw = str(row.get(key, "")).strip()
    if raw == "":
        return 0.0
    value = float(raw)
    if value < 0:
        raise ValueError(f"{key} cannot be negative")
    return value


def validate_feedback_row(row: dict, row_number: int) -> dict:
    missing = [key for key in ("product_id", "version_id", "period_start", "period_end") if not str(row.get(key, "")).strip()]
    if missing:
        raise ValueError(f"feedback row {row_number} missing: {', '.join(missing)}")
    start = dt.date.fromisoformat(str(row["period_start"]).strip())
    end = dt.date.fromisoformat(str(row["period_end"]).strip())
    if end < start:
        raise ValueError(f"feedback row {row_number}: period_end before period_start")
    numeric = {key: parse_number(row, key) for key in ("impressions", "clicks", "inquiries", "valid_inquiries", "quotes", "orders", "revenue")}
    if numeric["clicks"] > numeric["impressions"]:
        raise ValueError(f"feedback row {row_number}: clicks exceed impressions")
    if numeric["valid_inquiries"] > numeric["inquiries"]:
        raise ValueError(f"feedback row {row_number}: valid_inquiries exceed inquiries")
    result = {key: str(row.get(key, "")).strip() for key in FEEDBACK_COLUMNS}
    result.update(numeric)
    result["period_start"] = start.isoformat()
    result["period_end"] = end.isoformat()
    result["imported_at"] = iso_now()
    return result


def import_feedback(args: argparse.Namespace) -> int:
    root = hub_path(args.hub)
    ensure_hub(root)
    source = Path(args.file).expanduser().resolve()
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing_columns = [key for key in FEEDBACK_COLUMNS if key not in (reader.fieldnames or [])]
        if missing_columns:
            raise ValueError(f"feedback file missing columns: {', '.join(missing_columns)}")
        rows = [validate_feedback_row(row, index) for index, row in enumerate(reader, start=2)]
    existing = read_jsonl(root / "feedback.jsonl")
    keys = {(row["product_id"], row["version_id"], row["period_start"], row["period_end"]) for row in existing}
    known_products = {item.get("product_id") for item in read_json(root / "products-index.json", {}).get("products", [])}
    known_versions = load_versions(root)
    for row in rows:
        if row["product_id"] not in known_products:
            raise ValueError(f"unknown product_id in feedback: {row['product_id']}")
        if (row["product_id"], row["version_id"]) not in known_versions:
            raise ValueError(f"unknown or uncommitted version_id in feedback: {row['product_id']} / {row['version_id']}")
        key = (row["product_id"], row["version_id"], row["period_start"], row["period_end"])
        if key in keys:
            raise ValueError(f"duplicate feedback period: {key}")
        append_jsonl(root / "feedback.jsonl", row)
        keys.add(key)
    print(json.dumps({"imported": len(rows), "feedback_store": str(root / "feedback.jsonl")}, ensure_ascii=False, indent=2))
    return 0


def ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def fmt_percent(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.2f}%"


def load_versions(root: Path) -> dict[tuple[str, str], dict]:
    result = {}
    index = read_json(root / "products-index.json", {"products": []})
    for product in index.get("products", []):
        product_id = product.get("product_id")
        for version in read_jsonl(root / "products" / product_id / "content-history.jsonl"):
            result[(product_id, version.get("version_id"))] = version
    return result


def aggregate_feedback(rows: list[dict]) -> list[dict]:
    groups = defaultdict(lambda: defaultdict(float))
    meta = {}
    for row in rows:
        key = (row["product_id"], row["version_id"], row.get("platform", ""))
        for field in ("impressions", "clicks", "inquiries", "valid_inquiries", "quotes", "orders", "revenue"):
            groups[key][field] += float(row.get(field, 0))
        meta[key] = {"period_start": row["period_start"], "period_end": row["period_end"]}
    result = []
    for key, values in groups.items():
        item = {"product_id": key[0], "version_id": key[1], "platform": key[2], **values, **meta[key]}
        item["ctr"] = ratio(values["clicks"], values["impressions"])
        item["inquiry_rate"] = ratio(values["inquiries"], values["clicks"])
        item["valid_inquiry_rate"] = ratio(values["valid_inquiries"], values["inquiries"])
        item["quote_rate"] = ratio(values["quotes"], values["valid_inquiries"])
        item["order_rate"] = ratio(values["orders"], values["quotes"])
        result.append(item)
    return sorted(result, key=lambda item: (item["product_id"], item["period_end"], item["version_id"]))


def recommendation(current: dict, previous: dict | None) -> str:
    if not previous:
        return "当前只有一个可比版本，先继续收集同口径数据，不判断因果。"
    if current["impressions"] < previous["impressions"]:
        return "本期曝光下降，优先复核标题、关键词、类目和商品信息质量；不要仅凭此数据删除商品。"
    if current["ctr"] is not None and previous["ctr"] is not None and current["ctr"] < previous["ctr"]:
        return "曝光未下降但点击率下降，下一轮优先测试主图识别度与场景表达。"
    if current["inquiry_rate"] is not None and previous["inquiry_rate"] is not None and current["inquiry_rate"] < previous["inquiry_rate"]:
        return "点击后询盘率下降，下一轮优先复核详情页、规格选择、报价入口和交付边界。"
    return "主要漏斗指标未出现明确下降，保留当前版本并测试一个新的差异化角度。"


def build_upgrade_proposals(root: Path, aggregates: list[dict], versions: dict, config: dict) -> list[dict]:
    by_product = defaultdict(list)
    for item in aggregates:
        by_product[item["product_id"]].append(item)
    evidence_by_angle = defaultdict(list)
    for product_id, items in by_product.items():
        items.sort(key=lambda item: (item["period_end"], item["version_id"]))
        for previous, current in zip(items, items[1:]):
            version = versions.get((product_id, current["version_id"]), {})
            angle = version.get("strategy_angle")
            if not angle:
                continue
            for metric in ("ctr", "inquiry_rate", "valid_inquiry_rate"):
                before, after = previous.get(metric), current.get(metric)
                if before is None or after is None:
                    continue
                evidence_by_angle[(angle, metric)].append({
                    "product_id": product_id,
                    "previous_version": previous["version_id"],
                    "current_version": current["version_id"],
                    "delta": after - before,
                })
    proposals = []
    min_products = int(config["policies"]["global_transfer_min_products"])
    min_versions = int(config["policies"]["global_transfer_min_versions"])
    metric_labels = {"ctr": "点击率", "inquiry_rate": "询盘率", "valid_inquiry_rate": "有效询盘率"}
    for (angle, metric), items in evidence_by_angle.items():
        positive = [item for item in items if item["delta"] > 0]
        products = {item["product_id"] for item in positive}
        if len(products) < min_products or len(positive) < min_versions or len(positive) <= len(items) / 2:
            continue
        median_delta = median(item["delta"] for item in positive)
        proposal_id = hashlib.sha256(f"{angle}|{metric}|{len(positive)}|{sorted(products)}".encode("utf-8")).hexdigest()[:12]
        proposals.append({
            "proposal_id": proposal_id,
            "created_at": iso_now(),
            "scope": "global-method-candidate",
            "strategy_angle": angle,
            "metric": metric,
            "evidence": {"products": sorted(products), "positive_comparisons": len(positive), "all_comparisons": len(items), "median_positive_delta": median_delta, "comparisons": positive},
            "proposal": f"在更多同平台产品中把 {angle} 作为受控候选测试方向；已有跨产品比较与{metric_labels[metric]}正向变化相关。不得迁移任何产品事实、图片或认证。",
            "status": "pending-human-approval",
            "causality_warning": "This is an observed association, not proof that the content change caused the outcome.",
        })
    return proposals


def portfolio_report(args: argparse.Namespace) -> int:
    root = hub_path(args.hub)
    config = ensure_hub(root)
    rows = read_jsonl(root / "feedback.jsonl")
    today = dt.date.today()
    cutoff = today - dt.timedelta(days=int(args.days))
    filtered = [row for row in rows if dt.date.fromisoformat(row["period_end"]) >= cutoff]
    aggregates = aggregate_feedback(filtered)
    versions = load_versions(root)
    index = read_json(root / "products-index.json", {"products": []})
    names = {item["product_id"]: item.get("product_name", item["product_id"]) for item in index.get("products", [])}
    previous_by_product = {}
    lines = [f"# 电商内容运营全局报告（近 {args.days} 天）", "", f"生成时间：{iso_now()}", "", "## 全产品运营状态", "", "| 产品 | 已提交版本 | 红色素材角色 | 黄色素材角色 |", "|---|---:|---|---|"]
    for product in index.get("products", []):
        product_id = product["product_id"]
        try:
            _, _, catalog, product_history = locate_product(root, product_id)
            state = asset_status(catalog, product_history, int(config["policies"]["asset_yellow_unused_candidates"]))
            red = "、".join(role for role, item in state["coverage"].items() if item["level"] == "red") or "无"
            yellow = "、".join(role for role, item in state["coverage"].items() if item["level"] == "yellow") or "无"
            lines.append(f"| {names.get(product_id, product_id)} | {len(product_history)} | {red} | {yellow} |")
        except ValueError:
            lines.append(f"| {names.get(product_id, product_id)} | — | 档案异常 | — |")
    lines.extend(["", "## 产品与版本表现", "", "| 产品 | 版本 | 曝光 | 点击率 | 询盘率 | 有效询盘率 | 报价率 | 成交率 | 下一步 |", "|---|---|---:|---:|---:|---:|---:|---:|---|"])
    for item in aggregates:
        previous = previous_by_product.get(item["product_id"])
        action = recommendation(item, previous)
        lines.append(f"| {names.get(item['product_id'], item['product_id'])} | {item['version_id']} | {item['impressions']:.0f} | {fmt_percent(item['ctr'])} | {fmt_percent(item['inquiry_rate'])} | {fmt_percent(item['valid_inquiry_rate'])} | {fmt_percent(item['quote_rate'])} | {fmt_percent(item['order_rate'])} | {action} |")
        previous_by_product[item["product_id"]] = item
    if not aggregates:
        lines.append("| 暂无可用反馈 | — | — | — | — | — | — | — | 请按反馈模板导入数据 |")
    proposals = build_upgrade_proposals(root, aggregates, versions, config)
    lines.extend(["", "## 升级建议", ""])
    if proposals:
        for proposal in proposals:
            lines.append(f"- `{proposal['proposal_id']}`：{proposal['proposal']} 证据范围：{len(proposal['evidence']['products'])} 个产品、{proposal['evidence']['positive_comparisons']} 个正向比较。需人工确认后应用。")
    else:
        lines.append("当前没有达到跨产品升级门槛的策略；继续积累可比较的数据。")
    lines.extend(["", "## 解读边界", "", "报告展示的是关联和漏斗变化。平台流量、价格、库存、活动、季节及同时发生的改动都可能影响结果，不能把单次变化直接认定为内容造成。", ""])
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = root / "reports" / f"{stamp}_{args.days}d_运营报告.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    proposal_path = root / "upgrade-proposals" / f"{stamp}_升级建议.json"
    write_json(proposal_path, {"schema_version": SCHEMA_VERSION, "proposals": proposals})
    print(json.dumps({"report": str(report_path), "upgrade_proposals": str(proposal_path), "products_reported": len({item['product_id'] for item in aggregates})}, ensure_ascii=False, indent=2))
    return 0


def approve_upgrade(args: argparse.Namespace) -> int:
    root = hub_path(args.hub)
    config = ensure_hub(root)
    source = Path(args.proposal_file).expanduser().resolve()
    proposals = read_json(source, {}).get("proposals", [])
    proposal = next((item for item in proposals if item.get("proposal_id") == args.proposal_id), None)
    if proposal is None:
        raise ValueError(f"proposal_id not found: {args.proposal_id}")
    approval = {
        **proposal,
        "status": "approved",
        "approved_at": iso_now(),
        "approved_by": args.approved_by,
        "method_version_before": config.get("method_version"),
        "implementation_note": "Approval records the learned policy. It does not modify product facts or rewrite SKILL.md automatically.",
    }
    append_jsonl(root / "approved-upgrades" / "approved-strategies.jsonl", approval)
    print(json.dumps(approval, ensure_ascii=False, indent=2))
    return 0


def status(args: argparse.Namespace) -> int:
    root = hub_path(args.hub)
    config = ensure_hub(root)
    index = read_json(root / "products-index.json", {"products": []})
    feedback = read_jsonl(root / "feedback.jsonl")
    details = []
    for product in index.get("products", []):
        product_id = product["product_id"]
        try:
            _, _, catalog, history = locate_product(root, product_id)
            state = asset_status(catalog, history, int(config["policies"]["asset_yellow_unused_candidates"]))
            details.append({
                **product,
                "committed_versions": len(history),
                "red_asset_roles": [role for role, item in state["coverage"].items() if item["level"] == "red"],
                "yellow_asset_roles": [role for role, item in state["coverage"].items() if item["level"] == "yellow"],
                "unreviewed_assets": len(state["unreviewed"]),
            })
        except ValueError as exc:
            details.append({**product, "error": str(exc)})
    output = {"hub_root": str(root), "products": len(details), "feedback_rows": len(feedback), "product_status": details}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operate a persistent ecommerce content portfolio hub.")
    sub = parser.add_subparsers(dest="command", required=True)

    register = sub.add_parser("register", help="Register or refresh one product from three source paths.")
    register.add_argument("--product-library", required=True)
    register.add_argument("--keyword-library", required=True)
    register.add_argument("--image-dir", required=True)
    register.add_argument("--hub")
    register.add_argument("--product-name")
    register.add_argument("--product-id")
    register.add_argument("--platform", default="1688")
    register.add_argument("--listing-type", choices=("auto", "spot", "custom"), default="auto")
    register.set_defaults(func=register_product)

    plan = sub.add_parser("plan", help="Create a de-duplicated run plan and shooting-gap brief.")
    plan.add_argument("--product-id", required=True)
    plan.add_argument("--hub")
    plan.add_argument("--output")
    plan.set_defaults(func=plan_run)

    record = sub.add_parser("record", help="Validate a delivery manifest and optionally commit it to history.")
    record.add_argument("--product-id", required=True)
    record.add_argument("--manifest", required=True)
    record.add_argument("--hub")
    record.add_argument("--commit", action="store_true")
    record.set_defaults(func=record_delivery)

    feedback = sub.add_parser("import-feedback", help="Import weekly or monthly CSV feedback.")
    feedback.add_argument("--file", required=True)
    feedback.add_argument("--hub")
    feedback.set_defaults(func=import_feedback)

    report = sub.add_parser("report", help="Create a portfolio report and versioned upgrade proposals.")
    report.add_argument("--days", type=int, choices=(7, 30, 90), default=30)
    report.add_argument("--hub")
    report.set_defaults(func=portfolio_report)

    approve = sub.add_parser("approve-upgrade", help="Record explicit human approval of one upgrade proposal.")
    approve.add_argument("--proposal-file", required=True)
    approve.add_argument("--proposal-id", required=True)
    approve.add_argument("--approved-by", required=True)
    approve.add_argument("--hub")
    approve.set_defaults(func=approve_upgrade)

    show = sub.add_parser("status", help="Show portfolio-level status.")
    show.add_argument("--hub")
    show.set_defaults(func=status)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
