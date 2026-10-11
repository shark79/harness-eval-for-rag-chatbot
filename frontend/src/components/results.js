export function formatScore(value) {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(3) : 'Not run';
}

export function decisionLabel(decision) { return decision === 'ship' ? 'Ship' : 'Hold'; }

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function sourceBlocks(result) {
  const evidence = result.evidence?.length ? result.evidence : result.citations ?? [];
  return evidence.length ? evidence.map(item => {
    const block = element('div', undefined, 'evidence');
    block.append(element('h3', `${item.source_id} / ${item.section_id}`), element('p', item.excerpt));
    return block;
  }) : [element('p', 'No supporting documentation was returned. Hold this draft for review.')];
}

function reviewDetails(result, policy = {}) {
  const details = element('details');
  details.append(element('summary', 'Why this decision'));
  details.append(element('p', result.why?.decision_reason ?? result.stop_reason ?? 'Evaluation is incomplete; hold off.', 'score-explanation'));
  details.append(element('p', `Original score: ${formatScore(result.original_score)}. Final score: ${formatScore(result.final_score ?? result.score)}.`, 'quiet'));
  details.append(element('p', `Answer generation retried: ${result.generation_retried === true ? 'Yes' : result.generation_retried === false ? 'No' : 'Not reported'}. Scoring retried: ${result.scoring_retried === true ? 'Yes' : result.scoring_retried === false ? 'No' : 'Not reported'}.`, 'quiet'));
  const dimensions = element('div', undefined, 'dimensions');
  const ranked = result.why?.dimensions_ranked ?? Object.entries(result.dimensions ?? {}).map(([dimension, score]) => ({ dimension, score, weight: policy.weights?.[dimension] }));
  if (ranked.length) dimensions.append(element('h3', 'Dimensions, lowest score first'));
  for (const item of ranked) {
    const label = `${item.dimension.replaceAll('_', ' ')}: ${formatScore(item.score)}${typeof item.weight === 'number' ? ` · weight ${Math.round(item.weight * 100)}%` : ''}`;
    dimensions.append(element('p', `${label}${item.reason ? ` — ${item.reason}` : ''}`));
  }
  details.append(dimensions);
  const findings = element('ul');
  for (const failure of result.why?.hard_failures ?? result.deterministic?.failures ?? []) findings.append(element('li', failure.reason ?? failure.code));
  findings.append(element('li', `Semantic evaluation: ${(result.semantic?.status ?? 'not_run').replaceAll('_', ' ')}`));
  if (result.semantic?.reason) findings.append(element('li', result.semantic.reason));
  if (result.why?.rule_score_limit) findings.append(element('li', result.why.rule_score_limit));
  details.append(findings);
  return details;
}

export function renderAnswer(result) {
  document.querySelector('#answer-text').textContent = result.answer;
  const meta = document.querySelector('#answer-meta');
  meta.replaceChildren(...[result.category, result.disposition?.replaceAll('_', ' '), result.mode === 'extractive' ? 'Local source excerpts' : result.mode].filter(Boolean).map(text => element('span', text, 'tag')));
  const list = document.querySelector('#evidence-list');
  list.replaceChildren(...sourceBlocks(result));
  const release = document.querySelector('#answer-release');
  release.replaceChildren(element('strong', 'Awaiting Eval bot'), element('p', 'This is the RAG bot’s draft. Evaluate it before making a ship or hold decision.', 'quiet'));
  document.querySelector('#answer-area').hidden = false;
  document.querySelector('#empty-answer').hidden = true;
}

export function renderSingleEvaluation(result) {
  const container = document.querySelector('#single-evaluation');
  const title = element('h2', result.evaluation ? `${decisionLabel(result.decision)} · Score ${formatScore(result.score)}` : 'Response awaiting evaluation');
  container.replaceChildren(title, element('h3', `Ticket ${result.ticket_id ?? ''}`), element('p', result.ticket_text, 'ticket-preview'),
    element('h3', result.evaluation ? 'Evaluated response' : 'RAG bot’s draft'), element('p', result.answer, 'answer'));
  if (result.evaluation) container.append(reviewDetails({ ...result, ...result.evaluation }));
  const sources = element('details', undefined, 'sources');
  sources.append(element('summary', 'Supporting documentation'), ...sourceBlocks(result)); container.append(sources);
  document.querySelector('#evaluate-current').hidden = false;
}

export function renderEvaluation(report) {
  const summary = document.querySelector('#eval-summary');
  const metrics = element('div', undefined, 'metrics');
  for (const [label, value] of [['Ship', report.summary.ship], ['Hold off', report.summary.hold_off], ['Semantic checks not run', report.summary.semantic_not_run]]) {
    const item = element('p'); item.append(element('strong', String(value ?? 0)), document.createTextNode(label)); metrics.append(item);
  }
  summary.replaceChildren(metrics, element('p', report.release?.reason ?? 'Review the scores and mandatory gates before release.', 'quiet'));
  const table = element('table');
  const caption = element('caption', `Per-ticket scores · ${report.source} · ${report.mode}`);
  caption.style.textAlign = 'left'; caption.style.marginBottom = '10px'; table.append(caption);
  const head = element('thead'), heading = element('tr');
  for (const title of ['Ticket', 'Original score', 'Final score', 'Decision', 'Review']) { const th = element('th', title); th.scope = 'col'; heading.append(th); }
  head.append(heading); table.append(head);
  const body = element('tbody');
  for (const result of report.cases ?? []) {
    const row = element('tr');
    row.append(element('td', result.ticket_id), element('td', formatScore(result.original_score ?? result.attempts?.[0]?.score)), element('td', formatScore(result.final_score ?? result.score)), element('td', decisionLabel(result.decision)));
    const cell = element('td'), details = reviewDetails(result, report.policy);
    details.append(element('p', result.ticket_text), element('p', result.answer));
    const sources = element('details', undefined, 'sources');
    sources.append(element('summary', 'Supporting documentation'), ...sourceBlocks(result)); details.append(sources);
    cell.append(details); row.append(cell); body.append(row);
  }
  table.append(body);
  const container = element('div', undefined, 'table-scroll'); container.append(table);
  document.querySelector('#eval-results').replaceChildren(container);
  document.querySelector('#eval-status').textContent = `${report.case_count} tickets evaluated. Run ${report.run_id}.`;
}
