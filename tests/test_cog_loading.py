import ast
import unittest
from pathlib import Path


class TestCogLoading(unittest.TestCase):
    COG_FILES = [
        "src/cogs/admin.py",
        "src/cogs/moderation.py",
        "src/cogs/automod.py",
        "src/cogs/welcome.py",
        "src/cogs/info.py",
    ]

    def _has_setup_function(self, filepath: str) -> bool:
        source = Path(filepath).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "setup":
                return True
        return False

    def test_admin_has_setup(self) -> None:
        self.assertTrue(self._has_setup_function("src/cogs/admin.py"))

    def test_moderation_has_setup(self) -> None:
        self.assertTrue(self._has_setup_function("src/cogs/moderation.py"))

    def test_automod_has_setup(self) -> None:
        self.assertTrue(self._has_setup_function("src/cogs/automod.py"))

    def test_welcome_has_setup(self) -> None:
        self.assertTrue(self._has_setup_function("src/cogs/welcome.py"))

    def test_info_has_setup(self) -> None:
        self.assertTrue(self._has_setup_function("src/cogs/info.py"))


if __name__ == "__main__":
    unittest.main()