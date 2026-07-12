from pathlib import Path
import tempfile,unittest
from core.health import StartupChecks
from core.settings import RuntimeSettings
from database.journal import SQLiteAuditJournal
class ReleaseCandidateTests(unittest.TestCase):
    def setUp(self): self.root=Path(__file__).resolve().parent.parent
    def test_required_release_documents_exist(self):
        names=("OPERATIONS_HANDBOOK.md","PAPER_TRADING_GUIDE.md","SAFETY_BOUNDARIES.md","INCIDENT_RESPONSE.md","RELEASE_NOTES_RC1.md")
        self.assertTrue(all((self.root/"Docs"/name).is_file() for name in names)); self.assertTrue((self.root/"FOUNDATIONS.md").is_file())
    def test_release_documents_describe_current_rc(self):
        readme=(self.root/"README.md").read_text(encoding="utf-8")
        notes=(self.root/"Docs"/"RELEASE_NOTES_RC1.md").read_text(encoding="utf-8")
        self.assertIn("Paper Trading RC1 candidate",readme)
        self.assertIn("corrupted internal bbolt metadata database",notes)
        self.assertIn("no Docker-specific source changes",notes)
    def test_fresh_install_health(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); settings=RuntimeSettings("PAPER",root/"data"/"fresh.sqlite3",root/"logs",1000,1); journal=SQLiteAuditJournal(settings.database_path); journal.initialize(); self.assertTrue(StartupChecks(settings,journal).run().healthy)
    def test_no_private_exchange_or_live_order_code(self):
        forbidden=("create_order(","place_order(","api_secret","withdraw(","binance.client","ccxt.")
        sources="\n".join(path.read_text(encoding="utf-8").lower() for path in self.root.rglob("*.py") if ".git" not in path.parts and "tests" not in path.parts)
        self.assertFalse([value for value in forbidden if value in sources])
    def test_release_is_paper_only(self):
        settings=RuntimeSettings.from_env({}); self.assertEqual("PAPER",settings.mode); self.assertFalse(settings.live_trading)
        with self.assertRaises(ValueError): RuntimeSettings.from_env({"HERMES_MODE":"LIVE"})
    def test_no_html_or_website_artifacts(self):
        self.assertEqual([],list(self.root.rglob("*.html")))
if __name__=="__main__": unittest.main()
