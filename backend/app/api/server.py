"""Local ticket-chat HTTP transport and static UI server."""
import csv
import json
import uuid
from collections import OrderedDict
import mimetypes
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from typing import Any
from urllib.parse import unquote, urlsplit
from backend.app.config.settings import Settings
from backend.app.integrations.providers import ProviderError
from backend.app.services.chat import ChatService


def make_server(settings: Settings, host: str | None = None, port: int | None = None) -> ThreadingHTTPServer:
    """Create the transport with one corpus and a serialized evaluation runner."""
    chat = ChatService(settings)
    evaluation_lock = Lock()
    evaluator: Any = None
    drafts: OrderedDict[str, dict[str, Any]] = OrderedDict()
    draft_lock = Lock()

    def evaluation_service() -> Any:
        nonlocal evaluator
        if evaluator is None:
            from agents.evals.evaluation_service import EvaluationService
            evaluator = EvaluationService(settings.root, mode=settings.eval_mode, api_key=settings.openai_api_key)
        return evaluator

    class Handler(BaseHTTPRequestHandler):
        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(120)

        def log_message(self, format: str, *args: Any) -> None:
            # Tickets, keys and upstream response bodies never enter HTTP logs.
            return

        def send_json(self, status: int, value: Any) -> None:
            body = json.dumps(value, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path == '/api/health':
                self.send_json(200, {**chat.health(), 'eval_mode': settings.eval_mode})
                return
            if path == '/api/tickets':
                with (settings.root / 'evals/datasets/support-tickets.csv').open(newline='') as source:
                    tickets = [{'ticket_id': row['id'], 'ticket_text': row['ticket_text'], 'category': row['category']} for row in csv.DictReader(source)]
                self.send_json(200, {'tickets': tickets})
                return
            if path == '/api/evaluations/latest':
                try:
                    self.send_json(200, evaluation_service().latest())
                except (ImportError, RuntimeError, OSError, ValueError):
                    self.send_json(503, {'error': 'Evaluation runner is unavailable; inspect local configuration.'})
                return
            static_root = (settings.root / 'frontend/src').resolve()
            relative = 'app/index.html' if path == '/' else unquote(path.removeprefix('/src/'))
            candidate = (static_root / relative).resolve()
            if (path != '/' and not path.startswith('/src/')) or not candidate.is_relative_to(static_root) or not candidate.is_file():
                self.send_json(404, {'error': 'Not found.'})
                return
            body = candidate.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', mimetypes.guess_type(str(candidate))[0] or 'application/octet-stream')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            if self.path not in {'/api/chat', '/api/evaluations', '/api/evaluate-response'}:
                self.send_json(404, {'error': 'Not found.'})
                return
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + self.headers.get('Host', ''):
                self.send_json(403, {'error': 'Cross-origin requests are disabled.'})
                return
            if self.headers.get_content_type() != 'application/json':
                self.send_json(415, {'error': 'Content-Type must be application/json.'})
                return
            try:
                length_text = self.headers.get('Content-Length', '')
                if not length_text.isdecimal() or len(length_text) > 8 or self.headers.get('Transfer-Encoding'):
                    raise ValueError('A valid Content-Length is required.')
                length = int(length_text)
                if length > 32768:
                    self.send_json(413, {'error': 'Request exceeds 32 KiB.'})
                    return
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError('JSON body must be an object.')
                if self.path == '/api/chat':
                    draft_id = uuid.uuid4().hex
                    candidate = chat.answer(payload.get('ticket_text'), payload.get('ticket_id', ''))
                    candidate['ticket_id'] = candidate['ticket_id'] or 'generated-' + draft_id[:8]
                    result = {**candidate, 'draft_id': draft_id, 'evaluation_status': 'not_run', 'delivery_approved': False}
                    with draft_lock:
                        drafts[draft_id] = {'candidate': candidate, 'evaluation': None}
                        if len(drafts) > 64:
                            drafts.popitem(last=False)
                elif self.path == '/api/evaluate-response':
                    draft_id = payload.get('draft_id')
                    if not isinstance(draft_id, str) or len(draft_id) > 64:
                        raise ValueError('draft_id must identify a generated server draft.')
                    with draft_lock:
                        record = drafts.get(draft_id)
                    if record is None:
                        raise ValueError('Draft is unknown or expired; generate a new response first.')
                    if record['evaluation'] is not None:
                        self.send_json(200, record['evaluation'])
                        return
                    if not evaluation_lock.acquire(blocking=False):
                        self.send_json(409, {'error': 'An evaluation is already running.'})
                        return
                    try:
                        # Recheck under the execution lock so concurrent requests cannot rescore.
                        if record['evaluation'] is None:
                            evaluated = evaluation_service().evaluate_response(record['candidate'], chat_fn=chat.answer)
                            record['evaluation'] = {**evaluated, 'draft_id': draft_id, 'evaluation_status': 'completed'}
                        result = record['evaluation']
                    finally:
                        evaluation_lock.release()
                else:
                    source = payload.get('source', 'baseline')
                    limit = payload.get('limit', 26)
                    if not isinstance(source, str) or source not in {'baseline', 'chatbot'} or type(limit) is not int or not 1 <= limit <= 26:
                        raise ValueError('Evaluation source must be baseline or chatbot; limit must be 1 to 26.')
                    if not evaluation_lock.acquire(blocking=False):
                        self.send_json(409, {'error': 'An evaluation is already running.'})
                        return
                    try:
                        result = evaluation_service().run(source=source, limit=limit, chat_fn=chat.answer)
                    finally:
                        evaluation_lock.release()
                self.send_json(200, result)
            except (ValueError, UnicodeError) as error:
                self.send_json(400, {'error': str(error) if not isinstance(error, json.JSONDecodeError) else 'Invalid JSON body.'})
            except ProviderError as error:
                self.send_json(502, {'error': str(error)})
            except (ImportError, RuntimeError, OSError):
                self.send_json(503, {'error': 'Runner unavailable; check local configuration and provider credentials.'})

    return ThreadingHTTPServer((settings.host if host is None else host, settings.port if port is None else port), Handler)


def main() -> None:
    settings = Settings.load(Path(__file__).resolve().parents[3])
    server = make_server(settings)
    print(f'Ticket assistant listening on port {settings.port}; mode={settings.mode}, eval={settings.eval_mode}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
