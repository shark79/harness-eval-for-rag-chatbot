#!/usr/bin/env python3
"""Call the published Dify Service API using Python 3.11+ standard library.

Configuration comes only from explicit flags and environment variables. This
command does not load .env files, retry POST requests or follow redirects.
See --help and each subcommand's --help for the public interface.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from http.client import HTTPException
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID


MAX_BYTES = 8 * 1024 * 1024
JsonObject = dict[str, Any]


class DifyError(Exception):
    """Carry a safe message and documented process exit code."""

    def __init__(self, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass(frozen=True)
class Call:
    """A validated Service API request, excluding authentication."""

    method: str
    path: str
    body: JsonObject | None
    key_variable: str


def parser() -> argparse.ArgumentParser:
    """Build the CLI interface without reading configuration or credentials."""
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--base-url", help="Service API URL ending /v1; DIFY_API_BASE_URL")
    result.add_argument("--timeout", help="Seconds, greater than 0 and at most 600; DIFY_TIMEOUT (default 100)")
    result.add_argument("--user", help="Stable end-user identity; DIFY_USER")
    result.add_argument("--dry-run", action="store_true", help="Preview without credentials or network requests")
    result.add_argument("--allow-insecure-http", action="store_true", help="Explicitly permit remote HTTP; localhost HTTP is already permitted")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("info", help="Get app information")
    commands.add_parser("parameters", help="Get app input variables and features")
    for name in ("workflow-run", "chat", "completion"):
        command = commands.add_parser(name, help="Execute a published app in blocking mode")
        command.add_argument("--payload-file", help="Complete JSON request body; flags override matching fields")
        command.add_argument("--inputs", help="App inputs as a JSON object")
        command.add_argument("--user", default=argparse.SUPPRESS, help="Stable end-user identity; DIFY_USER")
        if name != "workflow-run":
            command.add_argument("--query", help="Chat message or legacy completion query")
        if name == "chat":
            command.add_argument("--conversation-id", help="Continue the conversation returned by a prior chat call")
    listing = commands.add_parser("knowledge-list", help="List knowledge bases (one page)")
    listing.add_argument("--page", type=int, default=1)
    listing.add_argument("--limit", type=int, default=20)
    for name in ("knowledge-get", "knowledge-create-text", "knowledge-index-status", "knowledge-retrieve"):
        command = commands.add_parser(name)
        command.add_argument("dataset_id", help="Knowledge base UUID")
        if name == "knowledge-index-status":
            command.add_argument("batch", help="Batch ID returned by document creation")
        if name in ("knowledge-create-text", "knowledge-retrieve"):
            command.add_argument("--payload-file", help="Complete JSON request body; flags override matching fields")
        if name == "knowledge-create-text":
            command.add_argument("--name", help="Document name")
            command.add_argument("--text-file", help="UTF-8 file containing document text")
            command.add_argument("--indexing-technique", choices=("economy", "high_quality"), help="Default economy (keyword index); existing base settings must match")
        if name == "knowledge-retrieve":
            command.add_argument("--query", help="Retrieval query, at most 250 characters")
    return result


def json_object(text: str) -> JsonObject:
    """Decode a strict JSON object with no non-finite number extensions."""
    try:
        value = json.loads(text, parse_float=finite_float, parse_constant=finite_float)
    except (ValueError, RecursionError):
        raise DifyError("Expected valid JSON without non-finite numbers.") from None
    if not isinstance(value, dict):
        raise DifyError("Expected a JSON object.")
    return value


def finite_float(text: str) -> float:
    """Reject JSON number overflow and non-standard NaN/Infinity constants."""
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("Non-finite number")
    return value


def read_text(path: str) -> str:
    """Read bounded UTF-8 data without disclosing the filename on errors."""
    try:
        with Path(path).open("rb") as source:
            data = source.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise DifyError("Input file exceeds the 8 MiB limit.")
        return data.decode("utf-8")
    except (OSError, UnicodeError):
        raise DifyError("Cannot read input file as UTF-8.") from None


def nonempty(value: Any, label: str, limit: int = MAX_BYTES) -> str:
    """Validate required strings using safe static field labels."""
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise DifyError(f"{label} must be a nonempty string within its size limit.")
    return value


def make_call(args: argparse.Namespace, env: Mapping[str, str]) -> Call:
    """Validate command input and produce a request to a fixed API endpoint."""
    name = args.command
    key = "DIFY_KNOWLEDGE_API_KEY" if name.startswith("knowledge-") else "DIFY_APP_API_KEY"
    if name in ("info", "parameters"):
        return Call("GET", "/" + name, None, key)
    if name == "knowledge-list":
        if not 1 <= args.page <= 1_000_000 or not 1 <= args.limit <= 100:
            raise DifyError("Page must be 1..1000000; limit must be 1..100.")
        return Call("GET", "/datasets?" + urlencode({"page": args.page, "limit": args.limit}), None, key)
    prefix = ""
    if name.startswith("knowledge-"):
        try:
            dataset_id = str(UUID(args.dataset_id))
        except ValueError:
            raise DifyError("dataset_id must be a UUID.") from None
        prefix = f"/datasets/{dataset_id}"
        if name == "knowledge-get":
            return Call("GET", prefix, None, key)
        if name == "knowledge-index-status":
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", args.batch):
                raise DifyError("Batch ID must contain 1..128 letters, digits, underscores or hyphens.")
            return Call("GET", prefix + f"/documents/{args.batch}/indexing-status", None, key)
    body = json_object(read_text(args.payload_file)) if args.payload_file else {}
    if name in ("workflow-run", "chat", "completion"):
        if args.inputs is not None:
            body["inputs"] = json_object(args.inputs)
        body.setdefault("inputs", {})
        if not isinstance(body["inputs"], dict):
            raise DifyError("inputs must be a JSON object.")
        if body.get("response_mode", "blocking") != "blocking":
            raise DifyError("This CLI supports response_mode blocking only.")
        body["response_mode"] = "blocking"
        user = args.user or body.get("user") or env.get("DIFY_USER")
        if user is None and args.dry_run:
            user = "preview-user"
        body["user"] = nonempty(user, "user", 256)
        if name != "workflow-run" and args.query is not None:
            body["query"] = args.query
        if name == "chat":
            body["query"] = nonempty(body.get("query"), "query")
            if args.conversation_id is not None:
                body["conversation_id"] = args.conversation_id
            if "conversation_id" in body and not isinstance(body["conversation_id"], str):
                raise DifyError("conversation_id must be a string.")
        if name == "completion" and "query" in body and not isinstance(body["query"], str):
            raise DifyError("query must be a string.")
        endpoint = {"workflow-run": "/workflows/run", "chat": "/chat-messages", "completion": "/completion-messages"}[name]
    elif name == "knowledge-create-text":
        if args.name is not None:
            body["name"] = args.name
        if args.text_file is not None:
            body["text"] = read_text(args.text_file)
        body["name"] = nonempty(body.get("name"), "name", 1024)
        body["text"] = nonempty(body.get("text"), "text")
        body["indexing_technique"] = args.indexing_technique or body.get("indexing_technique", "economy")
        if body["indexing_technique"] not in ("economy", "high_quality"):
            raise DifyError("indexing_technique must be economy or high_quality.")
        body.setdefault("process_rule", {"mode": "automatic"})
        rule = body["process_rule"]
        if not isinstance(rule, dict) or rule.get("mode") not in ("automatic", "custom", "hierarchical"):
            raise DifyError("process_rule must be an object with a supported mode.")
        endpoint = prefix + "/document/create-by-text"
    else:
        if args.query is not None:
            body["query"] = args.query
        body["query"] = nonempty(body.get("query"), "query", 250)
        endpoint = prefix + "/retrieve"
    try:
        encoded = json.dumps(body, allow_nan=False).encode("utf-8")
    except (ValueError, RecursionError):
        raise DifyError("Payload is not valid finite JSON.") from None
    if len(encoded) > MAX_BYTES:
        raise DifyError("Request body exceeds the 8 MiB limit.")
    return Call("POST", endpoint, body, key)


def configuration(args: argparse.Namespace, env: Mapping[str, str]) -> tuple[str, float]:
    """Resolve a bounded timeout and validated base URL without exposing secrets."""
    base = args.base_url or env.get("DIFY_API_BASE_URL", "https://api.dify.ai/v1")
    if len(base) > 2048 or any(character.isspace() for character in base):
        raise DifyError("Invalid Service API base URL.")
    try:
        parts = urlsplit(base)
        port = parts.port
    except ValueError:
        raise DifyError("Invalid Service API base URL.") from None
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username is not None or parts.password is not None or parts.query or parts.fragment or not parts.path.rstrip("/").endswith("/v1") or (port is not None and port == 0):
        raise DifyError("Base URL must be HTTP(S), end in /v1, and exclude credentials, query and fragment.")
    if parts.scheme == "http" and parts.hostname not in ("localhost", "127.0.0.1", "::1") and not args.allow_insecure_http:
        raise DifyError("Remote HTTP requires --allow-insecure-http; prefer HTTPS.")
    try:
        timeout = float(args.timeout or env.get("DIFY_TIMEOUT", "100"))
    except ValueError:
        raise DifyError("Timeout must be numeric, greater than 0 and at most 600 seconds.") from None
    if not math.isfinite(timeout) or not 0 < timeout <= 600:
        raise DifyError("Timeout must be numeric, greater than 0 and at most 600 seconds.")
    return base.rstrip("/"), timeout


def redact(value: Any, secrets: Sequence[str]) -> Any:
    """Remove known credentials from output, including echoed payload values."""
    if isinstance(value, str):
        for secret in secrets:
            value = value.replace(secret, "[REDACTED]")
        return value
    if isinstance(value, list):
        return [redact(item, secrets) for item in value]
    if isinstance(value, dict):
        return {redact(key, secrets): redact(item, secrets) for key, item in value.items()}
    return value


class NoRedirect(HTTPRedirectHandler):
    """Prevent Authorization headers from reaching a redirect target."""

    def redirect_request(self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def request(call: Call, base: str, timeout: float, token: str) -> JsonObject:
    """Send a single bounded request; report only safe HTTP/network errors."""
    data = json.dumps(call.body, allow_nan=False).encode("utf-8") if call.body is not None else None
    req = Request(base + call.path, data=data, method=call.method, headers={"Authorization": "Bearer " + token, "Accept": "application/json", "Content-Type": "application/json"})
    try:
        with build_opener(NoRedirect()).open(req, timeout=timeout) as response:
            length = response.headers.get("Content-Length")
            expected = None
            if length is not None:
                if not length.isdecimal() or len(length) > 10:
                    raise DifyError("Dify returned an invalid response length.", 1)
                expected = int(length)
                if expected > MAX_BYTES:
                    raise DifyError("Dify response exceeds the 8 MiB limit.", 1)
            raw = response.read(MAX_BYTES + 1)
            if expected is not None and len(raw) != expected:
                raise DifyError("Dify returned an incomplete response.", 1)
    except HTTPError as error:
        status = error.code
        error.close()
        raise DifyError(f"Dify returned HTTP {status}; response body omitted.", 1) from None
    except (URLError, OSError, ValueError, HTTPException):
        raise DifyError("Dify request failed or timed out; check connection and configuration.", 1) from None
    if len(raw) > MAX_BYTES:
        raise DifyError("Dify response exceeds the 8 MiB limit.", 1)
    try:
        return json_object(raw.decode("utf-8"))
    except (DifyError, UnicodeError):
        raise DifyError("Dify returned malformed JSON; response body omitted.", 1) from None


def response_status(command: str, value: JsonObject) -> int:
    """Distinguish workflow execution failures from successful HTTP transport."""
    if command == "workflow-run":
        data = value.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("status"), str):
            raise DifyError("Dify workflow response lacks data.status.", 1)
        return 0 if data["status"] == "succeeded" else 3
    if command in ("chat", "completion") and not isinstance(value.get("answer"), str):
        raise DifyError("Dify message response lacks an answer string.", 1)
    required = {
        "info": ("name", str),
        "parameters": ("user_input_form", list),
        "knowledge-list": ("data", list),
        "knowledge-get": ("id", str),
        "knowledge-create-text": ("document", dict),
        "knowledge-index-status": ("data", list),
        "knowledge-retrieve": ("records", list),
    }
    if command in required:
        field, field_type = required[command]
        if not isinstance(value.get(field), field_type):
            raise DifyError("Dify response lacks the expected result field.", 1)
    if command == "knowledge-create-text" and not isinstance(value.get("batch"), str):
        raise DifyError("Dify document response lacks its indexing batch.", 1)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the CLI and return 0 success, 1 transport, 2 input, or 3 workflow failure."""
    args = parser().parse_args(argv)
    env = os.environ
    secrets = sorted({env[key] for key in ("DIFY_APP_API_KEY", "DIFY_KNOWLEDGE_API_KEY") if env.get(key)}, key=len, reverse=True)
    try:
        base, timeout = configuration(args, env)
        call = make_call(args, env)
        if args.dry_run:
            value: JsonObject = {"method": call.method, "url": base + call.path, "body": call.body, "credential_env": call.key_variable, "timeout": timeout}
            exit_code = 0
        else:
            token = nonempty(env.get(call.key_variable), call.key_variable, 4096)
            if any(character.isspace() for character in token):
                raise DifyError("API key must not contain whitespace.")
            value = request(call, base, timeout, token)
            exit_code = response_status(args.command, value)
        print(json.dumps(redact(value, secrets), indent=2, ensure_ascii=False, allow_nan=False))
        if exit_code == 3:
            print("Workflow did not succeed; inspect data.status in the JSON result.", file=sys.stderr)
        return exit_code
    except DifyError as error:
        print(f"Error: {error}", file=sys.stderr)
        return error.exit_code


if __name__ == "__main__":
    sys.exit(main())
