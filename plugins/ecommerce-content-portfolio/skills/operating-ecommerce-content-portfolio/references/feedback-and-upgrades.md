# Feedback, reporting, and controlled upgrades

## Table of contents

1. Feedback contract
2. Import workflow
3. Metrics
4. Diagnostic routing
5. Global learning
6. Approval boundary

## 1. Feedback contract

Use `assets/feedback-template.csv` or the template created in the hub. Required columns:

| Field | Meaning |
|---|---|
| product_id | Registered product ID |
| version_id | Committed content version |
| platform | Marketplace |
| period_start / period_end | Comparable measurement window, ISO date |
| impressions | Product impressions |
| clicks | Product clicks or visits using one stable platform definition |
| inquiries | All inquiries |
| valid_inquiries | Qualified project or purchase inquiries |
| quotes | Formal quotations |
| orders | Completed orders using one stable definition |
| revenue | Optional order value |
| notes | Price, campaign, stock, season, or other concurrent change |

Do not combine incompatible platform definitions in one comparison. Record major concurrent changes in `notes`.

## 2. Import workflow

Import:

```bash
python3 scripts/portfolio_ops.py import-feedback \
  --file "/absolute/weekly-or-monthly-feedback.csv"
```

The importer rejects missing IDs, invalid dates, negative numbers, clicks above impressions, valid inquiries above inquiries, unknown products, and duplicate product/version/period rows.

Create a report:

```bash
python3 scripts/portfolio_ops.py report --days 7
python3 scripts/portfolio_ops.py report --days 30
```

Use 90 days only for longer-term comparison. Return the report and upgrade-proposal paths.

## 3. Metrics

- click-through rate = clicks / impressions;
- inquiry rate = inquiries / clicks;
- valid-inquiry rate = valid inquiries / inquiries;
- quote rate = quotes / valid inquiries;
- order rate = orders / quotes.

Report missing denominators as unavailable, not zero. Compare like-for-like periods and preserve absolute counts beside rates.

## 4. Diagnostic routing

Use the funnel to choose the next test surface:

- impressions down or absent: review title, keyword fit, category, attributes, information quality, and platform eligibility;
- impressions stable/up but click-through rate down: test main-image recognition, product clarity, and scene relevance;
- clicks stable/up but inquiry rate down: review detail page, specifications, quote entry, price/lead-time context, and buyer qualification;
- inquiry quality down: tighten product definition, application boundaries, minimum information required, and structured inquiry;
- quote/order conversion down: review commercial terms, follow-up, availability, delivery, and offer fit; content may not be the only cause.

Keep spot and custom products separate. Do not delete or rewrite a listing based on contradictory or insufficient platform data without backend verification.

## 5. Global learning

Product-level iteration happens after every validated feedback import. It may reprioritize:

- unused keyword and title angles;
- main-image roles and real assets;
- detail modules requiring clearer decision information;
- next required shooting tasks.

Global method proposals require evidence across at least the configured number of products and versions. A proposal is a test hypothesis, not a guaranteed best practice. It may transfer structures such as title patterns, content sequencing, asset standards, or measurement methods. It may never transfer product claims, images, certifications, private customers, or exact specifications.

## 6. Approval boundary

Reports write proposals with `pending-human-approval`. To approve one:

```bash
python3 scripts/portfolio_ops.py approve-upgrade \
  --proposal-file "/absolute/upgrade-proposals.json" \
  --proposal-id "proposal-id" \
  --approved-by "user-confirmed-name"
```

Approval appends an auditable strategy record. It does not silently rewrite the skill, product facts, or platform rules. When a core skill change is warranted, present the evidence, proposed diff, affected workflows, and rollback path; edit the skill only after explicit user authorization and re-run its validator and forward tests.
