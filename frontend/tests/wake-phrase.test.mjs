import assert from 'node:assert/strict';
import test from 'node:test';

import {
  extractWakeCommand,
  findWakePhrase,
  isEmergencyStopCommand,
  selectVoiceTranscriptAlternative,
  shouldUseWakeRecorderFallback,
} from '../app/lib/wake-phrase.ts';

test('accepts the configured wake name and its observed ASR rendering', () => {
  for (const transcript of [
    'Hey Elara',
    'Hey ElaraX, show urgent emails',
    'Hey Alana',
    'Hey Alana, what is on my calendar?',
    'Hey DeskBot, show urgent emails',
    'Hey Desk Bot, what is on my calendar?',
    'Hey Desk-Bot, check my inbox',
    'Hey Desk Boat, start my briefing',
    'Hey Desktop, check my inbox',
  ]) {
    assert.ok(findWakePhrase(transcript), transcript);
  }
});

test('still requires Hey followed by a narrowly accepted name', () => {
  for (const transcript of [
    'Elara, show urgent emails',
    'Okay Alana',
    'Hey Alexa',
    'Hey Lana',
    'They Alana said hello',
    'The calendar is ready',
  ]) {
    assert.equal(findWakePhrase(transcript), null, transcript);
  }
});

test('preserves the inline command boundary after the matched phrase', () => {
  const transcript = 'Hey Alana, show urgent emails';
  assert.equal(extractWakeCommand(transcript), 'show urgent emails');
  assert.equal(extractWakeCommand('Hey Elara'), '');
  assert.equal(extractWakeCommand('unrelated speech'), undefined);
});

test('uses recorder fallback only for unavailable browser recognition services', () => {
  for (const error of ['unsupported', 'network', 'service-not-allowed', 'language-not-supported']) {
    assert.equal(shouldUseWakeRecorderFallback(error), true, error);
  }
  for (const error of ['not-allowed', 'audio-capture', 'no-speech', 'aborted']) {
    assert.equal(shouldUseWakeRecorderFallback(error), false, error);
  }
});

test('keeps emergency stop matching narrow and standalone', () => {
  for (const command of ['stop', 'Stop moving.', 'please halt now', 'रुको।', 'থামো']) {
    assert.equal(isEmergencyStopCommand(command), true, command);
  }
  for (const command of ['stop checking email', 'the bus stop is nearby', 'please stop sending the reply']) {
    assert.equal(isEmergencyStopCommand(command), false, command);
  }
});

test('prefers an imperative command alternative over a slightly higher-confidence past tense', () => {
  const transcript = selectVoiceTranscriptAlternative([
    {
      transcript: 'Hey Elara sent email to sreoshibhowmik28@gmail.com',
      confidence: 0.92,
    },
    {
      transcript: 'Hey Elara send email to sreoshibhowmik28@gmail.com',
      confidence: 0.86,
    },
  ]);

  assert.equal(transcript, 'Hey Elara send email to sreoshibhowmik28@gmail.com');
});

test('keeps the highest-confidence alternative when command structure is equivalent', () => {
  const transcript = selectVoiceTranscriptAlternative([
    { transcript: 'Hey Elara show my urgent emails', confidence: 0.81 },
    { transcript: 'Hey Elara show my agent emails', confidence: 0.55 },
  ]);

  assert.equal(transcript, 'Hey Elara show my urgent emails');
  assert.equal(selectVoiceTranscriptAlternative([]), '');
});
