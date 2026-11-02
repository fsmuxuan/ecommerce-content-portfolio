from __future__ import annotations

import csv
import base64
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = SKILL_ROOT / "scripts" / "portfolio_ops.py"
MAIN_BUILDER = SKILL_ROOT / "scripts" / "main-images" / "build_from_brief.py"


class PortfolioOpsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.hub = self.root / "hub"
        self.product_library = self.root / "product"
        self.keyword_library = self.root / "keywords"
        self.image_dir = self.root / "images"
        for path in (self.product_library, self.keyword_library, self.image_dir):
            path.mkdir()
        (self.product_library / "产品主档.md").write_text("确认产品事实", encoding="utf-8")
        (self.keyword_library / "关键词.csv").write_text("词,状态\n测试产品,可用\n", encoding="utf-8")
        self.images = []
        for index in range(5):
            image = self.image_dir / f"image-{index + 1}.png"
            image.write_bytes(b"\x89PNG\r\n\x1a\n" + bytes([index]) * 32)
            self.images.append(image)

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args, expected=0):
        result = subprocess.run(
            ["python3", str(SCRIPT), *map(str, args)],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, expected, msg=f"stdout={result.stdout}\nstderr={result.stderr}")
        return result

    def register_and_classify(self):
        self.run_cli(
            "register",
            "--product-library", self.product_library,
            "--keyword-library", self.keyword_library,
            "--image-dir", self.image_dir,
            "--hub", self.hub,
            "--product-name", "测试产品",
            "--listing-type", "spot",
        )
        product_id = "测试产品"
        catalog_path = self.hub / "products" / product_id / "asset-catalog.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        roles = ["product-overview", "usage-scene", "product-detail", "sku-colors", "white-product"]
        for item, role in zip(catalog["assets"], roles):
            item.update({"roles": [role], "reviewed": True, "eligible": True, "privacy_ok": True, "product_consistency_ok": True})
        catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
        return product_id

    def make_manifest(self, product_id: str):
        output = self.root / "outputs"
        output.mkdir()
        files = {}
        for name in ("titles", "main_image_html", "main_image_export_report", "detail_html", "detail_export_report"):
            path = output / f"{name}.txt"
            path.write_text("ok", encoding="utf-8")
            files[name] = str(path)
        roles = ["product-overview", "usage-scene", "product-detail", "sku-colors", "white-product"]
        cards = []
        for role, image in zip(roles, self.images):
            cards.append({"role": role, "image_path": image.name, "headline": "" if role == "white-product" else role, "subline": ""})
        modules = [
            "01-application-solution", "02-product-definition", "03-advantages", "04-specifications-options",
            "05-supply-customization", "06-applications-projects", "07-packing-leadtime-service", "08-structured-inquiry",
        ]
        return {
            "product_id": product_id,
            "version_id": "20260814-v01",
            "platform": "1688",
            "listing_type": "spot",
            "strategy_angle": "scene",
            "fact_source_files": ["产品主档.md"],
            "titles": [
                {"text": "测试产品 户外场景使用 采购批发", "angle": "scene"},
                {"text": "测试产品 结构细节选择 工程采购", "angle": "structure"},
            ],
            "main_images": cards,
            "detail_modules": [{"module_id": module, "headline": f"模块 {index}", "claims": []} for index, module in enumerate(modules, start=1)],
            "outputs": files,
        }

    def test_register_plan_record_feedback_report(self):
        product_id = self.register_and_classify()
        plan_output = self.root / "run"
        self.run_cli("plan", "--hub", self.hub, "--product-id", product_id, "--output", plan_output)
        plan = json.loads((plan_output / "00_run-plan.json").read_text(encoding="utf-8"))
        self.assertTrue(plan["gates"]["required_main_image_roles_available"])
        self.assertTrue(all(item["level"] == "yellow" for item in plan["asset_status"]["coverage"].values()))
        self.assertEqual(plan["asset_status"]["detail_evidence"]["factory-workshop"]["level"], "red")
        self.assertEqual(plan["asset_status"]["detail_evidence"]["professional-packaging"]["level"], "red")
        self.assertIn("factory-workshop", plan["gates"]["detail_evidence_gaps"])

        manifest_path = self.root / "delivery-manifest.json"
        manifest_path.write_text(json.dumps(self.make_manifest(product_id), ensure_ascii=False, indent=2), encoding="utf-8")
        self.run_cli("record", "--hub", self.hub, "--product-id", product_id, "--manifest", manifest_path, "--commit")
        history = (self.hub / "products" / product_id / "content-history.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(history), 1)

        feedback_path = self.root / "feedback.csv"
        with feedback_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                "product_id", "version_id", "platform", "period_start", "period_end", "impressions", "clicks",
                "inquiries", "valid_inquiries", "quotes", "orders", "revenue", "notes",
            ])
            writer.writeheader()
            writer.writerow({
                "product_id": product_id, "version_id": "20260814-v01", "platform": "1688",
                "period_start": "2026-08-01", "period_end": "2026-08-07", "impressions": 1000,
                "clicks": 80, "inquiries": 8, "valid_inquiries": 5, "quotes": 3, "orders": 1,
                "revenue": 1000, "notes": "test",
            })
        self.run_cli("import-feedback", "--hub", self.hub, "--file", feedback_path)
        result = self.run_cli("report", "--hub", self.hub, "--days", "90")
        payload = json.loads(result.stdout)
        self.assertTrue(Path(payload["report"]).is_file())
        self.assertTrue(Path(payload["upgrade_proposals"]).is_file())

    def test_current_near_duplicate_titles_fail(self):
        product_id = self.register_and_classify()
        manifest = self.make_manifest(product_id)
        manifest["titles"] = [
            {"text": "测试产品 户外使用 工程采购"},
            {"text": "测试产品户外使用工程采购"},
        ]
        manifest_path = self.root / "duplicate-manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        result = self.run_cli("record", "--hub", self.hub, "--product-id", product_id, "--manifest", manifest_path, expected=2)
        self.assertIn("near duplicates", result.stdout)

    def test_title_over_60_fullwidth_units_fails(self):
        product_id = self.register_and_classify()
        manifest = self.make_manifest(product_id)
        manifest["titles"] = [{"text": "测" * 31, "angle": "scene"}]
        manifest_path = self.root / "long-title-manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        result = self.run_cli("record", "--hub", self.hub, "--product-id", product_id, "--manifest", manifest_path, expected=2)
        self.assertIn("full-width units", result.stdout)

    def test_main_image_builder_uses_vendored_template(self):
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        for image in self.images:
            image.write_bytes(png)
        roles = ["product-overview", "usage-scene", "product-detail", "sku-colors", "white-product"]
        cards = []
        for role, image in zip(roles, self.images):
            cards.append({
                "id": role,
                "title": "" if role == "white-product" else "测试产品",
                "subtitle": "" if role == "white-product" else "真实素材",
                "image": image.name,
            })
        brief = {"product_name_cn": "测试产品", "product_name_en": "Test Product", "cards": cards}
        brief_path = self.root / "brief.json"
        brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
        output = self.root / "main-output"
        result = subprocess.run(
            ["python3", str(MAIN_BUILDER), "--brief", str(brief_path), "--image-dir", str(self.image_dir), "--output-dir", str(output)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        html = (output / "platform-main-images.html").read_text(encoding="utf-8")
        self.assertIn('data-platform-card="white-product"', html)
        self.assertNotIn("{{CARDS}}", html)


if __name__ == "__main__":
    unittest.main()
