---
name: operating-ecommerce-content-portfolio
description: Operate an entire ecommerce product portfolio from one skill. Use when Codex must take a product knowledge library, keyword library, and real image library and produce platform titles, a five-image marketplace main-image pack, and a bilingual inquiry detail page while managing every product in one persistent hub, preventing repeated titles/copy/image roles, warning when photo material is low, importing weekly or monthly performance feedback, reporting portfolio results, and creating controlled self-iteration or skill-upgrade proposals. Supports 1688 and similar domestic marketplaces; keeps facts and assets isolated by product.
---

# 电商内容运营中枢

## Overview

Turn three source paths into one persistent operating loop for all products: plan, produce titles/main images/detail page, validate, record, measure, and improve. Keep product evidence isolated; share only validated operating methods across products.

## Required inputs

Accept only these normal inputs:

1. product knowledge library path;
2. keyword library path, either a folder or a supported file;
3. real product image library path.

Infer the product name and use `1688` as the default platform. Infer `spot` or `custom` from the product library; if still ambiguous, ask only that one question before generating publishable titles. Accept optional product name, product ID, platform, output path, or hub path when supplied.

Use `<current-workspace>/电商内容运营中枢` as the default persistent hub. Run commands from the workspace root so every agent working in that workspace resolves the same hub without asking the user again.

## Read before acting

Read these references completely:

- [architecture-and-contracts.md](references/architecture-and-contracts.md) for hub structure, roles, manifests, and outputs;
- [content-production-rules.md](references/content-production-rules.md) before writing titles, main images, or detail content;
- [platform-detail-page-adapters.md](references/platform-detail-page-adapters.md) when adapting a page for 1688, Taobao, Douyin Shop, Baidu AiCaigou, or researching public competitor references;
- [feedback-and-upgrades.md](references/feedback-and-upgrades.md) only when importing operating data, reporting results, or proposing an upgrade.

## End-to-end workflow

### 1. Register or refresh the product

Run:

```bash
python3 scripts/portfolio_ops.py register \
  --product-library "/absolute/product-knowledge" \
  --keyword-library "/absolute/keyword-library" \
  --image-dir "/absolute/real-product-images" \
  --platform 1688 \
  --listing-type auto
```

Use the returned `product_id`. Registration never edits source libraries. It inventories keywords and image hashes, preserves prior roles and usage, and links the product to the global index.

If listing type is inferred, re-run registration with `--listing-type spot` or `--listing-type custom` before title delivery. Never mix the two.

### 2. Review evidence and classify images

Read the product entry, relevant product facts, platform rules, approved keywords, and only files relevant to this product. Treat search terms as demand evidence, not proof of product facts.

Visually inspect every candidate image before using it. Update the product's `asset-catalog.json`:

- set `reviewed: true` only after visual inspection;
- set `privacy_ok` and `product_consistency_ok` explicitly;
- set `eligible: false` for unrelated, private, duplicate-quality, misleading, or unusable assets;
- assign one or more exact main-image roles where truthful: `product-overview`, `usage-scene`, `product-detail`, `sku-colors`, `white-product`;
- add detail roles such as `production`, `packaging`, `accessory`, `installation`, or `application` in addition to main roles when useful. For a strong picture-led detail page, specifically classify `production`, `packaging`, and `application` when truthful.

Do not infer an image role from its filename alone.

### 3. Plan before producing

Choose a new version ID such as `20260814-v01` and create a version output folder under:

`<hub>/products/<product_id>/runs/<version_id>`

Run:

```bash
python3 scripts/portfolio_ops.py plan \
  --product-id "<product_id>" \
  --output "/absolute/version-output"
```

Read `00_run-plan.json` and `02_素材余量与补拍清单.md`. Stop main-image production when any required role is red. Treat a red or yellow detail-evidence role as a required disclosure: do not claim factory/workshop, professional packing, or matched customer scenes without the related verified images, and give the user the exact photo brief. Never fabricate a replacement product, project, factory, certification, or use scene.

Before generating anything, write `01_成套内容策划.json` containing:

- target product, platform, listing type, buyer, and quotation goal;
- one differentiated `strategy_angle` not exhausted by history;
- title keyword groups and distinct search intents;
- five main-image jobs, selected real images, and short copy;
- eight detail-page module jobs, ensuring they expand buyer decisions without repeating main-image headlines;
- fact source files and excluded or unresolved claims;
- material gaps and planned substitutions or hidden sections.

### 4. Generate and validate titles

Default to 10 titles unless the user specifies a count. Use the title rules in [content-production-rules.md](references/content-production-rules.md). Validate every title with the company-wide 60-full-width-unit cap:

```bash
python3 scripts/title/validate_title.py "标题" \
  --platform 1688 \
  --listing-type spot \
  --core-keyword "核心词" \
  --max-fullwidth-units 60
```

Remove all errors. `汉字=2` and every other visible character (including space and punctuation) `=1`; pure Chinese is capped at 30 characters. Compare against `00_run-plan.json` history; do not deliver exact duplicates, near duplicates, or word-order-only variants. Write `titles.md` with full-width-unit counts, keyword roles, test angles, and validation status.

### 5. Build the five main images

Use exactly these roles and order:

1. product overview;
2. real usage scene;
3. visible product detail;
4. SKU/color/model selection;
5. pure-white real product with no copy.

Create the five-card brief described in [architecture-and-contracts.md](references/architecture-and-contracts.md), then run:

```bash
python3 scripts/main-images/build_from_brief.py \
  --brief "/absolute/product-main-image-brief.json" \
  --image-dir "/absolute/real-product-images" \
  --output-dir "/absolute/version-output/main-images"

node scripts/main-images/export_main_images.js \
  --html "/absolute/version-output/main-images/platform-main-images.html" \
  --output-dir "/absolute/version-output/main-images"
```

If `node` is unavailable, locate the bundled workspace or app Node runtime and run the same script with that absolute executable path. The exporter also accepts `PLAYWRIGHT_MODULE` and `--chrome` when auto-discovery is unavailable.

Verify five 1500×1500, five 1000×1000, and five 800×800 PNG files. Treat the white-background image as commercially ready only after comparison with the original product.

### 6. Build the inquiry detail page

Use `assets/detail-page/universal-inquiry-detail-master-v2.html` as the design reference. Build the eight required modules in the picture-led sequence: buyer scene, short purchase reasons, quality details, selection, workshop/supply proof, matched-use scenes, packing/service, inquiry. Use product-specific colors and real images, and keep Chinese primary with concise English.

Favor images over paragraphs. A complete page should visibly cover, when evidence exists: factory/workshop, product quality close-ups, professional packaging, and buyer-matched customer-use scenes. Each section uses a short title and one supporting line; no unverified image, claim, or section may be added merely to complete the layout. Apply the platform adapter before rendering: 1688 procurement, Taobao consumer decision, Douyin video continuity, or AiCaigou search-to-inquiry qualification.

When a user requests online competitor reference, conduct the controlled research protocol in [platform-detail-page-adapters.md](references/platform-detail-page-adapters.md), store only the structured method observations in `03_竞品页面参考摘要.md`, and never reuse competitor content or assets.

Export with:

```bash
node scripts/detail-page/export_detail_page.js \
  --html "/absolute/version-output/detail-page/product-detail.html" \
  --output-dir "/absolute/version-output/detail-page"
```

Use the bundled workspace or app Node runtime when the shell does not expose `node`.

Require a 750 CSS-pixel root, 2× scale, one 1500-pixel-wide full-page PNG, one 1500-pixel-wide PNG for each module, and a passing export report. Do not substitute an ordinary screenshot.

### 7. Validate and commit the complete version

Copy `assets/delivery-manifest-template.json` into the version folder and fill it with real files, content, roles, sources, and output paths. First validate without committing:

```bash
python3 scripts/portfolio_ops.py record \
  --product-id "<product_id>" \
  --manifest "/absolute/delivery-manifest.json"
```

Resolve all errors. Review warnings about historical titles, image-role reuse, or main/detail copy overlap. After all formal outputs pass, repeat with `--commit`. Never write an incomplete or failed run into content history.

### 8. Report completion

Return links to:

- `01_成套内容策划.json`;
- `titles.md`;
- five-image HTML and 15 PNG exports;
- detail HTML, full-page PNG, module PNGs, and export report;
- `02_素材余量与补拍清单.md`;
- `03_竞品页面参考摘要.md` when competitor-reference research was requested;
- `delivery-manifest.json` and `validation-report.json`.

State the exact product/version, whether history was committed, all yellow/red material warnings, missing evidence, and any intentionally omitted claim or module. Distinguish local generation and validation from marketplace publication; do not claim publication unless it actually occurred.

## Feedback and self-iteration

When the user supplies weekly or monthly operating data, follow [feedback-and-upgrades.md](references/feedback-and-upgrades.md). Import data, generate a 7/30/90-day portfolio report, and create versioned upgrade proposals.

Automatically update product operating history and the approved strategy ledger. Do not silently rewrite `SKILL.md`, product facts, certifications, or platform rules. Applying a global strategy requires explicit approval recorded with `approve-upgrade`. An approved method may change future testing priority; it may never transfer facts or images between products.

## Non-negotiable gates

- Plan before generating.
- Read history before selecting title angles, copy, or images.
- Keep product facts and assets isolated by `product_id`.
- Use only approved keywords and confirmed public facts.
- Stop on missing required real-image roles.
- Warn when fewer than two unused eligible images remain for a required role.
- Validate all outputs before committing history.
- Treat performance reports as observed associations, not proof of causality.
- Preserve every method change as a reviewable version; require human approval for global upgrades.
