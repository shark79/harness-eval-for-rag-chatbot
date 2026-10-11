import csv
import io
import json
from pathlib import Path
import tempfile
import unittest

try:
    from agents.evals.evaluation_service import EvaluationService, DecisionsJudge
except ImportError:
    EvaluationService = DecisionsJudge = None

ROOT = Path(__file__).resolve().parents[1]


class EvaluationServiceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(EvaluationService, 'The separate evaluator service must exist')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.service = EvaluationService(ROOT, results_dir=Path(self.tmp.name))

    def test_offline_baseline_never_counts_resolution_or_semantic_pass(self):
        report = self.service.run()
        self.assertEqual(report['case_count'], 26)
        self.assertEqual(report['summary']['semantic_not_run'], 26)
        self.assertEqual(report['summary']['semantic_pass'], 0)
        self.assertIsNone(report['summary']['strict_resolved']['rate'])
        self.assertEqual(report['summary']['strict_resolved']['count'], 0)

    def test_explicit_baseline_failures_are_detected_without_gold_text_matching(self):
        report = self.service.run()
        failed = {c['ticket_id'] for c in report['cases'] if c['deterministic']['status'] == 'fail'}
        self.assertTrue({'TCK-1005','TCK-1006','TCK-1009','TCK-1012','TCK-1015','TCK-1020','TCK-1021','TCK-1023'}.issubset(failed))
        self.assertEqual(report['cases'][0]['semantic']['status'], 'not_run')

    def test_preserves_original_rows_and_three_column_export(self):
        report = self.service.run(limit=2)
        rows = list(csv.DictReader(io.StringIO(Path(report['artifacts']['csv']).read_text())))
        self.assertEqual(list(rows[0]), ['ticket_text','assistant_answer','category'])
        self.assertEqual(rows[0]['ticket_text'], 'Hi, I just published my first chatbot app and I want to call it from my own backend. Where do I get an API key for it? -- Marcus')
        self.assertEqual(self.service.latest()['run_id'], report['run_id'])
        self.assertTrue(report['cases'][0]['evidence'])
        self.assertEqual(report['cases'][0]['citations'][0]['evidence_id'], report['cases'][0]['evidence'][0]['evidence_id'])
        self.assertEqual(json.loads(Path(report['artifacts']['json']).read_text())['case_count'], 2)

    def test_invalid_limits_and_sources_are_rejected(self):
        for limit in (0,27,True,1.2):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                self.service.run(limit=limit)
        with self.assertRaises(ValueError):
            self.service.run(source='unknown')

    def test_negated_team_sso_claim_is_not_prohibited(self):
        case = self.service.cases[5]
        self.assertEqual(self.service.detect_rules(case, 'Team does not provide SSO. SSO is an Enterprise capability.'), [])
        self.assertTrue(self.service.detect_rules(case, 'Team provides SSO to all 40 members.'))

    def test_model_provider_substitution_is_failed_on_app_key_ticket(self):
        failures = self.service.detect_rules(self.service.cases[0], 'Create an OpenAI API key to call your published Dify app.')
        self.assertIn('wrong_key_scope', [f['code'] for f in failures])
        self.assertEqual(self.service.detect_rules(self.service.cases[0], 'Do not create an OpenAI API key for this app. Use the app API Access panel.'), [])

    def test_chatbot_contract_failure_and_runtime_error_cannot_pass(self):
        def broken(text, ticket_id=''):
            if ticket_id == 'TCK-1001':
                return {'ticket_text': text, 'answer': 'Unsupported', 'category': 'api_keys', 'disposition':'answered','citations':[],'evidence':[]}
            raise RuntimeError('secret-provider-message')
        report = self.service.run(source='chatbot', limit=2, chat_fn=broken)
        self.assertEqual(report['summary']['deterministic_fail'], 2)
        self.assertEqual(report['summary']['operational_failures'], 1)
        self.assertNotIn('secret-provider-message', json.dumps(report))

    def test_fabricated_excerpt_or_citation_is_rejected(self):
        candidate = {'ticket_id':'TCK-1001','ticket_text':self.service.cases[0]['ticket_text'],'answer':'Use an app key.','category':'api_keys','disposition':'answered','citations':[{'evidence_id':'madeup','source_id':'product_guide','section_id':'workspace_api_keys'}], 'evidence':[{'evidence_id':'x','source_id':'product_guide','section_id':'workspace_api_keys','source_revision':self.service.manifest[0]['sha256'],'excerpt':'Invented source prose.'}]}
        failures = self.service.validate_candidate(self.service.cases[0], candidate)
        self.assertIn('invalid_evidence', [x['code'] for x in failures])
        self.assertIn('invalid_citation', [x['code'] for x in failures])

    def test_decisions_without_key_does_not_auto_pass(self):
        service = EvaluationService(ROOT, results_dir=Path(self.tmp.name), mode='decisions', api_key='')
        report = service.run(limit=1)
        self.assertEqual(report['cases'][0]['semantic']['status'], 'provider_failure')
        self.assertEqual(report['summary']['semantic_pass'], 0)


class DecisionsJudgeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(DecisionsJudge)

    def valid(self, value=4):
        return {'answers': [{'name':n,'type':'score','score':value} for n in ('grounding','factual_correctness','concern_relevance','completeness','category_accuracy','clarity')] + [{'name':n,'type':'predicate','probability':1.0} for n in ('supported','correct_scope','appropriate_disposition','addresses_requested_concern')]}

    def test_score_levels_are_normalized_not_confidence(self):
        payload=self.valid(3)
        for answer in payload['answers']: answer['confidence']=0.99
        result=DecisionsJudge(api_key='placeholder').parse(payload)
        self.assertEqual(result['dimensions']['grounding'],0.75)
        self.assertEqual(result['status'],'pass')

    def test_missing_refusal_duplicate_wrongtype_invalid_numbers_fail_closed(self):
        judge=DecisionsJudge(api_key='placeholder')
        valid=self.valid()['answers']
        for answers in (valid[:-1],valid+[valid[0]], [{'name':'grounding','type':'refusal'}], [{**a,'score':True} for a in valid], [{**a,'score':float('nan')} for a in valid], [{**a,'type':'choice'} for a in valid]):
            with self.subTest(answers=answers): self.assertEqual(judge.parse({'answers':answers})['status'],'provider_failure')

    def test_one_failed_gate_cannot_be_averaged_away(self):
        payload=self.valid()
        payload['answers'][-3]['probability']=0.1
        result=DecisionsJudge(api_key='placeholder').parse(payload)
        self.assertEqual(result['status'],'fail')
        self.assertFalse(result['gates']['correct_scope'])


class ScoringPolicyTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(EvaluationService)
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)

    def test_boundaries_and_hard_gate(self):
        service=EvaluationService(ROOT, results_dir=Path(self.tmp.name))
        for value, state in ((0.8,'ship'),(0.799,'retry'),(0.7,'retry'),(0.699,'hold_off'),(0.6,'hold_off'),(None,'hold_off')):
            self.assertEqual(service.decide(value, []),state)
        self.assertEqual(service.decide(1.0,[{'code':'wrong_key_scope'}]),'hold_off')

    def test_actual_harness_scores_and_unrun_semantics_stay_distinct(self):
        report=EvaluationService(ROOT,results_dir=Path(self.tmp.name)).run(limit=1)
        self.assertEqual(report['engine']['name'],'harness-evals')
        case=report['cases'][0]
        self.assertIsNone(case['score']); self.assertEqual(case['decision'],'hold_off')
        self.assertTrue(case['harness_scores'])
        self.assertEqual(case['harness_scores'][0]['value'],1.0)
        self.assertFalse(report['release']['eligible'])

    def test_retry_improves_to_ship_and_no_improvement_holds(self):
        class Judge:
            def __init__(self, values): self.values=iter(values)
            def judge(self, case, candidate):
                v=next(self.values)
                return {'status':'pass','gates':{'supported':True,'correct_scope':True,'appropriate_disposition':True,'addresses_requested_concern':True},'dimensions':{n:v for n in ('grounding','factual_correctness','concern_relevance','completeness','category_accuracy','clarity')}}
        service=EvaluationService(ROOT,results_dir=Path(self.tmp.name),judge=Judge([0.75,0.95]))
        def answer(text,ticket_id='',feedback=None):
            evidence=service.baseline_evidence(service.cases[0])
            return {'ticket_id':ticket_id,'ticket_text':text,'answer':'Use the app API Access panel to create an app key.'+(' Store it immediately.' if feedback else ''),'category':'api_keys','disposition':'answered','citations':evidence,'evidence':evidence}
        row=service.run(source='chatbot',limit=1,chat_fn=answer)['cases'][0]
        self.assertEqual(row['decision'],'ship'); self.assertEqual(len(row['attempts']),2)
        service.judge=Judge([0.75,0.75]); row=service.run(source='chatbot',limit=1,chat_fn=answer)['cases'][0]
        self.assertEqual(row['decision'],'hold_off'); self.assertEqual(len(row['attempts']),2)
        self.assertEqual(row['stop_reason'],'no_improvement')

class RetrySafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.service=EvaluationService(ROOT,results_dir=Path(self.tmp.name))

    def candidate(self,text,ticket_id='',feedback=None):
        e=self.service.baseline_evidence(self.service.cases[0])
        return {'ticket_text':text,'ticket_id':ticket_id,'answer':'Create an app key in API Access.'+(' Store it safely.' if feedback else ''), 'category':'api_keys','disposition':'answered','evidence':e,'citations':e}

    def judge(self,values):
        class Judge:
            def __init__(self): self.values=iter(values)
            def judge(self,case,candidate):
                v=next(self.values)
                return {'status':'pass','gates':{n:True for n in ('supported','correct_scope','appropriate_disposition','addresses_requested_concern')},'dimensions':{n:v for n in ('grounding','factual_correctness','concern_relevance','completeness','category_accuracy','clarity')}}
        return Judge()

    def test_one_retry_cap_when_improved_but_still_below_ship(self):
        self.service.judge=self.judge([0.7,0.79,1.0])
        row=self.service.run(source='chatbot',limit=1,chat_fn=self.candidate)['cases'][0]
        self.assertEqual(row['decision'],'hold_off'); self.assertEqual(len(row['attempts']),2)
        self.assertTrue(row['generation_retried']); self.assertFalse(row['scoring_retried'])
        self.assertEqual(row['judge_call_count'],2); self.assertEqual(row['stop_reason'],'one_retry_exhausted')

    def test_unchanged_answer_cannot_ship_by_getting_a_luckier_score(self):
        self.service.judge=self.judge([0.75,0.99])
        def unchanged(text,ticket_id='',feedback=None): return self.candidate(text,ticket_id)
        row=self.service.run(source='chatbot',limit=1,chat_fn=unchanged)['cases'][0]
        self.assertEqual(row['decision'],'hold_off'); self.assertEqual(row['stop_reason'],'unchanged_candidate')

    def test_threshold_uses_unrounded_value(self):
        self.service.judge=self.judge([0.7999996,0.7999997])
        row=self.service.run(source='chatbot',limit=1,chat_fn=self.candidate)['cases'][0]
        self.assertEqual(row['decision'],'hold_off'); self.assertLess(row['score'],0.8)

    def test_interactive_new_ticket_uses_independent_category_score(self):
        self.service.judge=self.judge([0.95])
        candidate=self.candidate('Where do I obtain the key for my published chatbot?')
        result=self.service.evaluate_response(candidate)
        self.assertEqual(result['decision'],'ship'); self.assertFalse(result['delivery_approved'])
        self.assertEqual(result['evaluation']['judge_call_count'],1)

    def test_bearer_claim_requires_transport_evidence(self):
        c=self.service.cases[0]; candidate=self.candidate(c['ticket_text'])
        candidate['answer']='Use the app key as a Bearer token.'
        candidate['evidence']=[e for e in candidate['evidence'] if e['source_id']=='product_guide']
        candidate['citations']=candidate['evidence']
        failures=self.service.validate_candidate(c,candidate)
        self.assertIn('missing_transport_evidence',[f['code'] for f in failures])

    def test_clarification_can_ask_for_error_details_without_runtime_leak_flag(self):
        failures=self.service.detect_rules(self.service.cases[22],'Please add details about the feature and the error you see.')
        self.assertEqual(failures,[])

    def test_malformed_candidate_is_deterministic_failure_not_provider_failure(self):
        candidate=self.candidate(self.service.cases[0]['ticket_text']); candidate['answer']=17
        result=self.service.evaluate_response(candidate)
        self.assertFalse(result['evaluation']['operational_failure'])
        self.assertEqual(result['decision'],'hold_off')


if __name__ == '__main__': unittest.main()
