// Browser speech recognition is especially inconsistent with short names.
// Keep the required "Hey" prefix, but accept the common phonetic renderings
// users will encounter for both supported names.
const WAKE_PHRASE = /\bhey[\s,.-]+(?:elara(?:\s*x)?|alara|alora|elora|ilara|alana|desk[-\s]*bot|desk\s+boat|desk\s+but|desk\s+body|desk\s+board|desk\s+bolt|desk\s+bought|desktop)\b/i;
const COMMAND_VERB = /\b(?:send|draft|compose|write|show|read|find|check|schedule|create|reschedule|cancel|move|turn|come|look|what|where|when|who|how)\b/i;
const PAST_TENSE_COMMAND = /\b(?:sent|drafted|composed|wrote|showed|found|checked|scheduled|created|moved|turned)\s+(?:an?\s+)?(?:email|mail|message|meeting)\b/i;
const EMAIL_ADDRESS = /\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b/i;
const EMERGENCY_STOP = /^(?:please\s+)?(?:stop\s+moving|stop|halt|ruko|thamo|দাঁড়াও|থামো|दाँड़ाओ|रुको|रुक)(?:\s+(?:now|robot|elarax|elara|aetherbot|bot))?[.!?।]?$/iu;

export type SpeechTranscriptAlternative = {
  transcript: string;
  confidence?: number;
};

export function findWakePhrase(transcript: string): RegExpExecArray | null {
  return WAKE_PHRASE.exec(transcript);
}

export function extractWakeCommand(transcript: string): string | undefined {
  const match = findWakePhrase(transcript);
  if (!match) return undefined;
  return transcript
    .slice((match.index ?? 0) + match[0].length)
    .replace(/^[\s,.:;!?-]+/, '')
    .trim();
}

function commandTranscriptScore(candidate: SpeechTranscriptAlternative): number {
  const transcript = candidate.transcript.trim();
  const confidence = Number.isFinite(candidate.confidence)
    ? Math.max(0, Math.min(1, candidate.confidence ?? 0))
    : 0;
  let score = confidence * 3;
  if (findWakePhrase(transcript)) score += 5;
  if (COMMAND_VERB.test(transcript)) score += 2;
  if (EMAIL_ADDRESS.test(transcript)) score += 2;
  if (PAST_TENSE_COMMAND.test(transcript)) score -= 1.5;
  return score;
}

export function selectVoiceTranscriptAlternative(
  alternatives: SpeechTranscriptAlternative[],
): string {
  const candidates = alternatives
    .map((candidate) => ({ ...candidate, transcript: candidate.transcript.trim() }))
    .filter((candidate) => candidate.transcript);
  if (candidates.length === 0) return '';
  return candidates.reduce((best, candidate) => (
    commandTranscriptScore(candidate) > commandTranscriptScore(best) ? candidate : best
  )).transcript;
}

export function shouldUseWakeRecorderFallback(error: string): boolean {
  return ['unsupported', 'network', 'service-not-allowed', 'language-not-supported'].includes(error.toLocaleLowerCase());
}

export function isEmergencyStopCommand(transcript: string): boolean {
  return EMERGENCY_STOP.test(transcript.trim());
}
