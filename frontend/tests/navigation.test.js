import test from 'node:test';
import assert from 'node:assert/strict';
import { nextTabIndex } from '../src/utils/navigation.js';

test('tab arrow keys wrap and Home or End reach the boundary', () => {
  assert.equal(nextTabIndex('ArrowRight', 1, 2), 0);
  assert.equal(nextTabIndex('ArrowLeft', 0, 2), 1);
  assert.equal(nextTabIndex('Home', 1, 2), 0);
  assert.equal(nextTabIndex('End', 0, 2), 1);
  assert.equal(nextTabIndex('Tab', 0, 2), null);
});
