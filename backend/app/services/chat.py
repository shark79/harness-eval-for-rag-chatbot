"""Basic ticket retrieval and Dify workflow orchestration."""
from typing import Any
import re
from backend.app.config.settings import Settings
from backend.app.integrations.providers import ProviderError, workflow_answer
from backend.app.services.retrieval import CorpusRetriever

CATEGORIES = {'api_keys': 'workspace_api_keys', 'account_workspace': 'workspace_api_keys',
              'model_providers': 'model_providers', 'rag_pipeline': 'rag_pipeline', 'billing_plans': 'billing_plans'}


def category_for(ticket: str) -> str:
    """Use contextual key scope, preserving explicit negation in this demo router."""
    text = ticket.lower()
    # shortcut: lexical context only; Dify's classifier should replace this for live traffic.
    text = re.sub(r'\b(?:i )?(?:do not|don\'t|not) need[^.!?]*[.!?]', '', text)
    if re.search(r'published|app.? api|call.{0,45}(app|chatbot)|backend|app-', text) and re.search(r'key|token|auth|401', text):
        return 'api_keys'
    if re.search(r'openai|anthropic|azure|provider|hosted model|credits.{0,20}(used|exhaust)', text):
        return 'model_providers'
    if re.search(r'dataset.{0,20}key|service api|401|api key|secret key|bearer', text):
        return 'api_keys' if re.search(r'dataset|knowledge|app|chatbot|rotate|401', text) else 'unknown'
    if re.search(r'retriev|chunk|index|embed|knowledge|rag|document|top_k|rerank', text):
        return 'rag_pipeline'
    if re.search(r'sso|saml|single sign.on|audit.log|compliance', text):
        return 'account_workspace'
    if re.search(r'bill|plan|sandbox|professional|enterprise|team plan|payment|invoice|downgrade|subscription|price|storage|seat|limit', text):
        return 'billing_plans'
    if re.search(r'member|teammate|invite|workspace|role|admin', text):
        return 'account_workspace'
    return 'unknown'


class ChatService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.retriever = CorpusRetriever(settings.root)

    def health(self) -> dict[str, Any]:
        return {'mode': self.settings.mode, 'configured': self.settings.mode == 'extractive' or bool(self.settings.dify_api_key), 'corpus_ready': bool(self.retriever.chunks)}

    def answer(self, ticket_text: str, ticket_id: str = '', *, feedback: str = '') -> dict[str, Any]:
        """Return a ticket answer, approved evidence and explicit execution mode."""
        if not isinstance(ticket_text, str) or not ticket_text.strip() or len(ticket_text) > 16000:
            raise ValueError('ticket_text must contain 1 to 16000 characters.')
        if not isinstance(ticket_id, str) or len(ticket_id) > 200:
            raise ValueError('ticket_id must be a string of at most 200 characters.')
        if not isinstance(feedback, str) or len(feedback) > 8000:
            raise ValueError('feedback must be a string of at most 8000 characters.')
        ticket = ticket_text.strip()
        category = category_for(ticket)
        result: dict[str, Any] = {'ticket_id': ticket_id, 'ticket_text': ticket_text,
            'category': category, 'mode': self.settings.mode, 'evidence': [], 'citations': [],
            'trace': {'routing': 'contextual_lexical', 'retry_feedback_received': bool(feedback)}}
        if self.settings.mode == 'dify':
            outputs = workflow_answer(self.settings, ticket, feedback)
            evidence = outputs['evidence']
            approved = {item.evidence_id: item for item in self.retriever.chunks}
            if len(evidence) > 64:
                raise ProviderError('Dify returned too many evidence records.')
            for item in evidence:
                if not isinstance(item, dict):
                    raise ProviderError('Dify evidence must contain objects.')
                matching = [chunk for chunk in approved.values()
                    if item.get('source_id') == chunk.source_id
                    and item.get('section_id') == chunk.section_id
                    and isinstance(item.get('excerpt'), str) and item['excerpt'].strip()
                    and item['excerpt'] in chunk.excerpt
                    and item.get('source_revision') == chunk.source_revision]
                if not matching or not isinstance(item.get('evidence_id'), str) or not item['evidence_id'].strip():
                    raise ProviderError('Dify evidence does not match an approved source revision.')
            evidence_by_id = {item['evidence_id']: item for item in evidence}
            if len(evidence_by_id) != len(evidence):
                raise ProviderError('Dify evidence identifiers must be unique.')
            citations = outputs['citations']
            for item in citations:
                if not isinstance(item, dict) or not isinstance(item.get('evidence_id'), str) or item['evidence_id'] not in evidence_by_id:
                    raise ProviderError('Dify citations must refer to returned evidence.')
                support = evidence_by_id[item['evidence_id']]
                if any(key in item and item[key] != support[key] for key in ('source_id', 'section_id', 'excerpt', 'source_revision')):
                    raise ProviderError('Dify citations must match their supporting evidence.')
            disposition = outputs.get('disposition', 'answered')
            if not isinstance(disposition, str) or disposition not in {'answered', 'needs_clarification', 'partial_escalation', 'escalated', 'temporarily_unavailable'}:
                raise ProviderError('Dify returned an invalid disposition.')
            if disposition == 'answered' and (not evidence or not citations):
                raise ProviderError('Dify answers require evidence and citations.')
            category = outputs.get('category', category)
            if not isinstance(category, str) or category not in {*CATEGORIES, 'unknown'}:
                raise ProviderError('Dify returned an invalid category.')
            result.update(answer=outputs['answer'], category=category, disposition=disposition,
                          evidence=evidence, citations=citations, trace={'routing': 'dify_workflow'})
            return result
        if re.search(r'saml|single sign.on|sso|audit.log|compliance|self.host|plugin sdk', ticket, re.I):
            result.update(answer='This guide does not cover that configuration. Please contact the appropriate specialist team.', disposition='escalated')
            return result
        if category == 'unknown':
            result.update(answer='Please clarify the product feature and what you are trying to do. If this concerns a key, is it for a published app, a knowledge dataset, or a model provider?', disposition='needs_clarification')
            return result
        query = ticket
        if category == 'api_keys' and re.search(r'app|chatbot|backend', ticket, re.I):
            query += ' App API keys published API Access Create new Secret Key app authentication'
        if category == 'model_providers':
            query += ' Settings Model Provider credentials plugin'
        evidence = self.retriever.retrieve(query, CATEGORIES[category], limit=2)
        if not evidence:
            result.update(answer='The approved guide does not contain enough matching information. Please add details about the feature and the error you see.', disposition='needs_clarification')
            return result
        result.update(answer='From the approved documentation:\n\n' + '\n\n'.join(item.excerpt for item in evidence), disposition='answered',
            evidence=[item.to_dict() for item in evidence], citations=[item.to_dict() for item in evidence])
        return result
