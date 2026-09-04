import ast
import os
import unittest
from pathlib import Path

SOURCE_FILE = Path(__file__).resolve().parent.parent / "src" / "config.py"


class TestDataDirResolution(unittest.TestCase):
    def test_has_resolve_function(self) -> None:
        source = SOURCE_FILE.read_text(encoding="utf-8")
        self.assertIn("def _resolve_data_dir", source)

    def test_env_var_takes_precedence(self) -> None:
        source = SOURCE_FILE.read_text(encoding="utf-8")
        self.assertIn('os.getenv("DATA_DIR")', source)
        self.assertIn("return Path(env_dir)", source)

    def test_fallback_to_tmp_when_not_writable(self) -> None:
        source = SOURCE_FILE.read_text(encoding="utf-8")
        self.assertIn("/tmp/slipstream-sentinel", source)

    def test_uses_project_data_dir_by_default(self) -> None:
        source = SOURCE_FILE.read_text(encoding="utf-8")
        self.assertIn("PROJECT_ROOT / \"data\"", source)

    def test_does_write_test_to_check_writability(self) -> None:
        source = SOURCE_FILE.read_text(encoding="utf-8")
        self.assertIn(".write_test", source)


if __name__ == "__main__":
    unittest.main()
