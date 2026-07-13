from pathlib import Path
import unittest


class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parent.parent

    def test_required_governance_documents_exist(self):
        names = (
            "HERMES_COMPANY_MANUAL.md", "ENGINEERING_STANDARDS.md",
            "AI_GOVERNANCE.md", "RISK_PHILOSOPHY.md", "PRODUCT_VISION.md",
            "V2_ROADMAP.md",
        )
        self.assertTrue(all((self.root / "Docs" / name).is_file() for name in names))
        self.assertTrue((self.root / "VERSION.md").is_file())

    def test_governance_preserves_human_risk_and_paper_boundaries(self):
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (self.root / "Docs").glob("*.md")
        )
        self.assertIn("Risk Manager veto is final", text)
        self.assertIn("Only a human may approve", text)
        self.assertIn("PAPER mode only", text)
        version = (self.root / "VERSION.md").read_text(encoding="utf-8")
        self.assertIn("Version: 0.1.0-rc1", version)
        self.assertIn("Live trading: disabled", version)


if __name__ == "__main__":
    unittest.main()
