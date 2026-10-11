"""Paste into the citation finalization Code node after structured LLM output."""

CATEGORIES = {'api_keys', 'model_providers', 'rag_pipeline', 'billing_plans', 'account_workspace', 'unknown'}
DISPOSITIONS = {'answered', 'needs_clarification', 'partial_escalation', 'escalated', 'temporarily_unavailable'}


def main(candidate: dict, evidence: list) -> dict:
    if not isinstance(candidate, dict) or not isinstance(evidence, list) or len(evidence) > 64:
        raise ValueError('Invalid candidate or normalized evidence.')
    answer, category, disposition = (candidate.get(k) for k in ('answer', 'category', 'disposition'))
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError('A nonempty customer answer is required.')
    if not isinstance(category, str) or category not in CATEGORIES:
        raise ValueError('Invalid category.')
    if not isinstance(disposition, str) or disposition not in DISPOSITIONS:
        raise ValueError('Invalid disposition.')
    by_id = {}
    fields = ('evidence_id', 'source_id', 'section_id', 'source_revision', 'excerpt')
    for record in evidence:
        if not isinstance(record, dict) or any(not isinstance(record.get(k), str) or not record[k].strip() for k in fields):
            raise ValueError('Evidence must come from the normalization node.')
        if record['evidence_id'] in by_id:
            raise ValueError('Evidence IDs must be unique.')
        by_id[record['evidence_id']] = record
    selected = candidate.get('cited_evidence_ids')
    if not isinstance(selected, list) or len(selected) > 64:
        raise ValueError('Cited evidence IDs must be an array of at most 64 strings.')
    citations = []
    seen = set()
    for ident in selected:
        if not isinstance(ident, str) or ident not in by_id:
            raise ValueError('The model cited evidence not supplied to it.')
        if ident not in seen:
            citations.append({k: by_id[ident][k] for k in ('evidence_id', 'source_id', 'section_id')})
            seen.add(ident)
    if disposition == 'answered' and not citations:
        raise ValueError('An answered candidate must cite actual retrieval evidence.')
    return {'answer': answer, 'category': category, 'disposition': disposition,
            'evidence': evidence, 'citations': citations}
