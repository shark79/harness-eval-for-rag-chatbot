"""Regression tests for grounded ticket chat behavior."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ChatServiceTests(unittest.TestCase):
    def service(self):
        self.assertTrue((ROOT / 'backend/app/services/chat.py').is_file(), 'Chat service must be implemented')
        from backend.app.config.settings import Settings
        from backend.app.services.chat import ChatService
        return ChatService(Settings(root=ROOT))

    def test_published_app_question_retrieves_app_key_instructions(self):
        result = self.service().answer('Hi, I published my first chatbot and want to call it from my backend. Where do I get its API key?', 'arbitrary-id')
        self.assertEqual(result['category'], 'api_keys')
        self.assertIn('API Access', result['answer'])
        self.assertIn('app-', result['answer'])
        self.assertNotIn('Settings → Model Provider', result['answer'])
        self.assertTrue(result['citations'])
        self.assertEqual(result['mode'], 'extractive')
        self.assertEqual(result['ticket_id'], 'arbitrary-id')

    def test_provider_key_configuration_keeps_scope(self):
        result = self.service().answer('How do I connect my own OpenAI API key instead of Dify-hosted credits?')
        self.assertEqual(result['category'], 'model_providers')
        self.assertIn('Model Provider', result['answer'])
        self.assertNotIn('Create new Secret Key', result['answer'])

    def test_negated_provider_key_does_not_override_app_intent(self):
        result = self.service().answer('I do not need an OpenAI provider key. I need a key to call my published app from my backend.')
        self.assertEqual(result['category'], 'api_keys')
        self.assertIn('API Access', result['answer'])

    def test_ambiguous_key_asks_for_object(self):
        result = self.service().answer('Where is my API key?')
        self.assertEqual(result['disposition'], 'needs_clarification')
        self.assertEqual(result['category'], 'unknown')
        self.assertFalse(result['citations'])

    def test_unknown_topic_does_not_return_random_docs(self):
        result = self.service().answer('What is the weather in Tokyo tomorrow?')
        self.assertEqual(result['disposition'], 'needs_clarification')
        self.assertFalse(result['evidence'])

    def test_excluded_configuration_is_escalated(self):
        result = self.service().answer('How do I configure SAML single sign-on?')
        self.assertEqual(result['disposition'], 'escalated')
        self.assertIn('specialist', result['answer'].lower())

    def test_empty_input_is_rejected(self):
        with self.assertRaises(ValueError):
            self.service().answer('   ')

    def test_ticket_identifier_cannot_select_fixture_answer(self):
        service = self.service()
        query = 'How do I invite a teammate into my workspace?'
        self.assertEqual(service.answer(query, 'TCK-1001')['answer'], service.answer(query, 'TCK-1026')['answer'])

    def test_long_input_is_rejected(self):
        with self.assertRaises(ValueError):
            self.service().answer('x' * 16001)

    def test_provider_mode_requires_credentials_and_never_falls_back(self):
        self.service()
        from backend.app.config.settings import Settings
        from backend.app.services.chat import ChatService
        from backend.app.integrations.providers import ProviderError
        service = ChatService(Settings(root=ROOT, mode='dify'))
        with self.assertRaises(ProviderError):
            service.answer('Where do I get the API key for my published app?')


if __name__ == '__main__':
    unittest.main()

class DifyEvidenceTests(unittest.TestCase):
    def test_dify_citations_cannot_forge_supporting_text(self):
        from backend.app.config.settings import Settings
        from backend.app.services.chat import ChatService
        from backend.app.integrations.providers import ProviderError
        from unittest.mock import patch
        service = ChatService(Settings(root=ROOT, mode='dify', dify_api_key='test-secret'))
        item = service.retriever.chunks[0].to_dict()
        output = {'answer': 'candidate', 'category': 'api_keys', 'disposition': 'answered',
                  'evidence': [item], 'citations': [{**item, 'excerpt': 'invented supporting text'}]}
        with patch('backend.app.services.chat.workflow_answer', return_value=output):
            with self.assertRaises(ProviderError):
                service.answer('API key for my published app')

class ProviderBoundaryTests(unittest.TestCase):
    def test_malformed_workflow_enums_are_provider_errors(self):
        from backend.app.config.settings import Settings
        from backend.app.services.chat import ChatService
        from backend.app.integrations.providers import ProviderError
        from unittest.mock import patch
        service = ChatService(Settings(root=ROOT, mode='dify', dify_api_key='test-secret'))
        item = service.retriever.chunks[0].to_dict()
        for field in ('category', 'disposition'):
            output = {'answer': 'candidate', 'category': 'api_keys', 'disposition': 'answered', 'evidence': [item], 'citations': [item]}
            output[field] = []
            with self.subTest(field=field), patch('backend.app.services.chat.workflow_answer', return_value=output):
                with self.assertRaises(ProviderError):
                    service.answer('API key for my published app')

class ProviderSecretTests(unittest.TestCase):
    def test_provider_echo_cannot_expose_configured_app_key(self):
        from backend.app.config.settings import Settings
        from backend.app.integrations.providers import workflow_answer
        from unittest.mock import patch
        settings = Settings(root=ROOT, mode='dify', dify_api_key='app-test-secret')
        response = {'data': {'status':'succeeded', 'outputs': {'answer':'echo app-test-secret', 'evidence':[], 'citations':[]}}}
        with patch('backend.app.integrations.providers.request', return_value=response):
            output = workflow_answer(settings, 'Where is the key?')
        self.assertNotIn(settings.dify_api_key, output['answer'])
