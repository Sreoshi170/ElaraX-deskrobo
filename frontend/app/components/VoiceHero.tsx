import React, { FormEvent, KeyboardEvent } from 'react';
import { LanguagePreference } from '../lib/aether-api';
import { UiLanguage, UiVoiceMode, getUiCopy } from '../lib/i18n';

type VoiceMode = UiVoiceMode;

export type VoiceHeroProps = {
  dateLabel: string;
  timeLabel: string;
  hour: number;
  input: string;
  setInput: (value: string) => void;
  handleSubmit: (event: FormEvent) => void;
  handleKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
  busy: boolean;
  voiceState: 'idle' | 'listening' | 'transcribing';
  voiceMode: VoiceMode;
  wakeUsesRecorderFallback: boolean;
  toggleVoiceCommand: () => Promise<void>;
  languagePreference: LanguagePreference;
  setLanguagePreference: (value: LanguagePreference) => void;
  language: UiLanguage;
};

export default function VoiceHero({
  dateLabel,
  timeLabel,
  hour,
  input,
  setInput,
  handleSubmit,
  handleKeyDown,
  busy,
  voiceState,
  voiceMode,
  wakeUsesRecorderFallback,
  toggleVoiceCommand,
  languagePreference,
  setLanguagePreference,
  language,
}: VoiceHeroProps) {
  const copy = getUiCopy(language);
  const activeVoiceCopy = copy.voice[voiceMode];

  return (
    <>
      <section className="welcome" id="command">
        <div>
          <p className="eyebrow">{dateLabel}</p>
          <h1>{copy.welcome.greeting('Hazra', hour)}</h1>
          <p>{copy.welcome.clear}</p>
        </div>
        <div className="welcome-time">
          <strong>{timeLabel}</strong>
          <span>{copy.welcome.timezone}</span>
        </div>
      </section>

      <form className={`voice-hero voice-${voiceMode}`} onSubmit={handleSubmit} aria-label={copy.input.aria}>
        <div className="voice-field" aria-hidden="true">
          <div className="field-ring ring-one" />
          <div className="field-ring ring-two" />
          <div className="field-ring ring-three" />
          <div className="field-core"><span /></div>
          <div className="field-bars"><i /><i /><i /><i /><i /></div>
        </div>
        <div className="voice-panel">
          <div className="voice-status-row">
            <span className="voice-kicker">{activeVoiceCopy.eyebrow}</span>
            <span className="voice-mode-readout">
              {voiceMode === 'armed' 
                ? (wakeUsesRecorderFallback ? copy.input.mode.cloudFallback : copy.input.mode.localWake)
                : voiceMode === 'idle' ? copy.input.mode.voiceFirst : activeVoiceCopy.eyebrow}
            </span>
          </div>
          <h2>{activeVoiceCopy.title}</h2>
          <p className="voice-description">{activeVoiceCopy.description}</p>
          <div className="command-input-shell">
            <label className="command-copy">
              <span>{copy.input.type}</span>
              <textarea 
                value={input} 
                onChange={(event) => setInput(event.target.value)} 
                onKeyDown={handleKeyDown} 
                placeholder={copy.input.placeholder}
                rows={1} 
                disabled={busy || voiceState !== 'idle'} 
                aria-label={copy.input.type}
              />
            </label>
            <div className="command-actions">
              <button 
                type="button" 
                className={`voice-button${voiceState === 'listening' ? ' listening' : ''}`} 
                onClick={() => void toggleVoiceCommand()} 
                disabled={busy || voiceState === 'transcribing'} 
                aria-label={voiceState === 'listening' ? copy.input.stop : copy.input.speak}
                aria-pressed={voiceState === 'listening'}
              >
                <span aria-hidden="true">{voiceState === 'listening' ? copy.input.stop : copy.input.speak}</span>
              </button>
              <button type="submit" className="send-button" disabled={!input.trim() || busy || voiceState !== 'idle'}>
                {copy.input.send}
              </button>
            </div>
          </div>
          <div className="voice-language-hint">
            <label htmlFor="language-preference">{copy.input.language}</label>
            <select
              id="language-preference"
              value={languagePreference}
              onChange={(event) => setLanguagePreference(event.target.value as LanguagePreference)}
              aria-label={copy.input.responseLanguage}
            >
              <option value="auto">{copy.input.mode.auto}</option>
              <option value="en">{copy.input.mode.en}</option>
              <option value="hi">{copy.input.mode.hi}</option>
              <option value="bn">{copy.input.mode.bn}</option>
              <option value="mixed">{copy.input.mode.mixed}</option>
            </select>
          </div>
        </div>
      </form>
    </>
  );
}
