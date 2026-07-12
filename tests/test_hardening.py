from pathlib import Path
import json,logging,tempfile,unittest
from core.health import GracefulShutdown,StartupChecks
from core.logger import JsonFormatter,setup_logger
from core.settings import RuntimeSettings
from database.journal import SQLiteAuditJournal
from database.maintenance import backup_database,restore_database
class HardeningTests(unittest.TestCase):
    def test_settings_default_to_paper(self): self.assertEqual("PAPER",RuntimeSettings.from_env({}).mode)
    def test_live_mode_cannot_be_enabled(self):
        with self.assertRaises(ValueError): RuntimeSettings.from_env({"HERMES_MODE":"LIVE"})
        with self.assertRaises(ValueError): RuntimeSettings.from_env({"HERMES_LIVE_TRADING":"true"})
    def test_typed_config_validation(self):
        with self.assertRaises(ValueError): RuntimeSettings.from_env({"HERMES_LOG_MAX_BYTES":"zero"})
    def test_structured_logging(self):
        record=logging.LogRecord("hermes",logging.INFO,"",0,"paper %s",("mode",),None); payload=json.loads(JsonFormatter().format(record)); self.assertEqual("paper mode",payload["message"])
    def test_graceful_shutdown(self):
        shutdown=GracefulShutdown(); self.assertFalse(shutdown.requested); shutdown.request(); self.assertTrue(shutdown.requested)
    def test_startup_and_database_health(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); journal=SQLiteAuditJournal(root/"db.sqlite3"); journal.initialize(); settings=RuntimeSettings("PAPER",root/"db.sqlite3",root/"logs",1000,1)
            self.assertTrue(StartupChecks(settings,journal).run().healthy)
    def test_backup_and_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/"source.sqlite3"; SQLiteAuditJournal(source).initialize(); backup=backup_database(source,root/"backup.sqlite3"); restored=restore_database(backup,root/"restored.sqlite3"); SQLiteAuditJournal(restored).validate_schema()
    def test_container_is_non_root_and_paper_only(self):
        root=Path(__file__).resolve().parent.parent; docker=(root/"Dockerfile").read_text(); compose=(root/"docker-compose.yml").read_text(); self.assertIn("USER hermes",docker); self.assertIn("HERMES_MODE: PAPER",compose); self.assertNotIn("LIVE",compose)
if __name__=="__main__": unittest.main()
