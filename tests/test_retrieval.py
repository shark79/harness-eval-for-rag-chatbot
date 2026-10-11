"""Approved source boundary and evidence provenance tests."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RetrievalTests(unittest.TestCase):
    def retriever(self):
        self.assertTrue((ROOT / 'backend/app/services/retrieval.py').is_file(), 'Corpus retrieval must be implemented')
        from backend.app.services.retrieval import CorpusRetriever
        return CorpusRetriever(ROOT)

    def test_returned_excerpts_are_present_in_approved_source(self):
        evidence = self.retriever().retrieve('published app backend API key')
        self.assertTrue(evidence)
        manifest = json.loads((ROOT / 'shared/contracts/evidence-sources.json').read_text())
        sources = {source['id']: source for source in manifest['sources']}
        for item in evidence:
            source = sources[item.source_id]
            original = (ROOT / source['path']).read_text()
            self.assertIn(item.excerpt, original)
            self.assertEqual(item.source_revision, source['sha256'])

    def test_csv_baseline_answers_never_indexed(self):
        retriever = self.retriever()
        self.assertEqual({item.source_id for item in retriever.chunks}, {'product_guide', 'api_transport_supplement'})
        self.assertFalse(any('TCK-' in item.excerpt for item in retriever.chunks))

    def test_unrelated_query_has_no_evidence(self):
        self.assertEqual(self.retriever().retrieve('weather forecast tokyo tomorrow'), [])

    def test_modified_manifest_source_is_not_trusted(self):
        self.retriever()
        from backend.app.services.retrieval import CorpusRetriever, CorpusError
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'knowledge/sources').mkdir(parents=True)
            (root / 'shared/contracts').mkdir(parents=True)
            (root / 'knowledge/sources/test.md').write_text('## Approved\n\nAltered source')
            manifest = {'sources': [{'id': 'test', 'path': 'knowledge/sources/test.md', 'sha256': '0' * 64, 'section_ids': ['approved']}]}
            (root / 'shared/contracts/evidence-sources.json').write_text(json.dumps(manifest))
            with self.assertRaises(CorpusError):
                CorpusRetriever(root)


if __name__ == '__main__':
    unittest.main()

class RetrievalScopeTests(unittest.TestCase):
    def test_provider_queries_exclude_transport_supplement(self):
        from backend.app.services.retrieval import CorpusRetriever
        rows = CorpusRetriever(ROOT).retrieve('OpenAI API key backend HTTP Authorization', 'model_providers')
        self.assertTrue(rows)
        self.assertTrue(all(row.section_id == 'model_providers' for row in rows))
