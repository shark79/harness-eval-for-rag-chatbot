import test from 'node:test';
import assert from 'node:assert/strict';
import { request } from '../src/services/api.js';

test('request sends JSON and returns the server result', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async (path, options) => {
    assert.equal(path, '/api/chat');
    assert.equal(options.method, 'POST');
    assert.equal(options.headers['Content-Type'], 'application/json');
    assert.deepEqual(JSON.parse(options.body), { ticket_text: 'App key?' });
    return { ok: true, json: async () => ({ answer: 'Open API Access.' }) };
  };
  try { assert.deepEqual(await request('/api/chat', { ticket_text: 'App key?' }), { answer: 'Open API Access.' }); }
  finally { globalThis.fetch = original; }
});

test('request exposes a safe server error', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => ({ ok: false, status: 503, json: async () => ({ error: 'Dify is unavailable.' }) });
  try { await assert.rejects(request('/api/chat', {}), /Dify is unavailable/); }
  finally { globalThis.fetch = original; }
});

test('an unreadable server response gives an actionable error', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => ({ ok: false, json: async () => { throw new Error('Invalid JSON'); } });
  try { await assert.rejects(request('/api/chat', {}), /unreadable response/); }
  finally { globalThis.fetch = original; }
});
