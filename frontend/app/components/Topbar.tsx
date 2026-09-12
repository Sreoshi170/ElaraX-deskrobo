import React from 'react';
import { GoogleConnectionStatus } from '../lib/aether-api';
import { UiLanguage, getUiCopy } from '../lib/i18n';

export type TopbarProps = {
  isBackendConnected: boolean;
  isGoogleConnected: boolean;
  googleStatus?: GoogleConnectionStatus;
  wakeState: 'off' | 'starting' | 'armed' | 'heard';
  wakeEnabled: boolean;
  toggleWakePhrase: () => void;
  ttsState: 'idle' | 'loading' | 'playing';
  ttsEnabled: boolean;
  toggleSpokenResponses: () => void;
  lastAssistantText: string;
  speakAssistantResponse: (text: string, force?: boolean) => void;
  focusMode: boolean;
  setFocusMode: React.Dispatch<React.SetStateAction<boolean>>;
  language: UiLanguage;
  userName?: string;
  userOccupation?: string;
  onSignOut?: () => void;
};

export default function Topbar({
  isBackendConnected,
  isGoogleConnected,
  googleStatus,
  wakeState,
  wakeEnabled,
  toggleWakePhrase,
  ttsState,
  ttsEnabled,
  toggleSpokenResponses,
  lastAssistantText,
  speakAssistantResponse,
  focusMode,
  setFocusMode,
  language,
  userName,
  userOccupation,
  onSignOut,
}: TopbarProps) {
  const copy = getUiCopy(language);
  return (
    <header className="topbar">
      <div className="mobile-brand">Elara<span>X</span></div>
      <div className="system-status">
        <i className={isBackendConnected ? '' : 'demo-dot'} />
        <span>
          {isGoogleConnected 
            ? copy.status.googleConnected(googleStatus?.email)
            : isBackendConnected 
              ? copy.status.ready
              : copy.status.demo}
        </span>
      </div>
      <div className="top-actions">
        {userName && <div className="account-chip" title={userOccupation || undefined}><span>{userName.slice(0, 1).toUpperCase()}</span><strong>{userName}</strong><button type="button" onClick={onSignOut}>Sign out</button></div>}
        <button 
          type="button" 
          className={`wake-toggle wake-${wakeState}${wakeEnabled ? ' active' : ''}`} 
          onClick={toggleWakePhrase} 
          disabled={wakeState === 'starting' && !wakeEnabled} 
          aria-label={wakeEnabled ? copy.status.wakeOn : copy.status.wakeOff}
          aria-pressed={wakeEnabled} 
          title={wakeEnabled ? copy.status.wakeOn : copy.status.wakeOff}
        >
          <i />
          <span>{wakeState === 'starting' ? copy.status.wakeStarting : copy.status.wake}</span>
        </button>
        <button type="button" className="icon-button notification-button" aria-label={copy.status.notifications}>
          <span aria-hidden="true">○</span><b>2</b>
        </button>
        <button 
          type="button" 
          className={`icon-button tts-toggle${ttsState !== 'idle' ? ' active' : ''}`} 
          onClick={toggleSpokenResponses} 
          aria-label={ttsEnabled ? copy.status.mute : copy.status.enableSpeech}
          aria-pressed={ttsEnabled}
        >
          <span aria-hidden="true">{ttsEnabled ? (ttsState === 'loading' ? '...' : '))') : '—)'}</span>
        </button>
        <button 
          type="button" 
          className="icon-button replay-button" 
          onClick={() => lastAssistantText && void speakAssistantResponse(lastAssistantText, true)} 
          disabled={!lastAssistantText || ttsState === 'loading'} 
          aria-label={copy.status.replay}
        >
          <span aria-hidden="true">↻</span>
        </button>
        <button 
          type="button" 
          className={`focus-button${focusMode ? ' active' : ''}`} 
          onClick={() => setFocusMode((value) => !value)} 
          aria-pressed={focusMode}
        >
          <span aria-hidden="true">□</span>{focusMode ? copy.status.exitFocus : copy.status.focus}
        </button>
      </div>
    </header>
  );
}
