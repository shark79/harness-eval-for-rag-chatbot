"""Configuration accepts local Dify without sending credentials to unsafe URLs."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.app.config.settings import Settings


class SettingsTests(unittest.TestCase):
    def test_default_endpoint_targets_local_dify(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {}, clear=True):
            settings = Settings.load(Path(directory))
            self.assertEqual(settings.dify_base_url, "http://localhost/v1")
            self.assertEqual(Settings(root=Path(directory)).dify_base_url, "http://localhost/v1")

    def test_local_endpoints_and_https_can_be_loaded_from_env(self) -> None:
        for base in ["http://localhost/v1", "http://127.0.0.1:8081/v1/", "http://host.docker.internal:8081/v1", "https://api.dify.ai/v1", "https://dify.example.com/v1", "https://example.com/dify/v1"]:
            with self.subTest(base=base), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / ".env").write_text("DIFY_API_BASE_URL=" + base + "\n")
                with patch.dict("os.environ", {}, clear=True):
                    self.assertEqual(Settings.load(root).dify_base_url, base.rstrip("/"))

    def test_process_endpoint_overrides_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text("DIFY_API_BASE_URL=https://api.dify.ai/v1\n")
            with patch.dict("os.environ", {"DIFY_API_BASE_URL": "http://host.docker.internal/v1"}, clear=True):
                self.assertEqual(Settings.load(root).dify_base_url, "http://host.docker.internal/v1")

    def test_unsafe_endpoint_is_rejected_without_echoing_secret(self) -> None:
        for base in ["http://example.com/v1", "http://localhost.evil/v1", "http://host.docker.internal.evil/v1", "https://user:private-secret@example.com/v1", "http://localhost/v1?private-secret", "http://localhost/v1#private-secret", "http://localhost/console", "http://localhost:bad/v1", "http://localhost:0/v1", "http://localhost/v1//"]:
            with self.subTest(base=base), tempfile.TemporaryDirectory() as directory:
                with patch.dict("os.environ", {"DIFY_API_BASE_URL": base}, clear=True):
                    with self.assertRaises(ValueError) as caught:
                        Settings.load(Path(directory))
                self.assertNotIn("private-secret", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
