# Architecture and contracts

## Table of contents

1. Operating architecture
2. Product registration
3. Asset catalog
4. Run plan
5. Delivery manifest
6. Output structure
7. Status and failure behavior

## 1. Operating architecture

The hub is persistent data, not part of the skill installation:

```text
电商内容运营中枢/
├── hub-config.json
├── products-index.json
├── feedback-template.csv
├── feedback.jsonl
├── products/
│   └── <product_id>/
│       ├── profile.json
│       ├── keyword-inventory.json
│       ├── asset-catalog.json
│       ├── content-history.jsonl
│       ├── run-context.json
│       └── runs/<version_id>/
├── reports/
├── upgrade-proposals/
└── approved-upgrades/
```

The skill is reusable code and rules. The hub is user business history. Never store mutable product history inside the installed skill directory.

## 2. Product registration

Three paths are sufficient:

- `product_library`: product facts and public boundaries;
- `keyword_library`: approved, candidate, disabled, and tested terms;
- `image_dir`: real product and project imagery.

Use a stable explicit `product_id` when the company already has SKU or product codes. Otherwise the registration tool derives a readable ID from the product folder. Reusing the same ID refreshes inventory and preserves history.

`listing_type` values:

- `spot`: prohibit custom/made-to-order implications unless a separate service is confirmed;
- `custom`: allow confirmed customization wording but do not imply stock;
- `auto`: preflight only; do not deliver 1688 titles until resolved.

## 3. Asset catalog

Every asset has a SHA-256 content identity, so renaming a file does not reset its history. The agent must visually set:

- `reviewed`;
- `eligible`;
- `privacy_ok`;
- `product_consistency_ok`;
- `roles`;
- `notes`.

The five main roles are exact machine-readable values:

- `product-overview`;
- `usage-scene`;
- `product-detail`;
- `sku-colors`;
- `white-product`.

An asset counts as available only when all four booleans are true and its role matches. Green means at least two unused candidates remain. Yellow means at least one eligible candidate exists but fewer than two are unused. Red means no eligible candidate exists and main-image production must stop.

The shooting brief must name the missing role, visible subject, angle, minimum quantity, privacy boundary, and product-consistency requirement.

## 4. Run plan

`00_run-plan.json` provides history, recommended unused angle, asset status, and hard gates. It is an input to judgment, not finished copy.

Create `01_成套内容策划.json` before production with this minimum shape:

```json
{
  "product_id": "product-code",
  "version_id": "20260814-v01",
  "platform": "1688",
  "listing_type": "spot",
  "buyer": "target buyer",
  "quotation_goal": "qualified inquiry",
  "strategy_angle": "scene",
  "title_intents": [],
  "main_image_jobs": [],
  "detail_module_jobs": [],
  "fact_source_files": [],
  "excluded_or_unresolved_claims": [],
  "material_gaps": []
}
```

Do not begin rendering before this file exists and its choices are consistent with `00_run-plan.json`.

## 5. Delivery manifest

Use `assets/delivery-manifest-template.json`. Required rules:

- `product_id` matches registration;
- `version_id` is new and stable;
- `listing_type` is `spot` or `custom`;
- `strategy_angle` identifies the tested difference;
- `fact_source_files` contains actual product evidence files;
- titles include text, keyword roles, angle, `fullwidth_units`, the 60-unit limit, and validation result;
- main images use the exact five roles and real image paths;
- detail modules use the exact eight module IDs. When shown, workshop, packing, and customer-scene modules name their approved image roles;
- output paths point to formal files and export reports.

The validator checks current and historical title similarity, required roles and order, repeated main-image assets, historical image-role reuse, main/detail near-identical copy, real file resolution, and required outputs. Warnings require review; errors block history commit.

## 6. Output structure

```text
runs/<version_id>/
├── 00_run-plan.json
├── 01_成套内容策划.json
├── 02_素材余量与补拍清单.md
├── titles.md
├── main-images/
│   ├── platform-main-images.html
│   ├── product-main-image-brief.json
│   ├── master-1500/*.png
│   ├── platform_exports/1000x1000/*.png
│   ├── platform_exports/800x800/*.png
│   └── export-report.json
├── detail-page/
│   ├── product-detail.html
│   ├── 00_完整详情页_2x.png
│   ├── 01_*.png ... 08_*.png
│   └── export-report.json
├── delivery-manifest.json
└── validation-report.json
```

## 7. Status and failure behavior

Stop and report the exact blocker when:

- a required source path does not exist;
- the product remains ambiguous;
- spot/custom remains unresolved before title delivery;
- a required image role is red;
- sources conflict on a public claim;
- title validation fails;
- Chrome/Playwright or formal export fails;
- delivery validation has errors.

Do not claim complete, committed, published, or improved unless the corresponding evidence exists.
