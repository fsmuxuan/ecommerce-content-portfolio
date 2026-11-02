# Content production rules

## Table of contents

1. Evidence hierarchy
2. Keyword governance
3. 1688 titles
4. Five main images
5. Inquiry detail page
6. Cross-output de-duplication
7. Common errors

## 1. Evidence hierarchy

- `A confirmed`: may be used within the confirmed scope.
- `B pending review`: rewrite as configurable or subject to order confirmation; do not state as fixed fact.
- `C market candidate`: may guide keyword research only; never becomes a product claim.
- `D prohibited`: internal cost, margin, supplier identity, private bid data, invented certification, sales, inventory, delivery, performance, or absolute claim.

An image proves only what is visible. A keyword proves search language, not material, capacity, certification, ownership, warranty, or performance.

Keep every product's facts, images, certifications, configurations, and customer evidence isolated. Cross-product learning may transfer only a method or test hypothesis.

## 2. Keyword governance

Use only terms marked usable, testing, or validated for the target platform and listing type. Review raw search suggestions before use. Never use disabled terms. Reassess terms before transferring them between platforms.

Read the product facts before the keyword pool. When a keyword implies an unconfirmed fact, remove it or qualify it; do not change the product library automatically.

## 3. Product titles: company-wide hard cap

Default to 10. Use one core product term, one or two long-tail terms, and one procurement-intent term. Put the core term early. Test meaningfully different intents such as scene, specification, structure, supply mode, or buyer problem; do not create quantity by rearranging the same words.

No title for any platform may exceed **60 full-width counting units**: each Chinese character counts as 2; every English letter, digit, space, and punctuation mark counts as 1. A pure-Chinese title may therefore contain no more than **30 Chinese characters**. This is a company hard cap, not a reason to pad weak terms. A verified platform limit that is lower still takes precedence.

Keep a title concise and meaningful. Do not set a minimum length. For 1688, use no emoji or punctuation and at most two spaces; do not include region, company, or brand by default.

Separate spot and custom. Preserve exact product variants and operating structures. Do not mix related products, configurations, hardware, colors, or service boundaries.

Validate every title with `scripts/title/validate_title.py`. Delivery must show `fullwidth_units`, the 60-unit limit, core keyword, long-tail terms, procurement term, distinct test angle, and passing result. The portfolio manifest independently rechecks the same cap before history can be committed.

## 4. Five main images

Use one primary real photo for each role:

1. recognizable complete product;
2. attributable real use scene;
3. visible product detail;
4. confirmed model, size, grade, SKU, accessory, or color choices;
5. one exact real product on pure `#FFFFFF`, without copy.

Cards 1–3 have one heading and at most one support line. Card 4 is a compact choice view, not a dense specification table. Product or product theme occupies more than half of cards 1–3. Never use unrelated projects, third-party watermarks, unknown logos, or generated scenes as evidence.

Export five PNGs at each of 1500×1500, 1000×1000, and 800×800. Verify dimensions, mobile readability, image loading, and white-product consistency.

## 5. Inquiry detail page

Build the page as a picture-led proof sequence. Buyers should see the product in a relatable setting before reading long text. Use these modules in order:

1. buyer scene and expected use result — 1–3 real scenario images;
2. product definition and three short purchase reasons — one concise line per reason;
3. quality detail proof — 2–4 sharp real close-ups of material, structure, connection, finish, or visible process;
4. specifications, options, and accessories — selection visual plus only decision-critical facts;
5. workshop / supply / customization proof — workshop or production images only when the company identity and image evidence support the claim;
6. matching customer-use scenes — group real scenes by buyer situation; never merge separate projects into one case;
7. professional packaging, delivery, and service — real packing / dispatch images plus confirmed terms;
8. structured inquiry.

Write as the supplier. Keep Chinese primary and concise English for product names, headings, specifications, procurement conditions, and CTA. Generate specification tables from confirmed product facts. Each image-led module may have one headline (recommended <=14 Chinese characters) and one support line; replace long sales paragraphs with real, attributable pictures. Images are proof, not decoration.

For company-strength imagery, use this evidence mapping:

- workshop: prove only the visible workshop/process and only call it "厂家/工厂" when both company identity and production evidence are confirmed;
- product detail: point to visible detail, not invisible material grades or performance;
- packing: show actual protection, labeling, palletizing, or dispatch practices without exposing buyer data;
- customer scenes: show product-environment fit without claiming every image belongs to one customer or project.

If a module lacks truthful images, hide the claimed advantage and write the exact missing-photo request to `02_素材余量与补拍清单.md`. Do not fill the gap with stock imagery, generated project scenes, or generic factory claims.

Use this quotation CTA when appropriate:

`请把用途、规格、数量和收货地区发来，我按需求给你报价和交期。`

`Please send your application, specifications, quantity, and delivery location. We’ll quote based on your requirements.`

Use a 750 CSS-pixel root, mark every section with a unique `data-export-section`, export at 2× scale, and require 1500-pixel-wide complete and module PNGs.

## 6. Cross-output de-duplication

De-duplication has four layers:

- exact title and normalized title match;
- near-semantic title similarity against current and historical versions;
- same real image in multiple current main-image roles or the same historical role;
- near-identical main-image and detail-page copy.

The detail page may expand a topic introduced by a main image, but must not repeat its headline and subline as a module headline or paragraph. Main images establish recognition and selection; detail modules prove quality, supplier capability, fit, and delivery confidence.

When the image library cannot support another visibly distinct version, issue the shooting brief. Do not claim novelty through layout changes alone.

## 7. Common errors

- Generating before reading the product facts and content history.
- Treating a file rename as a new image.
- Counting unreviewed images as available inventory.
- Using the same angle across titles, all five main images, and every detail module.
- Claiming a product or method improved from one short period without a comparable baseline.
- Updating global rules from one product while transferring product facts by accident.
- Recording a failed or incomplete export as a completed version.
