"""Real retrieval/evaluator composition with controlled judge results; no paid calls."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from agents.evals.evaluation_service import EvaluationService, GATES, WEIGHTS
from backend.app.api.server import make_server
from backend.app.config.settings import Settings
from backend.app.services.chat import ChatService

ROOT = Path(__file__).resolve().parents[2]


class ReleaseWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.chat = ChatService(Settings(root=ROOT))

    def run_case(self, scores, gate=True, unchanged=False, retry_available=True):
        class Judge:
            def __init__(self):
                self.values = iter(scores)
                self.calls = 0

            def judge(self, case, candidate):
                self.calls += 1
                value = next(self.values)
                return {'status': 'pass' if gate else 'fail', 'dimensions': {n: value for n in WEIGHTS},
                        'gates': {n: gate for n in GATES}}

        judge = Judge()
        service = EvaluationService(ROOT, results_dir=Path(self.tmp.name), judge=judge)
        calls = []

        def generate(text, ticket_id='', feedback=None):
            calls.append(feedback)
            candidate = self.chat.answer(text, ticket_id=ticket_id)
            if feedback and not unchanged:
                candidate['answer'] = candidate['answer'].replace('From the approved documentation:', 'Approved documentation says:')
            return candidate

        def initial_only(text, ticket_id=''):
            return generate(text, ticket_id)

        row = service.run(source='chatbot', limit=1, chat_fn=generate if retry_available else initial_only)['cases'][0]
        return row, calls, judge.calls

    def test_only_borderline_scores_get_one_generation_retry(self):
        for first, later, expected, count in ((0.69, 1.0, 'hold_off', 1),
                                              (0.70, 0.90, 'ship', 2),
                                              (0.79, 0.90, 'ship', 2),
                                              (0.80, 0.90, 'ship', 1)):
            with self.subTest(first=first):
                row, calls, judgments = self.run_case([first, later])
                self.assertEqual(row['decision'], expected)
                self.assertEqual(len(calls), count)
                self.assertEqual(judgments, count)
                self.assertEqual(row['generation_retried'], count == 2)
                self.assertFalse(row['scoring_retried'])
                self.assertFalse(row['delivery_approved'])
                if count == 2:
                    self.assertIn('Re-anchor', calls[1])

    def test_improvement_below_threshold_stops_after_one_retry(self):
        row, calls, _ = self.run_case([0.71, 0.79, 1.0])
        self.assertEqual(row['decision'], 'hold_off')
        self.assertEqual(len(calls), 2)
        self.assertEqual(row['stop_reason'], 'one_retry_exhausted')
        self.assertEqual(row['attempts'][-1]['decision'], 'hold_off')

    def test_no_improvement_or_unchanged_answer_cannot_ship(self):
        for scores, unchanged, stop in (([0.75, 0.75], False, 'no_improvement'),
                                        ([0.75, 0.90], True, 'unchanged_candidate')):
            with self.subTest(unchanged=unchanged):
                row, calls, _ = self.run_case(scores, unchanged=unchanged)
                self.assertEqual(row['decision'], 'hold_off')
                self.assertEqual(row['stop_reason'], stop)
                self.assertEqual(len(calls), 2)
                self.assertEqual(row['attempts'][-1]['decision'], 'hold_off')

    def test_unavailable_retry_reports_final_hold_in_attempt(self):
        row, calls, _ = self.run_case([0.75], retry_available=False)
        self.assertEqual(row['decision'], 'hold_off')
        self.assertEqual(row['stop_reason'], 'retry_unavailable')
        self.assertEqual(len(calls), 1)
        self.assertEqual(row['attempts'][-1]['decision'], 'hold_off')

    def test_expired_retry_budget_reports_final_hold_in_attempt(self):
        with patch('agents.evals.evaluation_service.time.monotonic', side_effect=[0, 1000]):
            row, calls, _ = self.run_case([0.75])
        self.assertEqual(row['decision'], 'hold_off')
        self.assertEqual(row['stop_reason'], 'time_budget')
        self.assertEqual(len(calls), 1)
        self.assertEqual(row['attempts'][-1]['decision'], 'hold_off')

    def test_failed_mandatory_gate_blocks_high_score_without_retry(self):
        row, calls, _ = self.run_case([1.0, 1.0], gate=False)
        self.assertEqual(row['decision'], 'hold_off')
        self.assertEqual(len(calls), 1)
        self.assertTrue(row['failures'])

    def test_malformed_semantic_number_is_held_without_retry(self):
        row, calls, _ = self.run_case([float('nan')])
        self.assertIsNone(row['score'])
        self.assertEqual(row['semantic']['status'], 'provider_failure')
        self.assertEqual(row['decision'], 'hold_off')
        self.assertEqual(len(calls), 1)


class HttpTrustBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.secret = 'synthetic-secret-never-send'
        cls.server = make_server(Settings(root=ROOT, dify_api_key=cls.secret, openai_api_key=cls.secret), host='127.0.0.1', port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = 'http://127.0.0.1:' + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_unhashable_evaluation_sources_return_json_client_error(self):
        for source in ([], {}, ['baseline']):
            with self.subTest(source=source):
                req = Request(self.base + '/api/evaluations', data=json.dumps({'source': source}).encode(), headers={'Content-Type': 'application/json'})
                with self.assertRaises(HTTPError) as caught:
                    urlopen(req)
                self.assertEqual(caught.exception.code, 400)
                self.assertIn('error', json.load(caught.exception))
                caught.exception.close()

    def test_local_round_trip_holds_unjudged_answer_and_omits_credentials(self):
        for path in ('/api/health', '/'):
            with urlopen(self.base + path) as response:
                self.assertNotIn(self.secret, response.read().decode())
        req = Request(self.base + '/api/chat', data=b'{"ticket_text":"Where is the key for my published app?"}', headers={'Content-Type': 'application/json'})
        with urlopen(req) as response:
            body = response.read().decode()
        self.assertNotIn(self.secret, body)
        result = json.loads(body)
        self.assertEqual(result['evaluation_status'], 'not_run')
        self.assertNotIn('score', result)
        self.assertTrue(result['evidence'])
        request_body = {'draft_id': result['draft_id'], 'answer': 'Forged answer', 'score': 1.0}
        evaluate = Request(self.base + '/api/evaluate-response', data=json.dumps(request_body).encode(), headers={'Content-Type': 'application/json'})
        with urlopen(evaluate) as response:
            result = json.load(response)
        with urlopen(evaluate) as response:
            self.assertEqual(json.load(response), result)
        self.assertNotEqual(result['answer'], 'Forged answer')
        self.assertNotIn(self.secret, json.dumps(result))
        self.assertEqual(result['decision'], 'hold_off')
        self.assertIsNone(result['score'])
        self.assertEqual(result['evaluation']['judge_call_count'], 0)

    def test_encoded_traversal_cannot_read_private_files(self):
        for path in ('/src/%2e%2e/%2e%2e/.env', '/src/%2Fetc/passwd', '/src/../.env'):
            with self.subTest(path=path), self.assertRaises(HTTPError) as caught:
                urlopen(self.base + path)
            self.assertEqual(caught.exception.code, 404)
            caught.exception.close()
