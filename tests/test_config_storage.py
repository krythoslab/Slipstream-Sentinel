import unittest
import tempfile
import sys
import types
from pathlib import Path

# Mock dotenv before importing config_storage
dotenv_mock = types.ModuleType("dotenv")
dotenv_mock.load_dotenv = lambda *args, **kwargs: None
sys.modules["dotenv"] = dotenv_mock

# Mock src.config
config_mock = types.ModuleType("src.config")
config_mock.DATA_DIR = Path(tempfile.gettempdir()) / "slipstream_test"
config_mock.DATA_DIR.mkdir(parents=True, exist_ok=True)
sys.modules["src.config"] = config_mock

from src.modules import config_storage


class TestConfigStorage(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        config_storage.CONFIG_FILE = Path(self.tmpdir.name) / "config.json"

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_get_default(self) -> None:
        self.assertIsNone(config_storage.get("missing_key"))
        self.assertEqual(config_storage.get("missing_key", "default"), "default")

    def test_set_and_get(self) -> None:
        config_storage.set("welcome_channel_id", 12345)
        self.assertEqual(config_storage.get("welcome_channel_id"), 12345)

    def test_get_welcome_channel_id(self) -> None:
        config_storage.set("welcome_channel_id", 999)
        self.assertEqual(config_storage.get_welcome_channel_id(), 999)

    def test_get_welcome_channel_id_default(self) -> None:
        self.assertEqual(config_storage.get_welcome_channel_id(), 0)

    def test_set_modlog_channel_id(self) -> None:
        config_storage.set_modlog_channel_id(555)
        self.assertEqual(config_storage.get_modlog_channel_id(), 555)


if __name__ == "__main__":
    unittest.main()