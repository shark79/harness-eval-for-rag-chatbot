"""HTTP boundary and golden-path integration tests."""
import json
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'backend/app/api/server.py').is_file())
        from backend.app.config.settings import Settings
        from backend.app.api.server import make_server
        self.server = make_server(Settings(root=ROOT), host='127.0.0.1', port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = 'http://127.0.0.1:' + str(self.server.server_port)

    def tearDown(self):
        if hasattr(self, 'server'):
            self.server.shutdown()
            self.server.server_close()
            self.thread.join()

    def test_round_trip_chat_and_health(self):
        with urlopen(self.base + '/api/health') as response:
            self.assertTrue(json.load(response)['corpus_ready'])
        request = Request(self.base + '/api/chat', data=json.dumps({'ticket_text': 'Where do I get a key for my published app?'}).encode(), headers={'Content-Type': 'application/json'})
        with urlopen(request) as response:
            result = json.load(response)
        self.assertEqual(result['category'], 'api_keys')
        self.assertTrue(result['evidence'])
        self.assertEqual(result['evaluation_status'], 'not_run')
        self.assertFalse(result['delivery_approved'])
        self.assertNotIn('decision', result)
        evaluated_request = Request(self.base + '/api/evaluate-response', data=json.dumps({'draft_id': result['draft_id']}).encode(), headers={'Content-Type': 'application/json'})
        with urlopen(evaluated_request) as response:
            evaluated = json.load(response)
        self.assertEqual(evaluated['decision'], 'hold_off')
        self.assertIsNone(evaluated['score'])
        self.assertEqual(evaluated['ticket_text'], result['ticket_text'])
        with urlopen(evaluated_request) as response:
            self.assertEqual(json.load(response), evaluated)

    def test_bad_input_returns_safe_client_error(self):
        request = Request(self.base + '/api/chat', data=b'{"ticket_text":32}', headers={'Content-Type': 'application/json'})
        with self.assertRaises(HTTPError) as raised:
            urlopen(request)
        self.assertEqual(raised.exception.code, 400)
        raised.exception.close()

    def test_request_cannot_read_environment(self):
        with self.assertRaises(HTTPError) as raised:
            urlopen(self.base + '/src/../../.env')
        self.assertEqual(raised.exception.code, 404)
        raised.exception.close()

    def test_cross_origin_mutation_rejected(self):
        request = Request(self.base + '/api/chat', data=b'{}', headers={'Content-Type': 'application/json', 'Origin': 'https://evil.example'})
        with self.assertRaises(HTTPError) as raised:
            urlopen(request)
        self.assertEqual(raised.exception.code, 403)
        raised.exception.close()

    def test_oversized_input_rejected(self):
        request = Request(self.base + '/api/chat', data=b'x' * 32769, headers={'Content-Type': 'application/json'})
        with self.assertRaises(HTTPError) as raised:
            urlopen(request)
        self.assertEqual(raised.exception.code, 413)
        raised.exception.close()

    def test_evaluation_requires_actual_server_generated_draft(self):
        request = Request(self.base + '/api/evaluate-response', data=b'{"draft_id":"invented","answer":"trust me"}', headers={'Content-Type':'application/json'})
        with self.assertRaises(HTTPError) as raised:
            urlopen(request)
        self.assertEqual(raised.exception.code, 400)
        raised.exception.close()

    def test_ticket_selector_never_exposes_baseline_answers(self):
        with urlopen(self.base + '/api/tickets') as response:
            rows = json.load(response)['tickets']
        self.assertEqual(len(rows), 26)
        self.assertTrue(all(set(row) == {'ticket_id','ticket_text','category'} for row in rows))


if __name__ == '__main__':
    unittest.main()
