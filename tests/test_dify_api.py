"""CLI contracts, validated without Dify credentials or paid provider calls."""

from __future__ import annotations

import json
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import dify_api


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dify_api.py"
DATASET = "11111111-1111-4111-8111-111111111111"


def invoke(*arguments: str, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run the CLI entry point with isolated configuration and captured output."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("DIFY_")}
    env.update(environment or {})
    output, errors = io.StringIO(), io.StringIO()
    with patch.dict(os.environ, env, clear=True), redirect_stdout(output), redirect_stderr(errors):
        try:
            code = dify_api.main(arguments)
        except SystemExit as error:
            code = error.code
    return subprocess.CompletedProcess(arguments, code, output.getvalue(), errors.getvalue())


class PreviewTests(unittest.TestCase):
    """Catch wrong endpoints, payload defaults and credential disclosure."""

    def test_workflow_preview_needs_no_credentials(self) -> None:
        result = invoke("--dry-run", "workflow-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        preview = json.loads(result.stdout)
        self.assertEqual(preview["url"], "https://api.dify.ai/v1/workflows/run")
        self.assertEqual(preview["method"], "POST")
        self.assertEqual(preview["body"], {"inputs": {}, "response_mode": "blocking", "user": "preview-user"})

    def test_all_read_endpoints(self) -> None:
        cases = [
            (["info"], "/info"),
            (["parameters"], "/parameters"),
            (["knowledge-list", "--page", "2", "--limit", "10"], "/datasets?page=2&limit=10"),
            (["knowledge-get", DATASET], f"/datasets/{DATASET}"),
            (["knowledge-index-status", DATASET, "20261011120000"], f"/datasets/{DATASET}/documents/20261011120000/indexing-status"),
        ]
        for arguments, suffix in cases:
            with self.subTest(arguments=arguments):
                result = invoke("--dry-run", *arguments)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["url"], "https://api.dify.ai/v1" + suffix)
                self.assertEqual(json.loads(result.stdout)["method"], "GET")

    def test_payload_file_preserves_complex_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            path.write_text(json.dumps({"inputs": {"count": 2, "enabled": True, "docs": [{"type": "document", "transfer_method": "local_file", "upload_file_id": "file-id"}]}, "user": "alice"}), encoding="utf-8")
            result = invoke("--dry-run", "workflow-run", "--payload-file", str(path))
        self.assertEqual(result.returncode, 0, result.stderr)
        body = json.loads(result.stdout)["body"]
        self.assertEqual(body["inputs"]["docs"][0]["upload_file_id"], "file-id")
        self.assertEqual(body["user"], "alice")

    def test_chat_completion_and_retrieve_payloads(self) -> None:
        for command, endpoint in [("chat", "/chat-messages"), ("completion", "/completion-messages")]:
            result = invoke("--dry-run", "--user", "bob", command, "--query", "hello")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["url"], "https://api.dify.ai/v1" + endpoint)
            self.assertEqual(json.loads(result.stdout)["body"]["query"], "hello")
        result = invoke("--dry-run", "knowledge-retrieve", DATASET, "--query", "hello")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["body"], {"query": "hello"})

    def test_document_creation_uses_economy_automatic_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "note.txt"
            path.write_text("a useful note", encoding="utf-8")
            result = invoke("--dry-run", "knowledge-create-text", DATASET, "--name", "note", "--text-file", str(path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["body"], {"name": "note", "text": "a useful note", "indexing_technique": "economy", "process_rule": {"mode": "automatic"}})

    def test_preview_redacts_both_keys_everywhere(self) -> None:
        result = invoke("--dry-run", "chat", "--query", "app-secret knowledge-secret", environment={"DIFY_APP_API_KEY": "app-secret", "DIFY_KNOWLEDGE_API_KEY": "knowledge-secret"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("app-secret", result.stdout + result.stderr)
        self.assertNotIn("knowledge-secret", result.stdout + result.stderr)

    def test_invalid_configuration_is_rejected_without_echoing_values(self) -> None:
        cases = [
            {"DIFY_API_BASE_URL": "https://token:secret@example.com/v1"},
            {"DIFY_API_BASE_URL": "https://example.com/v1?secret=token"},
            {"DIFY_API_BASE_URL": "https://example.com/v1#token"},
            {"DIFY_API_BASE_URL": "http://example.com/v1"},
            {"DIFY_API_BASE_URL": "https://example.com"},
            {"DIFY_API_BASE_URL": "https://example.com:bad/v1"},
            {"DIFY_TIMEOUT": "nan"}, {"DIFY_TIMEOUT": "inf"},
            {"DIFY_TIMEOUT": "0"}, {"DIFY_TIMEOUT": "601"},
            {"DIFY_TIMEOUT": "token"},
        ]
        for config in cases:
            with self.subTest(config=config):
                result = invoke("--dry-run", "info", environment=config)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("token", result.stdout + result.stderr)

    def test_invalid_payloads_do_not_send(self) -> None:
        for payload in ["[]", "invalid-json", '{"inputs": []}', '{"response_mode":"streaming"}', '{"inputs": {"value": NaN}}']:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "payload.json"
                path.write_text(payload, encoding="utf-8")
                result = invoke("--dry-run", "workflow-run", "--payload-file", str(path))
                self.assertEqual(result.returncode, 2)

    def test_missing_required_inputs_and_bad_identifiers(self) -> None:
        for arguments in [["chat"], ["knowledge-retrieve", DATASET], ["knowledge-retrieve", DATASET, "--query", "x" * 251], ["knowledge-create-text", DATASET], ["knowledge-get", "../escape"], ["knowledge-index-status", DATASET, "../escape"], ["knowledge-list", "--limit", "101"], ["knowledge-list", "--page", "0"]]:
            with self.subTest(arguments=arguments):
                self.assertEqual(invoke("--dry-run", *arguments).returncode, 2)

    def test_live_calls_require_the_correct_key(self) -> None:
        result = invoke("info", environment={"DIFY_KNOWLEDGE_API_KEY": "knowledge-secret"})
        self.assertEqual(result.returncode, 2)
        result = invoke("knowledge-list", environment={"DIFY_APP_API_KEY": "app-secret"})
        self.assertEqual(result.returncode, 2)


class LocalApiTests(unittest.TestCase):
    """Use a real local HTTP server to test transport and API result behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.status = 200
        cls.response = b'{}'
        cls.recorded: list[tuple[str, str, str | None, bytes]] = []
        cls.redirect_target: str | None = None
        cls.advertised_length: int | None = None

        class Handler(BaseHTTPRequestHandler):
            def handle_request(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                cls.recorded.append((self.command, self.path, self.headers.get("Authorization"), self.rfile.read(length)))
                self.send_response(cls.status)
                self.send_header("Content-Type", "application/json")
                if cls.redirect_target:
                    self.send_header("Location", cls.redirect_target)
                if cls.advertised_length is not None:
                    self.send_header("Content-Length", str(cls.advertised_length))
                self.end_headers()
                self.wfile.write(cls.response)

            do_GET = handle_request
            do_POST = handle_request

            def log_message(self, format: str, *args: object) -> None:
                pass

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}/v1"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self) -> None:
        type(self).status = 200
        type(self).response = b'{}'
        type(self).redirect_target = None
        type(self).advertised_length = None
        self.recorded.clear()

    def live(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return invoke(*arguments, environment={"DIFY_API_BASE_URL": self.base, "DIFY_APP_API_KEY": "app-secret", "DIFY_KNOWLEDGE_API_KEY": "knowledge-secret", "DIFY_USER": "alice"})

    def test_workflow_round_trip_keeps_json_and_stable_user(self) -> None:
        type(self).response = json.dumps({"workflow_run_id": "run-id", "task_id": "task-id", "data": {"id": "run-id", "workflow_id": "workflow-id", "status": "succeeded", "outputs": {"message": "hello"}, "error": None, "elapsed_time": 0.1, "total_tokens": 12, "total_steps": 2, "created_at": 1, "finished_at": 2}}).encode()
        result = self.live("workflow-run", "--inputs", '{"question":"hello"}')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["data"]["outputs"], {"message": "hello"})
        method, path, authorization, raw = self.recorded[0]
        self.assertEqual((method, path, authorization), ("POST", "/v1/workflows/run", "Bearer app-secret"))
        self.assertEqual(json.loads(raw), {"inputs": {"question": "hello"}, "response_mode": "blocking", "user": "alice"})

    def test_workflow_failed_200_is_failure_and_preserves_json(self) -> None:
        for status in ["failed", "partial-succeeded", "stopped", "paused", "running"]:
            with self.subTest(status=status):
                type(self).response = json.dumps({"data": {"status": status, "error": "provider failed"}}).encode()
                result = self.live("workflow-run")
                self.assertEqual(result.returncode, 3)
                self.assertEqual(json.loads(result.stdout)["data"]["status"], status)

    def test_correct_keys_for_app_and_knowledge_endpoints(self) -> None:
        for arguments, response, key in [
            (["info"], {"name": "example", "mode": "workflow"}, "app-secret"),
            (["parameters"], {"user_input_form": []}, "app-secret"),
            (["knowledge-list"], {"data": [], "page": 1, "limit": 20, "total": 0, "has_more": False}, "knowledge-secret"),
            (["knowledge-get", DATASET], {"id": DATASET, "name": "example"}, "knowledge-secret"),
            (["knowledge-retrieve", DATASET, "--query", "hello"], {"query": {"content": "hello"}, "records": []}, "knowledge-secret"),
            (["knowledge-index-status", DATASET, "batch-1"], {"data": [{"id": "doc-id", "indexing_status": "completed"}]}, "knowledge-secret"),
        ]:
            with self.subTest(arguments=arguments):
                type(self).response = json.dumps(response).encode()
                result = self.live(*arguments)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), response)
                self.assertEqual(self.recorded[-1][2], "Bearer " + key)

    def test_chat_and_completion_blocking_answers(self) -> None:
        for command in ["chat", "completion"]:
            type(self).response = b'{"answer":"hello","conversation_id":"conversation-id"}'
            result = self.live(command, "--query", "question")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["answer"], "hello")

    def test_missing_fields_in_successful_response_are_not_success(self) -> None:
        for arguments in [["workflow-run"], ["chat", "--query", "hello"], ["completion"], ["info"], ["parameters"], ["knowledge-list"], ["knowledge-get", DATASET], ["knowledge-retrieve", DATASET, "--query", "hello"], ["knowledge-index-status", DATASET, "batch"]]:
            with self.subTest(arguments=arguments):
                result = self.live(*arguments)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")

    def test_http_errors_omit_body_and_post_is_never_retried(self) -> None:
        type(self).status = 503
        type(self).response = b'app-secret knowledge-secret private-provider-details'
        result = self.live("workflow-run")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(self.recorded), 1)
        self.assertIn("HTTP 503", result.stderr)
        self.assertNotIn("secret", result.stderr)
        self.assertNotIn("private-provider", result.stderr)

    def test_redirect_target_never_receives_credentials(self) -> None:
        type(self).status = 302
        type(self).redirect_target = self.base + "/leak-target"
        result = self.live("info")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(self.recorded), 1)
        self.assertIn("HTTP 302", result.stderr)

    def test_malformed_json_is_bounded_safe_failure(self) -> None:
        for payload in [b'not-json app-secret', b'[]', b'\xff', b'{"data":NaN}', b'{"name":"example","value":1e999}']:
            with self.subTest(payload=payload):
                type(self).response = payload
                result = self.live("info")
                self.assertEqual(result.returncode, 1)
                self.assertNotIn("app-secret", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_truncated_http_response_is_safe_failure(self) -> None:
        type(self).response = b'{"name":"example"}'
        type(self).advertised_length = 100
        result = self.live("info")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")

    def test_success_output_redacts_credentials_echoed_by_server(self) -> None:
        type(self).response = b'{"name":"app-secret","items":["knowledge-secret"]}'
        result = self.live("info")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("secret", result.stdout)
        self.assertEqual(json.loads(result.stdout)["name"], "[REDACTED]")


class GoldenPathTests(unittest.TestCase):
    """Catch executable/import/argument wiring regressions using subprocesses."""

    def test_actual_cli_dry_run(self) -> None:
        env = {key: value for key, value in os.environ.items() if not key.startswith("DIFY_")}
        result = subprocess.run([sys.executable, str(SCRIPT), "--dry-run", "workflow-run", "--inputs", '{"question":"What does our project do?"}', "--user", "demo-user"], capture_output=True, text=True, env=env, timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["body"]["user"], "demo-user")


if __name__ == "__main__":
    unittest.main()
