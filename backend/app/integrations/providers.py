"""Dify Cloud and self-hosted adapter reusing the toolkit's bounded, redirect-safe transport."""
from typing import Any
from backend.app.config.settings import Settings
from scripts.dify_api import Call, DifyError, redact, request


class ProviderError(RuntimeError):
    """A provider call failed or returned an unusable answer."""


def workflow_answer(settings: Settings, ticket: str, feedback: str = '') -> dict[str, Any]:
    if not settings.dify_api_key:
        raise ProviderError('Configure DIFY_APP_API_KEY in local .env before using Dify mode.')
    inputs = {settings.dify_input_name: ticket}
    if feedback:
        inputs['evaluation_feedback'] = feedback
    call = Call('POST', '/workflows/run', {'inputs': inputs, 'response_mode': 'blocking', 'user': 'ticket-chat-local'}, 'DIFY_APP_API_KEY')
    try:
        result = request(call, settings.dify_base_url, 100.0, settings.dify_api_key)
    except DifyError as error:
        raise ProviderError(str(error)) from None
    data = result.get('data', {})
    if not isinstance(data, dict) or data.get('status') != 'succeeded':
        raise ProviderError('Dify workflow did not succeed; inspect its server-side trace.')
    outputs = data.get('outputs')
    if not isinstance(outputs, dict) or not isinstance(outputs.get('answer'), str) or not outputs['answer'].strip():
        raise ProviderError('Dify workflow must return a nonempty answer output.')
    for name in ('evidence', 'citations'):
        if isinstance(outputs.get(name), str):
            import json
            try:
                outputs[name] = json.loads(outputs[name])
            except ValueError:
                raise ProviderError(f'Dify {name} must be a JSON array.') from None
        if not isinstance(outputs.get(name), list):
            raise ProviderError(f'Dify workflow must return actual {name} as an array.')
    return redact(outputs, [key for key in (settings.dify_api_key, settings.openai_api_key) if key])
