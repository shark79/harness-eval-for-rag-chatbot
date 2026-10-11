import test from 'node:test';
import assert from 'node:assert/strict';
import { serializeResponses } from '../src/utils/csv.js';

test('CSV export preserves quoted, multiline ticket and answer text in exactly three columns', () => {
  assert.equal(serializeResponses([{ticket_text:'Where is my "app" key?\n-- Marcus',assistant_answer:'Use "API Access", then copy it.',category:'api_keys'}]),
    'ticket_text,assistant_answer,category\r\n"Where is my ""app"" key?\n-- Marcus","Use ""API Access"", then copy it.","api_keys"\r\n');
});

test('CSV export supports chat answer field without exporting traces or secrets from other fields', () => {
  assert.equal(serializeResponses([{ticket_text:'Question',answer:'Reply',category:'api_keys',trace:{secret:'do not export'}}]),
    'ticket_text,assistant_answer,category\r\n"Question","Reply","api_keys"\r\n');
});

test('empty export remains a valid header-only file', () => {
  assert.equal(serializeResponses([]), 'ticket_text,assistant_answer,category\r\n');
});
