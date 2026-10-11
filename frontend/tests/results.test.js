import test from 'node:test';
import assert from 'node:assert/strict';
import { formatScore, decisionLabel } from '../src/components/results.js';

test('an unrun score stays visibly unscored', () => {
  assert.equal(formatScore(null), 'Not run');
  assert.equal(formatScore(undefined), 'Not run');
});

test('score formatting keeps a retry score below the ship boundary', () => {
  assert.equal(formatScore(0.799), '0.799');
  assert.equal(formatScore(0), '0.000');
  assert.equal(formatScore(0.8), '0.800');
});

test('only a final ship verdict is labeled ship', () => {
  assert.equal(decisionLabel('ship'), 'Ship');
  assert.equal(decisionLabel('hold_off'), 'Hold');
  assert.equal(decisionLabel('retry'), 'Hold');
  assert.equal(decisionLabel(undefined), 'Hold');
});
