import assert from 'node:assert/strict';
import test from 'node:test';

import { canReuseWakeStream, enqueueWakeClip } from '../app/lib/wake-listener.ts';

test('reuses only an active stream with a live audio track', () => {
  const stream = (active, readyStates) => ({
    active,
    getAudioTracks: () => readyStates.map((readyState) => ({ readyState })),
  });

  assert.equal(canReuseWakeStream(stream(true, ['live'])), true);
  assert.equal(canReuseWakeStream(stream(true, ['ended', 'live'])), true);
  assert.equal(canReuseWakeStream(stream(true, ['ended'])), false);
  assert.equal(canReuseWakeStream(stream(false, ['live'])), false);
  assert.equal(canReuseWakeStream(undefined), false);
});

test('serializes background clip work and recovers after a rejected queue item', async () => {
  const order = [];
  let releaseFirst;
  const firstGate = new Promise((resolve) => {
    releaseFirst = resolve;
  });
  const first = enqueueWakeClip(Promise.resolve(), async () => {
    order.push('first-start');
    await firstGate;
    order.push('first-end');
  });
  const second = enqueueWakeClip(first, async () => {
    order.push('second');
  });

  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.deepEqual(order, ['first-start']);
  releaseFirst();
  await second;
  assert.deepEqual(order, ['first-start', 'first-end', 'second']);

  const recovered = enqueueWakeClip(Promise.reject(new Error('old clip failed')), async () => {
    order.push('recovered');
  });
  await recovered;
  assert.equal(order.at(-1), 'recovered');
});
