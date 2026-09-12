'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { MicVAD, type RealTimeVADOptions } from '@ricky0123/vad-web';

const NULL_AUDIO_ERROR = 'MicVAD has null stream, audio context, or processor adapter';

const errorMessage = (error: unknown) => error instanceof Error ? error.message : String(error);

const isNullAudioError = (error: unknown) => errorMessage(error).includes(NULL_AUDIO_ERROR);

/**
 * The published vad-react hook calls MicVAD.destroy() during React cleanup
 * even when MicVAD has not finished creating its audio nodes. vad-web then
 * throws from getAudioInstances(), which becomes an unhandled rejection.
 * Keep the same public controls while making teardown idempotent.
 */
const safelyDestroy = async (instance: MicVAD) => {
  try {
    await instance.destroy();
  } catch (error) {
    if (!isNullAudioError(error)) {
      console.warn('MicVAD cleanup failed:', error);
    }
  }
};

export type SafeMicVAD = {
  loading: boolean;
  listening: boolean;
  errored: string | null;
  start: () => Promise<void>;
  pause: () => Promise<void>;
  toggle: () => Promise<void>;
};

export function useSafeMicVAD(options: Partial<RealTimeVADOptions>): SafeMicVAD {
  const optionsRef = useRef(options);

  useEffect(() => {
    optionsRef.current = options;
  }, [options]);

  const instanceRef = useRef<MicVAD | null>(null);
  const [loading, setLoading] = useState(true);
  const [listening, setListening] = useState(false);
  const [errored, setErrored] = useState<string | null>(null);

  const model = options.model ?? 'legacy';
  const setupKey = [
    model,
    options.baseAssetPath ?? '',
    options.onnxWASMBasePath ?? '',
    options.processorType ?? '',
  ].join('|');

  useEffect(() => {
    let canceled = false;
    let instance: MicVAD | null = null;

    const setup = async () => {
      try {
        setLoading(true);
        setErrored(null);

        const currentOptions = optionsRef.current;
        instance = await MicVAD.new({
          ...currentOptions,
          onFrameProcessed: (probabilities, frame) => currentOptions.onFrameProcessed?.(probabilities, frame),
          onVADMisfire: () => optionsRef.current.onVADMisfire?.(),
          onSpeechStart: () => optionsRef.current.onSpeechStart?.(),
          onSpeechEnd: (audio) => optionsRef.current.onSpeechEnd?.(audio),
          onSpeechRealStart: () => optionsRef.current.onSpeechRealStart?.(),
        });

        if (canceled) {
          await safelyDestroy(instance);
          return;
        }

        instanceRef.current = instance;
        setLoading(false);
      } catch (error) {
        if (canceled) return;
        setLoading(false);
        setErrored(errorMessage(error));
      }
    };

    void setup();

    return () => {
      canceled = true;
      if (instanceRef.current === instance) instanceRef.current = null;
      if (instance) void safelyDestroy(instance);
      setListening(false);
    };
  }, [setupKey]);

  const start = useCallback(async () => {
    const instance = instanceRef.current;
    if (!instance || errored) return;
    await instance.start();
    setListening(instance.listening);
  }, [errored]);

  const pause = useCallback(async () => {
    const instance = instanceRef.current;
    if (!instance) return;
    try {
      await instance.pause();
    } catch (error) {
      if (!isNullAudioError(error)) throw error;
    } finally {
      setListening(false);
    }
  }, []);

  const toggle = useCallback(async () => {
    if (listening) await pause();
    else await start();
  }, [listening, pause, start]);

  return { loading, listening, errored, start, pause, toggle };
}
