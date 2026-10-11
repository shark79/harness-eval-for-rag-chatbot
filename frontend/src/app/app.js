import { request } from '../services/api.js';
import { renderAnswer, renderEvaluation, renderSingleEvaluation } from '../components/results.js';
import { serializeResponses } from '../utils/csv.js';
import { nextTabIndex } from '../utils/navigation.js';

const ticket = document.querySelector('#ticket-text');
const examples = {
  app: 'Hi, I just published my first chatbot app and I want to call it from my own backend. Where do I get an API key for it?\n-- Marcus',
  provider: 'I want to use my own OpenAI account for the model. Where do I configure the provider key, and who bills the tokens?',
  retrieval: 'My knowledge base is returning zero chunks. Is this because I just configured a new provider key? What should I check?',
};
let latestAnswer;
let sampleTickets = [];
const sampleSelect = document.querySelector('#sample-ticket');
const tabs = [...document.querySelectorAll('[role="tab"]')];
function selectTab(index, focus = false) {
  tabs.forEach((tab, position) => {
    const active = position === index; tab.setAttribute('aria-selected', String(active)); tab.tabIndex = active ? 0 : -1;
    document.getElementById(tab.getAttribute('aria-controls')).hidden = !active;
  });
  if (focus) tabs[index].focus();
}
tabs.forEach((tab, index) => {
  tab.addEventListener('click', () => selectTab(index));
  tab.addEventListener('keydown', event => {
    const next = nextTabIndex(event.key, index, tabs.length);
    if (next !== null) { event.preventDefault(); selectTab(next, true); }
  });
});

sampleSelect.addEventListener('change', () => {
  const sample = sampleTickets.find(item => item.ticket_id === sampleSelect.value);
  if (sample) { ticket.value = sample.ticket_text; ticket.setCustomValidity(''); ticket.focus(); }
});

for (const button of document.querySelectorAll('[data-example]')) button.addEventListener('click', () => {
  ticket.value = examples[button.dataset.example]; sampleSelect.value = ''; ticket.setCustomValidity(''); ticket.focus();
});

document.querySelector('#ticket-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (!ticket.value.trim()) { ticket.setCustomValidity('Enter the customer’s ticket.'); ticket.reportValidity(); return; }
  const button = document.querySelector('#ask'), status = document.querySelector('#chat-status'), error = document.querySelector('#chat-error');
  button.disabled = true; status.textContent = 'Looking up documentation…'; error.hidden = true;
  const evaluationButtons = [document.querySelector('#evaluate-draft'), document.querySelector('#evaluate-current')];
  evaluationButtons.forEach(item => { item.disabled = true; });
  try {
    const sample = sampleTickets.find(item => item.ticket_id === sampleSelect.value && item.ticket_text === ticket.value);
    latestAnswer = await request('/api/chat', { ticket_text: ticket.value, ...(sample ? { ticket_id: sample.ticket_id } : {}) });
    renderAnswer(latestAnswer); renderSingleEvaluation(latestAnswer); status.textContent = 'Draft ready. Send it to Eval bot for review.';
    document.querySelector('#single-eval-status').textContent = ''; document.querySelector('#single-eval-error').hidden = true;
  } catch (failure) { error.textContent = failure.message; error.hidden = false; status.textContent = 'Draft unavailable.'; }
  finally { button.disabled = false; evaluationButtons.forEach(item => { item.disabled = false; }); }
});
ticket.addEventListener('input', () => ticket.setCustomValidity(''));

async function evaluateDraft() {
  if (!latestAnswer?.draft_id) return;
  selectTab(1, true);
  const buttons = [document.querySelector('#evaluate-draft'), document.querySelector('#evaluate-current')];
  const status = document.querySelector('#single-eval-status'), error = document.querySelector('#single-eval-error');
  document.querySelector('#ask').disabled = true;
  buttons.forEach(button => { button.disabled = true; }); error.hidden = true; status.textContent = 'Eval bot is checking the stored response and ticket…';
  try {
    const evaluated = await request('/api/evaluate-response', { draft_id: latestAnswer.draft_id });
    latestAnswer = evaluated;
    renderAnswer(evaluated);
    renderSingleEvaluation(evaluated); status.textContent = `Evaluation complete: ${evaluated.decision === 'ship' ? 'Ship' : 'Hold'}.`;
  } catch (failure) { error.textContent = failure.message; error.hidden = false; status.textContent = 'Evaluation unavailable. The draft has not been approved.'; }
  finally { buttons.forEach(button => { button.disabled = false; }); document.querySelector('#ask').disabled = false; }
}
document.querySelector('#evaluate-draft').addEventListener('click', evaluateDraft);
document.querySelector('#evaluate-current').addEventListener('click', evaluateDraft);

document.querySelector('#export').addEventListener('click', () => {
  if (!latestAnswer) return;
  const url = URL.createObjectURL(new Blob([serializeResponses([latestAnswer])], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a'); link.href = url; link.download = 'ticket-response.csv'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

document.querySelector('#eval-form').addEventListener('submit', async event => {
  event.preventDefault();
  const button = document.querySelector('#run-eval'), error = document.querySelector('#eval-error'), status = document.querySelector('#eval-status');
  button.disabled = true; error.hidden = true; status.textContent = 'Running the separate evaluation suite…';
  try { renderEvaluation(await request('/api/evaluations', { source: document.querySelector('#eval-source').value, limit: 26 })); }
  catch (failure) { error.textContent = failure.message; error.hidden = false; status.textContent = 'Evaluation unavailable. Responses remain held.'; }
  finally { button.disabled = false; }
});

request('/api/health').then(health => {
  document.querySelector('#connection').textContent = health.mode === 'extractive'
    ? 'Local retrieval mode · Answers quote approved source passages.'
    : `${health.mode === 'dify' ? 'Dify Cloud' : health.mode} · ${health.configured ? 'Configured' : 'Configuration required'}`;
}).catch(() => { document.querySelector('#connection').textContent = 'Server unavailable. Check that the application is running.'; });

request('/api/evaluations/latest').then(report => { if (report?.run_id) renderEvaluation(report); }).catch(() => {});
request('/api/tickets').then(result => {
  sampleTickets = result.tickets;
  for (const sample of sampleTickets) {
    const option = document.createElement('option'); option.value = sample.ticket_id;
    option.textContent = `${sample.ticket_id} · ${sample.category} · ${sample.ticket_text.slice(0, 60)}`;
    sampleSelect.append(option);
  }
}).catch(() => { sampleSelect.options[0].textContent = 'Samples unavailable. You can still enter your own ticket.'; });
