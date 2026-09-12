type WakeStreamLike = {
  active: boolean;
  getAudioTracks: () => ArrayLike<{ readyState: string }>;
};

export type BrowserSpeechRecognitionAlternative = {
  transcript: string;
  confidence: number;
};

export type BrowserSpeechRecognitionResult = {
  isFinal: boolean;
  length: number;
  [index: number]: BrowserSpeechRecognitionAlternative;
};

export type BrowserSpeechRecognitionEvent = Event & {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: BrowserSpeechRecognitionResult;
  };
};

export type BrowserSpeechRecognitionErrorEvent = Event & {
  error: string;
  message?: string;
};

export type BrowserSpeechRecognition = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  onstart: (() => void) | null;
  onresult: ((event: BrowserSpeechRecognitionEvent) => void) | null;
  onerror: ((event: BrowserSpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};

export type SpeechRecognitionConstructor = new () => BrowserSpeechRecognition;

export function getSpeechRecognitionConstructor(): SpeechRecognitionConstructor | undefined {
  if (typeof window === 'undefined') return undefined;
  const browserWindow = window as unknown as {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  };
  return browserWindow.SpeechRecognition || browserWindow.webkitSpeechRecognition;
}

export function canReuseWakeStream(stream?: WakeStreamLike): boolean {
  return Boolean(
    stream?.active
    && Array.from(stream.getAudioTracks()).some((track) => track.readyState === 'live'),
  );
}

export function enqueueWakeClip(
  currentQueue: Promise<void>,
  processClip: () => Promise<void>,
): Promise<void> {
  return currentQueue
    .catch(() => undefined)
    .then(processClip);
}
