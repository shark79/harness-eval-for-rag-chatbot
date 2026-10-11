"""Standalone Code nodes preserve retrieval provenance and resolve supplied IDs."""
import json
from pathlib import Path
import unittest

from backend.app.services.retrieval import CorpusRetriever


ROOT = Path(__file__).resolve().parents[1]
GUIDE_NAME = 'Constructed fictional product documentation for the RAG knowledge base.md'


class WorkflowNodeTests(unittest.TestCase):
    def setUp(self):
        from agents.tools.dify_normalize_evidence import main as normalize
        from agents.tools.dify_resolve_citations import main as resolve
        self.normalize, self.resolve = normalize, resolve
        self.source = next(e for e in CorpusRetriever(ROOT).chunks if e.excerpt.startswith('- **App API keys**'))
        self.app_excerpt = self.source.excerpt.split('\n- **Dataset')[0]
        self.chunk = {'content': self.app_excerpt, 'title': GUIDE_NAME, 'metadata': {'document_name': GUIDE_NAME}}

    def test_partial_retrieved_bullet_retains_exact_text_and_authoritative_revision(self):
        result = self.normalize([self.chunk])
        self.assertEqual(len(result['evidence']), 1)
        evidence = result['evidence'][0]
        self.assertEqual(evidence['excerpt'], self.app_excerpt)
        self.assertNotIn('Dataset (knowledge base)', evidence['excerpt'])
        self.assertEqual(evidence['source_revision'], self.source.source_revision)
        self.assertEqual(evidence['section_id'], 'workspace_api_keys')
        self.assertEqual(json.loads(result['context']), result['evidence'])

    def test_unapproved_document_or_unsupported_content_is_skipped(self):
        unknown = dict(self.chunk, title='tickets.csv', metadata={'document_name': 'tickets.csv'})
        invented = dict(self.chunk, content='Generate an OpenAI API key to call your app.')
        self.assertEqual(self.normalize([unknown, invented])['evidence'], [])

    def test_contradictory_document_names_are_skipped(self):
        self.assertEqual(self.normalize([dict(self.chunk, title='other.md')])['evidence'], [])

    def test_duplicates_collapse_and_distinct_substrings_have_distinct_ids(self):
        second = dict(self.chunk, content=self.source.excerpt.split('\n')[1])
        evidence = self.normalize([self.chunk, self.chunk, second])['evidence']
        self.assertEqual(len(evidence), 2)
        self.assertEqual(len({e['evidence_id'] for e in evidence}), 2)

    def test_answer_citations_resolve_only_supplied_evidence_ids(self):
        evidence = self.normalize([self.chunk])['evidence']
        draft = {'answer': 'Create the key from the app API Access panel.', 'category': 'api_keys',
                 'disposition': 'answered', 'cited_evidence_ids': [evidence[0]['evidence_id']]}
        output = self.resolve(draft, evidence)
        self.assertEqual(output['answer'], draft['answer'])
        self.assertEqual(output['evidence'], evidence)
        self.assertEqual(output['citations'], [{k: evidence[0][k] for k in ('evidence_id', 'source_id', 'section_id')}])

    def test_unknown_citations_and_uncited_answers_fail_closed(self):
        evidence = self.normalize([self.chunk])['evidence']
        draft = {'answer': 'Answer', 'category': 'api_keys', 'disposition': 'answered', 'cited_evidence_ids': []}
        for ids in ([], ['invented']):
            with self.assertRaises(ValueError):
                self.resolve(dict(draft, cited_evidence_ids=ids), evidence)

    def test_clarification_can_return_without_evidence_but_invalid_enums_cannot(self):
        draft = {'answer': 'Which kind of key do you need?', 'category': 'unknown',
                 'disposition': 'needs_clarification', 'cited_evidence_ids': []}
        self.assertEqual(self.resolve(draft, [])['citations'], [])
        for changed in ({'category': 'made_up'}, {'disposition': 'ship'}, {'answer': ''}):
            with self.assertRaises(ValueError):
                self.resolve(dict(draft, **changed), [])

    def test_frozen_corpus_remains_identical_to_canonical_corpus(self):
        from agents.tools.dify_normalize_evidence import APPROVED_CORPUS
        self.assertEqual(APPROVED_CORPUS, [e.to_dict() for e in CorpusRetriever(ROOT).chunks])


if __name__ == '__main__':
    unittest.main()
