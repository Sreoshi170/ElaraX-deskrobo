'use client';

import { FormEvent, KeyboardEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ActionItem,
  AuthSession,
  ChatResult,
  DashboardData,
  EmailResult,
  GoogleConnectionStatus,
  InvoiceAutomationStatus,
  LanguagePreference,
  Overview,
  PendingAction,
  ResearchReport,
  confirmAction,
  completeActionItem,
  disconnectGoogle,
  getGoogleStatus,
  getCurrentUser,
  getDashboard,
  getInvoiceAutomationStatus,
  getOverview,
  listActionItems,
  launchGoogleConnection,
  sendChat,
  signOut,
  setInvoiceAutomationEnabled,
  synthesizeVoice,
  transcribeVoice,
} from './lib/aether-api';
import { utils } from '@ricky0123/vad-web';
import Sidebar, { WorkspaceView } from './components/Sidebar';
import Topbar from './components/Topbar';
import VoiceHero from './components/VoiceHero';
import ConversationPanel from './components/ConversationPanel';
import BusinessResearchForm from './components/BusinessResearchForm';
import AuthPage from './components/AuthPage';
import ConnectionsStrip from './components/ConnectionsStrip';
import ContextRail from './components/ContextRail';
import DashboardPanel from './components/DashboardPanel';
import { useSafeMicVAD } from './lib/safe-vad';
import * as ort from 'onnxruntime-web';

const onnxWasmBasePath = process.env.NODE_ENV === 'development'
  ? '/node_modules/onnxruntime-web/dist/'
  : '/';

if (typeof window !== 'undefined') {
  ort.env.wasm.wasmPaths = onnxWasmBasePath;
}

import {
  extractWakeCommand,
  findWakePhrase,
  isEmergencyStopCommand,
  selectVoiceTranscriptAlternative,
  shouldUseWakeRecorderFallback,
} from './lib/wake-phrase';
import {
  BrowserSpeechRecognition,
  BrowserSpeechRecognitionEvent,
  getSpeechRecognitionConstructor,
  SpeechRecognitionConstructor,
  enqueueWakeClip,
} from './lib/wake-listener';
import { UiLanguage, getUiCopy, localeForUiLanguage, uiLanguageFor } from './lib/i18n';

type ConversationMessage = {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  intent?: string;
  risk?: string | null;
  language?: string | null;
  emails?: EmailResult[];
  agentMode?: 'deterministic' | 'gemini';
  taskCount?: number;
  showEmailResults?: boolean;
  research?: ResearchReport | null;
};

type PendingConfirmation = { threadId: string; action: PendingAction };
type VoiceState = 'idle' | 'listening' | 'transcribing';
type TtsState = 'idle' | 'loading' | 'playing';
type WakeState = 'off' | 'starting' | 'armed' | 'heard';
type VoiceMode = 'idle' | 'armed' | 'heard' | 'listening' | 'thinking' | 'speaking';
type SpeechLanguage = 'en' | 'bn' | 'hi' | 'mixed';

const BROWSER_VOICE_NAMES: Record<SpeechLanguage, string[]> = {
  en: ['prabhat', 'ravi', 'neerja'],
  bn: ['bashkar', 'tanishaa'],
  hi: ['madhur', 'swara'],
  mixed: ['prabhat', 'ravi', 'neerja'],
};

const BROWSER_VOICE_LOCALES: Record<SpeechLanguage, string> = {
  en: 'en-IN',
  bn: 'bn-IN',
  hi: 'hi-IN',
  mixed: 'en-IN',
};

function normalizeSpeechLanguage(language?: string | null): SpeechLanguage {
  const normalized = (language || '').trim().toLocaleLowerCase();
  if (normalized.startsWith('bn')) return 'bn';
  if (normalized.startsWith('hi')) return 'hi';
  if (normalized === 'mixed') return 'mixed';
  return 'en';
}

function selectBrowserVoice(language: SpeechLanguage): SpeechSynthesisVoice | undefined {
  const voices = window.speechSynthesis.getVoices();
  const sortedVoices = voices
    .slice()
    .sort((left, right) => left.name.localeCompare(right.name) || left.voiceURI.localeCompare(right.voiceURI));
  const preferredNames = BROWSER_VOICE_NAMES[language];
  const preferredVoice = sortedVoices.find((voice) => preferredNames.some((name) => voice.name.toLocaleLowerCase().includes(name)));
  if (preferredVoice) return preferredVoice;
  const locale = BROWSER_VOICE_LOCALES[language].toLocaleLowerCase();
  return sortedVoices.find((voice) => voice.lang.toLocaleLowerCase() === locale || voice.lang.toLocaleLowerCase().startsWith(`${locale}-`))
    || sortedVoices[0];
}

function createMessage(role: ConversationMessage['role'], text: string, result?: ChatResult): ConversationMessage {
  const emailResultIntents = new Set([
    'CHECK_EMAIL',
    'READ_EMAIL',
    'READ_UNREAD_EMAILS',
    'FIND_EMAIL',
    'PRIORITIZE_EMAILS',
    'GET_URGENT_EMAILS',
  ]);
  const showEmailResults = Boolean(
    result?.emails?.length
      && (emailResultIntents.has(result.intent) || result.task_results?.some((task) => task.intent && emailResultIntents.has(task.intent))),
  );
  return {
    id: crypto.randomUUID(),
    role,
    text,
    intent: result?.intent,
    risk: result?.risk_level,
    language: result?.input_language,
    emails: result?.emails,
    agentMode: result?.agent_mode,
    taskCount: result?.task_results?.length,
    showEmailResults,
    research: result?.research_report ?? result?.data?.research ?? null,
  };
}

function AssistantWorkspace({ session, onSignOut }: { session: AuthSession; onSignOut: () => void }) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [pending, setPending] = useState<PendingConfirmation>();
  const [overview, setOverview] = useState<Overview>();
  const [googleStatus, setGoogleStatus] = useState<GoogleConnectionStatus>();
  const [googleConnecting, setGoogleConnecting] = useState(false);
  const [invoiceAutomation, setInvoiceAutomation] = useState<InvoiceAutomationStatus>();
  const [invoiceAutomationUpdating, setInvoiceAutomationUpdating] = useState(false);
  const [actionItems, setActionItems] = useState<ActionItem[]>([]);
  const [dashboard, setDashboard] = useState<DashboardData>();
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [dashboardRefreshing, setDashboardRefreshing] = useState(false);
  const [completingActionItemId, setCompletingActionItemId] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [voiceState, setVoiceState] = useState<VoiceState>('idle');
  const [wakeEnabled, setWakeEnabled] = useState(false);
  const [wakeState, setWakeState] = useState<WakeState>('off');
  const [wakeUsesRecorderFallback, setWakeUsesRecorderFallback] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(true);
  // Keep the initial value identical on the server and browser. Reading localStorage
  // during the initial state calculation makes the first client render diverge from
  // SSR whenever the user has a saved language preference, which triggers hydration
  // errors. Restore and persist the preference only after hydration completes.
  const [languagePreference, setLanguagePreference] = useState<LanguagePreference>('auto');
  const [uiLanguage, setUiLanguage] = useState<UiLanguage>('en');
  const [ttsState, setTtsState] = useState<TtsState>('idle');
  const [lastAssistantText, setLastAssistantText] = useState('');
  const [focusMode, setFocusMode] = useState(false);
  const [activeView, setActiveView] = useState<WorkspaceView>('home');
  const [notice, setNotice] = useState<string>();
  const [clock, setClock] = useState<Date>(() => new Date(0));
  const googleConnectedRef = useRef(false);
  const endRef = useRef<HTMLDivElement>(null);
  const voiceRecorderRef = useRef<MediaRecorder | undefined>(undefined);
  const voiceStreamRef = useRef<MediaStream | undefined>(undefined);
  const voiceChunksRef = useRef<Blob[]>([]);
  const voiceTimeoutRef = useRef<number | undefined>(undefined);
  const nativeWakeRecognitionRef = useRef<BrowserSpeechRecognition | undefined>(undefined);
  const nativeWakeRestartRef = useRef<number | undefined>(undefined);
  const startNativeWakeRecognitionRef = useRef<(() => void) | undefined>(undefined);
  const disableWakePhraseRef = useRef<((noticeText?: string) => void) | undefined>(undefined);
  const speechRecognitionConstructorRef = useRef<SpeechRecognitionConstructor | undefined>(undefined);
  const wakeRecorderFallbackRef = useRef(false);
  const commandVADActiveRef = useRef(false);
  const fallbackWakeQueueRef = useRef<Promise<void>>(Promise.resolve());
  const wakeEnabledRef = useRef(false);
  const processVoiceTranscriptRef = useRef<((transcript: string) => Promise<void>) | undefined>(undefined);
  const startVoiceRecordingRef = useRef<((fromWakePhrase?: boolean) => Promise<void>) | undefined>(undefined);
  const busyRef = useRef(false);
  const voiceStateRef = useRef<VoiceState>('idle');
  const threadIdRef = useRef<string | undefined>(undefined);
  const pendingRef = useRef<PendingConfirmation | undefined>(undefined);
  const ttsEnabledRef = useRef(true);
  const speechLanguageRef = useRef<SpeechLanguage>('en');
  const ttsAudioRef = useRef<HTMLAudioElement | undefined>(undefined);
  const ttsUrlRef = useRef<string | undefined>(undefined);
  const ttsRequestRef = useRef(0);
  const languagePreferenceRestoredRef = useRef(false);
  const copy = getUiCopy(uiLanguage);

  const handleLanguagePreferenceChange = useCallback((value: LanguagePreference) => {
    setLanguagePreference(value);
    setUiLanguage(uiLanguageFor(value));
  }, []);

  const refreshGoogleData = useCallback(async () => {
    try {
      const [nextOverview, nextStatus, nextInvoiceAutomation, nextActionItems] = await Promise.all([
        getOverview(),
        getGoogleStatus(),
        getInvoiceAutomationStatus(),
        listActionItems(),
      ]);
      const isConnected = Boolean(nextStatus.connected);
      if (isConnected && !googleConnectedRef.current) {
        setMessages([]);
        setInput('');
        threadIdRef.current = undefined;
        pendingRef.current = undefined;
        setPending(undefined);
      }
      googleConnectedRef.current = isConnected;
      setOverview(nextOverview);
      setGoogleStatus(nextStatus);
      setInvoiceAutomation(nextInvoiceAutomation);
      setActionItems(nextActionItems);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'The local ElaraX backend is unavailable.');
    }
  }, []);

  const refreshDashboard = useCallback(async (silent = false) => {
    if (!silent) setDashboardLoading(true);
    setDashboardRefreshing(true);
    try {
      const nextDashboard = await getDashboard();
      setDashboard(nextDashboard);
      setOverview(nextDashboard.overview);
      setGoogleStatus(nextDashboard.google);
      setInvoiceAutomation(nextDashboard.invoice_automation);
      setActionItems(nextDashboard.action_items.filter((item) => item.status === 'open'));
    } catch (error) {
      if (!silent) setNotice(error instanceof Error ? error.message : 'The live dashboard is unavailable.');
    } finally {
      setDashboardLoading(false);
      setDashboardRefreshing(false);
    }
  }, []);

  useEffect(() => {
    // This effect synchronizes the UI with the external local backend after mount.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refreshGoogleData();
    const initialClock = window.setTimeout(() => setClock(new Date()), 0);
    const timer = window.setInterval(() => setClock(new Date()), 30_000);
    const handleGoogleMessage = (event: MessageEvent) => {
      if (event.origin !== 'http://localhost:8000' || event.data?.type !== 'aetherbot-google-auth') return;
      void refreshGoogleData();
      setNotice(event.data.status === 'connected'
        ? copy.notices.googleConnected
        : copy.notices.googleWaiting);
    };
    window.addEventListener('message', handleGoogleMessage);
    return () => {
      window.clearTimeout(initialClock);
      window.clearInterval(timer);
      window.removeEventListener('message', handleGoogleMessage);
    };
  }, [copy.notices.googleConnected, copy.notices.googleWaiting, refreshGoogleData]);

  useEffect(() => {
    // The dashboard effect subscribes to the live backend and starts its first refresh.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refreshDashboard();
    const dashboardTimer = window.setInterval(() => void refreshDashboard(true), 15_000);
    return () => window.clearInterval(dashboardTimer);
  }, [refreshDashboard]);

  useEffect(() => {
    // Deferring this to the next task keeps the first client render identical to
    // the server-rendered English fallback while still restoring a saved choice.
    const restoreTimer = window.setTimeout(() => {
      const saved = window.localStorage.getItem('elarax-language-preference');
      if (saved === 'en' || saved === 'hi' || saved === 'bn' || saved === 'mixed') {
        handleLanguagePreferenceChange(saved);
      }
      languagePreferenceRestoredRef.current = true;
    }, 0);
    return () => window.clearTimeout(restoreTimer);
  }, [handleLanguagePreferenceChange]);

  useEffect(() => {
    if (!languagePreferenceRestoredRef.current) return;
    window.localStorage.setItem('elarax-language-preference', languagePreference);
  }, [languagePreference]);

  useEffect(() => () => {
    if (voiceTimeoutRef.current) window.clearTimeout(voiceTimeoutRef.current);
    if (nativeWakeRestartRef.current) window.clearTimeout(nativeWakeRestartRef.current);
    wakeEnabledRef.current = false;
    nativeWakeRecognitionRef.current?.abort();
    nativeWakeRecognitionRef.current = undefined;
    const recorder = voiceRecorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      recorder.ondataavailable = null;
      recorder.onstop = null;
      recorder.stop();
    }
    voiceStreamRef.current?.getTracks().forEach((track) => track.stop());
    ttsRequestRef.current += 1;
    ttsAudioRef.current?.pause();
    if (ttsUrlRef.current) URL.revokeObjectURL(ttsUrlRef.current);
    window.speechSynthesis?.cancel();
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
      block: 'nearest',
    });
  }, [messages, pending]);

  const locale = localeForUiLanguage(uiLanguage);
  const dateLabel = useMemo(() => clock.getTime() === 0 ? copy.welcome.today : clock.toLocaleDateString(locale, { weekday: 'long', day: 'numeric', month: 'long' }), [clock, copy.welcome.today, locale]);
  const timeLabel = useMemo(() => clock.getTime() === 0 ? '--:--' : clock.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit', hour12: false }), [clock, locale]);
  const greetingHour = clock.getTime() === 0 ? new Date().getHours() : clock.getHours();

  const stopSpeaking = () => {
    ttsRequestRef.current += 1;
    ttsAudioRef.current?.pause();
    ttsAudioRef.current = undefined;
    if (ttsUrlRef.current) URL.revokeObjectURL(ttsUrlRef.current);
    ttsUrlRef.current = undefined;
    window.speechSynthesis?.cancel();
    setTtsState('idle');
  };

  const speakWithBrowserFallback = (text: string, language: SpeechLanguage) => {
    if (!('speechSynthesis' in window)) {
      setTtsState('idle');
      setNotice(copy.notices.speechUnavailable);
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text.slice(0, 3_000));
    const voice = selectBrowserVoice(language);
    utterance.voice = voice ?? null;
    utterance.lang = voice?.lang || BROWSER_VOICE_LOCALES[language];
    utterance.rate = 0.96;
    utterance.pitch = 1;
    utterance.onstart = () => setTtsState('playing');
    utterance.onend = () => setTtsState('idle');
    utterance.onerror = () => setTtsState('idle');
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  };

  const speakAssistantResponse = async (text: string, force = false, language?: string | null) => {
    const cleanText = text.trim();
    setLastAssistantText(cleanText);
    if (!cleanText || (!ttsEnabledRef.current && !force)) return;
    const speechLanguage = normalizeSpeechLanguage(language || speechLanguageRef.current);
    speechLanguageRef.current = speechLanguage;
    stopSpeaking();
    const requestId = ++ttsRequestRef.current;
    setTtsState('loading');
    let generatedAudioUrl: string | undefined;
    const releaseGeneratedAudio = () => {
      if (!generatedAudioUrl) return;
      if (ttsUrlRef.current === generatedAudioUrl) {
        ttsUrlRef.current = undefined;
        ttsAudioRef.current = undefined;
      }
      URL.revokeObjectURL(generatedAudioUrl);
      generatedAudioUrl = undefined;
    };
    try {
      const audioBlob = await synthesizeVoice(cleanText, speechLanguage);
      if (requestId !== ttsRequestRef.current) return;
      const audioUrl = URL.createObjectURL(audioBlob);
      generatedAudioUrl = audioUrl;
      const audio = new Audio(audioUrl);
      ttsUrlRef.current = audioUrl;
      ttsAudioRef.current = audio;
      audio.onplay = () => setTtsState('playing');
      audio.onended = () => {
        releaseGeneratedAudio();
        setTtsState('idle');
      };
      audio.onerror = () => {
        releaseGeneratedAudio();
        if (requestId === ttsRequestRef.current) speakWithBrowserFallback(cleanText, speechLanguage);
      };
      await audio.play();
    } catch {
      releaseGeneratedAudio();
      if (requestId === ttsRequestRef.current) speakWithBrowserFallback(cleanText, speechLanguage);
    }
  };

  const submitEmergencyStop = async (command: string, inputSource: 'typed' | 'voice' = 'typed') => {
    const ownsBusyState = !busyRef.current;
    if (ownsBusyState) {
      busyRef.current = true;
      setBusy(true);
    }
    stopSpeaking();
    setNotice(copy.notices.emergencySent);
    setInput('');
    try {
      const result = await sendChat(command, undefined, inputSource, languagePreference, session.user.id);
      if (languagePreference === 'auto' || languagePreference === 'mixed') {
        setUiLanguage(uiLanguageFor(languagePreference, result.response_language ?? result.input_language));
      }
      setMessages((current) => [...current, createMessage('user', command), createMessage('assistant', result.response, result)]);
      void speakAssistantResponse(result.response, false, result.response_language ?? result.input_language);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : copy.notices.emergencyFailed);
    } finally {
      if (ownsBusyState) {
        busyRef.current = false;
        setBusy(false);
      }
    }
  };

  const submitCommand = async (command: string, inputSource: 'typed' | 'voice' = 'typed') => {
    const cleanCommand = command.trim();
    if (!cleanCommand) return;
    if (isEmergencyStopCommand(cleanCommand)) {
      await submitEmergencyStop(cleanCommand, inputSource);
      return;
    }
    if (busyRef.current) {
      if (cleanCommand && busyRef.current) setNotice(copy.notices.busy);
      return;
    }
    busyRef.current = true;
    setBusy(true);
    setNotice(undefined);
    pendingRef.current = undefined;
    setPending(undefined);
    setInput('');
    setMessages((current) => [...current, createMessage('user', cleanCommand)]);
    try {
      const result = await sendChat(cleanCommand, threadIdRef.current, inputSource, languagePreference, session.user.id);
      if (languagePreference === 'auto' || languagePreference === 'mixed') {
        setUiLanguage(uiLanguageFor(languagePreference, result.response_language ?? result.input_language));
      }
      threadIdRef.current = result.thread_id;
      setMessages((current) => [...current, createMessage('assistant', result.response, result)]);
      if (result.mode === 'backend') {
        void listActionItems().then(setActionItems);
      }
      if (result.requires_confirmation && result.pending_action) {
        const nextPending = { threadId: result.thread_id, action: result.pending_action };
        pendingRef.current = nextPending;
        setPending(nextPending);
      }
      void speakAssistantResponse(result.response, false, result.response_language ?? result.input_language);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : copy.notices.requestFailed);
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    void submitCommand(input);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      void submitCommand(input);
    }
  };

  const handleConfirmation = async (decision: 'approve' | 'reject') => {
    const currentPending = pendingRef.current;
    if (!currentPending || busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    try {
      const result = await confirmAction(currentPending.threadId, decision);
      pendingRef.current = undefined;
      setPending(undefined);
      setMessages((current) => [...current, createMessage('assistant', result.response)]);
      void speakAssistantResponse(result.response, false, languagePreference);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : copy.notices.confirmationFailed);
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  };

  const toggleSpokenResponses = () => {
    if (ttsEnabled) {
      stopSpeaking();
      ttsEnabledRef.current = false;
      setTtsEnabled(false);
      setNotice(copy.notices.muted);
    } else {
      ttsEnabledRef.current = true;
      setTtsEnabled(true);
      setNotice(copy.notices.speechEnabled);
      if (lastAssistantText) void speakAssistantResponse(lastAssistantText, true);
    }
  };

  const voiceConfirmationDecision = (transcript: string): 'approve' | 'reject' | undefined => {
    const normalized = transcript.toLocaleLowerCase().trim();
    if (/\b(?:cancel|reject|no|nope|stop|don'?t)\b|(?:না|नहीं)/i.test(normalized)) return 'reject';
    if (/\b(?:approve|confirm|yes|send it|mail it|do it|proceed)\b|(?:হ্যাঁ|हाँ|মঞ্জুর)/i.test(normalized)) return 'approve';
    return undefined;
  };

  const processVoiceTranscript = async (transcript: string) => {
    const cleanTranscript = transcript.trim();
    if (!cleanTranscript) throw new Error('I could not hear a command. Please try again.');
    if (isEmergencyStopCommand(cleanTranscript)) {
      await submitEmergencyStop(cleanTranscript, 'voice');
      return;
    }
    setInput(cleanTranscript);
    const currentPending = pendingRef.current;
    const decision = currentPending ? voiceConfirmationDecision(cleanTranscript) : undefined;
    if (currentPending && decision) {
      setMessages((current) => [...current, createMessage('user', cleanTranscript)]);
      await handleConfirmation(decision);
    } else {
      await submitCommand(cleanTranscript, 'voice');
    }
  };

  const stopVoiceRecording = () => {
    if (voiceTimeoutRef.current) window.clearTimeout(voiceTimeoutRef.current);
    const recorder = voiceRecorderRef.current;
    if (recorder && recorder.state !== 'inactive') recorder.stop();
  };

  const startVoiceRecording = async (fromWakePhrase = false) => {
    if (voiceStateRef.current === 'listening') return;
    if (busyRef.current || voiceStateRef.current === 'transcribing') return;
    processVoiceTranscriptRef.current = processVoiceTranscript;
    startVoiceRecordingRef.current = startVoiceRecording;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setNotice(copy.notices.recordingUnsupported);
      return;
    }
    try {
      stopSpeaking();
      const commandVADNeeded = fromWakePhrase && wakeEnabledRef.current;
      if (commandVADNeeded) {
        commandVADActiveRef.current = true;
        if (!wakeRecorderFallbackRef.current && !vad.listening) await vad.start();
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
      const preferredTypes = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
      const mimeType = preferredTypes.find((type) => MediaRecorder.isTypeSupported(type));
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      voiceStreamRef.current = stream;
      voiceRecorderRef.current = recorder;
      voiceChunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) voiceChunksRef.current.push(event.data);
      };
      recorder.onerror = () => {
        stream.getTracks().forEach((track) => track.stop());
        commandVADActiveRef.current = false;
        if (!wakeRecorderFallbackRef.current) void vad.pause();
        voiceStateRef.current = 'idle';
        setVoiceState('idle');
        setNotice(copy.notices.recordingFailed);
      };
      recorder.onstop = async () => {
        if (voiceTimeoutRef.current) window.clearTimeout(voiceTimeoutRef.current);
        stream.getTracks().forEach((track) => track.stop());
        voiceRecorderRef.current = undefined;
        voiceStreamRef.current = undefined;
        const shouldResumeNativeWake = wakeEnabledRef.current && !wakeRecorderFallbackRef.current;
        commandVADActiveRef.current = false;
        if (shouldResumeNativeWake) await vad.pause();
        const recording = new Blob(voiceChunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        voiceChunksRef.current = [];
        if (recording.size < 512) {
          voiceStateRef.current = 'idle';
          setVoiceState('idle');
          setNotice(fromWakePhrase ? copy.notices.noAudioAfterWake : copy.notices.noAudio);
          if (shouldResumeNativeWake) startNativeWakeRecognitionRef.current?.();
          return;
        }
        voiceStateRef.current = 'transcribing';
        setVoiceState('transcribing');
        setNotice(copy.notices.transcribing);
        try {
          const result = await transcribeVoice(recording, languagePreference);
          await processVoiceTranscriptRef.current?.(result.transcript);
        } catch (error) {
          setNotice(error instanceof Error ? error.message : copy.notices.voiceFailed);
        } finally {
          voiceStateRef.current = 'idle';
          setVoiceState('idle');
          if (wakeEnabledRef.current) setWakeState('armed');
          if (shouldResumeNativeWake) startNativeWakeRecognitionRef.current?.();
        }
      };
      recorder.start(250);
      voiceStateRef.current = 'listening';
      setVoiceState('listening');
      setNotice(fromWakePhrase ? copy.notices.wakeListening : copy.notices.listening);
      voiceTimeoutRef.current = window.setTimeout(stopVoiceRecording, 15_000);
    } catch (error) {
      commandVADActiveRef.current = false;
      if (!wakeRecorderFallbackRef.current) void vad.pause();
      voiceStateRef.current = 'idle';
      setVoiceState('idle');
      setNotice(error instanceof DOMException && error.name === 'NotAllowedError' ? copy.notices.micDenied : copy.notices.micFailed);
    }
  };

  const toggleVoiceCommand = async () => {
    if (voiceStateRef.current === 'listening') {
      stopVoiceRecording();
      return;
    }
    await startVoiceRecording();
  };

  const vad = useSafeMicVAD({
    startOnLoad: false,
    baseAssetPath: '/',
    onnxWASMBasePath: onnxWasmBasePath,
    model: 'v5',
    onSpeechStart: () => {
      if (wakeRecorderFallbackRef.current && wakeEnabledRef.current && !commandVADActiveRef.current && !busyRef.current && voiceStateRef.current === 'idle') {
        setWakeState('heard');
        setNotice(copy.notices.wakeDetected);
      }
    },
    onSpeechEnd: async (audio) => {
      if (commandVADActiveRef.current && voiceStateRef.current === 'listening') {
        commandVADActiveRef.current = false;
        stopVoiceRecording();
        return;
      }
      if (!wakeRecorderFallbackRef.current || busyRef.current || voiceStateRef.current !== 'idle') return;
      fallbackWakeQueueRef.current = enqueueWakeClip(fallbackWakeQueueRef.current, async () => {
        if (!wakeEnabledRef.current || busyRef.current || voiceStateRef.current !== 'idle') return;
        try {
          const wavBuffer = utils.encodeWAV(audio);
          const blob = new Blob([wavBuffer], { type: 'audio/wav' });
          voiceStateRef.current = 'transcribing';
          setVoiceState('transcribing');
          setNotice(copy.notices.checkingWake);
          const result = await transcribeVoice(blob, languagePreference);
          const command = extractWakeCommand(result.transcript);
          if (command !== undefined) {
            setNotice(command ? `${copy.notices.wakeListening} “${command}”` : copy.notices.wakeListening);
            if (command) {
              await processVoiceTranscriptRef.current?.(command);
              setWakeState('armed');
            } else {
              voiceStateRef.current = 'idle';
              setVoiceState('idle');
              await startVoiceRecordingRef.current?.(true);
            }
          } else {
            setWakeState('armed');
            setNotice(copy.notices.wakeListening);
          }
        } catch (error) {
          setWakeState('armed');
          const detail = error instanceof Error ? ` (${error.message})` : '';
          setNotice(copy.notices.wakeClipFailed(detail));
        } finally {
          if (voiceStateRef.current === 'transcribing') {
            voiceStateRef.current = 'idle';
            setVoiceState('idle');
          }
        }
      });
    },
  });

  useEffect(() => {
    if (vad.errored && wakeEnabledRef.current && wakeRecorderFallbackRef.current) {
      setWakeState('off');
      setWakeEnabled(false);
      wakeEnabledRef.current = false;
      const message = String((vad.errored as { message?: string })?.message || vad.errored);
      setNotice(copy.notices.wakeDisabled(message));
    }
  }, [copy.notices, vad.errored]);

  const disableWakePhrase = (noticeText = copy.status.wakeOff) => {
    wakeEnabledRef.current = false;
    wakeRecorderFallbackRef.current = false;
    setWakeUsesRecorderFallback(false);
    commandVADActiveRef.current = false;
    if (nativeWakeRestartRef.current) window.clearTimeout(nativeWakeRestartRef.current);
    nativeWakeRestartRef.current = undefined;
    nativeWakeRecognitionRef.current?.abort();
    nativeWakeRecognitionRef.current = undefined;
    vad.pause();
    setWakeEnabled(false);
    setWakeState('off');
    setNotice(noticeText);
  };

  const playWakeCue = () => {
    try {
      const AudioContextConstructor = window.AudioContext || (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!AudioContextConstructor) return;
      const context = new AudioContextConstructor();
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(660, context.currentTime);
      oscillator.frequency.exponentialRampToValueAtTime(880, context.currentTime + 0.09);
      gain.gain.setValueAtTime(0.0001, context.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.035, context.currentTime + 0.015);
      gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.12);
      oscillator.connect(gain);
      gain.connect(context.destination);
      oscillator.start();
      oscillator.stop(context.currentTime + 0.13);
      oscillator.addEventListener('ended', () => void context.close(), { once: true });
    } catch {
      // The state change remains useful when a browser blocks the optional cue.
    }
  };

  const scheduleNativeWakeRecognition = () => {
    if (nativeWakeRestartRef.current || !wakeEnabledRef.current || wakeRecorderFallbackRef.current) return;
    nativeWakeRestartRef.current = window.setTimeout(() => {
      nativeWakeRestartRef.current = undefined;
      startNativeWakeRecognitionRef.current?.();
    }, 220);
  };

  const switchToWakeRecorderFallback = async () => {
    if (!wakeEnabledRef.current || wakeRecorderFallbackRef.current) return;
    wakeRecorderFallbackRef.current = true;
    setWakeUsesRecorderFallback(true);
    nativeWakeRecognitionRef.current?.abort();
    nativeWakeRecognitionRef.current = undefined;
    setNotice(copy.notices.localWakeUnavailable);
    try {
      await vad.start();
      setWakeState('armed');
    } catch {
      disableWakePhrase('The microphone listener could not start in this browser.');
    }
  };

  const handleNativeWakeResult = (transcript: string, isFinal: boolean) => {
    const inlineCommand = extractWakeCommand(transcript);
    if (isEmergencyStopCommand(transcript) || (inlineCommand && isEmergencyStopCommand(inlineCommand))) {
      void processVoiceTranscriptRef.current?.(inlineCommand || transcript);
      return;
    }
    if (!wakeEnabledRef.current || busyRef.current || voiceStateRef.current !== 'idle') return;
    setWakeState('heard');
    setNotice(copy.notices.wakeListening);
    playWakeCue();
    if (isFinal && inlineCommand) {
      void processVoiceTranscriptRef.current?.(inlineCommand);
    } else {
      void startVoiceRecordingRef.current?.(true);
    }
  };

  const startNativeWakeRecognition = () => {
    if (!wakeEnabledRef.current || wakeRecorderFallbackRef.current || nativeWakeRecognitionRef.current) return;
    const Recognition = speechRecognitionConstructorRef.current || getSpeechRecognitionConstructor();
    if (!Recognition) {
      void switchToWakeRecorderFallback();
      return;
    }
    speechRecognitionConstructorRef.current = Recognition;
    let recognition: BrowserSpeechRecognition;
    try {
      recognition = new Recognition();
    } catch {
      void switchToWakeRecorderFallback();
      return;
    }
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = languagePreference === 'hi'
      ? 'hi-IN'
      : languagePreference === 'bn'
        ? 'bn-IN'
        : 'en-IN';
    recognition.maxAlternatives = 3;
    recognition.onstart = () => {
      if (wakeEnabledRef.current && voiceStateRef.current === 'idle') setWakeState('armed');
    };
    recognition.onresult = (event: BrowserSpeechRecognitionEvent) => {
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        const alternatives = [];
        for (let alternativeIndex = 0; alternativeIndex < result.length; alternativeIndex += 1) {
          alternatives.push(result[alternativeIndex]);
        }
        const transcript = selectVoiceTranscriptAlternative(alternatives);
        if (!transcript) continue;
        if (isEmergencyStopCommand(transcript)) {
          void processVoiceTranscriptRef.current?.(transcript);
          return;
        }
        if (findWakePhrase(transcript)) {
          handleNativeWakeResult(transcript, result.isFinal);
          return;
        }
      }
    };
    recognition.onerror = (event) => {
      nativeWakeRecognitionRef.current = undefined;
      if (!wakeEnabledRef.current) return;
      if (shouldUseWakeRecorderFallback(event.error)) {
        void switchToWakeRecorderFallback();
        return;
      }
      if (event.error === 'no-speech' || event.error === 'aborted') {
        scheduleNativeWakeRecognition();
        return;
      }
      disableWakePhrase(event.error === 'not-allowed'
        ? 'Microphone permission was denied. Allow access to turn on wake phrases.'
        : 'The local wake listener could not access this microphone.');
    };
    recognition.onend = () => {
      if (nativeWakeRecognitionRef.current === recognition) nativeWakeRecognitionRef.current = undefined;
      if (wakeEnabledRef.current && !wakeRecorderFallbackRef.current && voiceStateRef.current === 'idle' && !busyRef.current) scheduleNativeWakeRecognition();
    };
    nativeWakeRecognitionRef.current = recognition;
    try {
      recognition.start();
    } catch {
      nativeWakeRecognitionRef.current = undefined;
      void switchToWakeRecorderFallback();
    }
  };

  useEffect(() => {
    startNativeWakeRecognitionRef.current = startNativeWakeRecognition;
    disableWakePhraseRef.current = disableWakePhrase;
  });

  const enableWakePhrase = async () => {
    processVoiceTranscriptRef.current = processVoiceTranscript;
    startVoiceRecordingRef.current = startVoiceRecording;
    if (!navigator.mediaDevices?.getUserMedia) {
      setNotice(copy.notices.micAccessUnavailable);
      return;
    }
    setWakeState('starting');
    setNotice(copy.notices.startingListening);
    try {
      const permissionStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      permissionStream.getTracks().forEach((track) => track.stop());
      wakeEnabledRef.current = true;
      setWakeEnabled(true);
      speechRecognitionConstructorRef.current = getSpeechRecognitionConstructor();
      wakeRecorderFallbackRef.current = shouldUseWakeRecorderFallback(speechRecognitionConstructorRef.current ? '' : 'unsupported');
      setWakeUsesRecorderFallback(wakeRecorderFallbackRef.current);
      if (wakeRecorderFallbackRef.current) await vad.start();
      else startNativeWakeRecognition();
      setWakeState('armed');
      setNotice(wakeRecorderFallbackRef.current
        ? copy.status.wakeOn
        : copy.notices.startingListening);
    } catch {
      disableWakePhrase(copy.notices.wakePermissionDenied);
    }
  };

  const toggleWakePhrase = () => {
    if (wakeEnabledRef.current) disableWakePhrase();
    else void enableWakePhrase();
  };

  const handleGoogleConnect = async () => {
    if (googleConnecting) return;
    setGoogleConnecting(true);
    try {
      await launchGoogleConnection();
      setNotice(copy.notices.googleOpened);
      for (let attempt = 0; attempt < 80; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 1_500));
        const status = await getGoogleStatus();
        setGoogleStatus(status);
        if (status.connected) {
          await refreshGoogleData();
          setNotice(copy.notices.googleConnected);
          return;
        }
      }
      setNotice(copy.notices.googleWaiting);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : copy.notices.googleStartFailed);
    } finally {
      setGoogleConnecting(false);
    }
  };

  const handleGoogleDisconnect = async () => {
    if (!window.confirm(copy.notices.googleDisconnectConfirm)) return;
    try {
      const status = await disconnectGoogle();
      setGoogleStatus(status);
      await refreshGoogleData();
      setNotice(copy.notices.googleDisconnected);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : copy.notices.googleDisconnectFailed);
    }
  };

  const handleInvoiceAutomationToggle = async () => {
    if (!invoiceAutomation || invoiceAutomationUpdating) return;
    const nextEnabled = !invoiceAutomation.enabled;
    if (nextEnabled && !window.confirm(copy.notices.invoiceConfirm)) return;
    setInvoiceAutomationUpdating(true);
    try {
      const status = await setInvoiceAutomationEnabled(nextEnabled);
      setInvoiceAutomation(status);
      setNotice(nextEnabled ? copy.notices.invoiceOn : copy.notices.invoicePaused);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : copy.notices.invoiceUpdateFailed);
    } finally {
      setInvoiceAutomationUpdating(false);
    }
  };

  const handleCompleteActionItem = async (itemId: string) => {
    if (completingActionItemId) return;
    setCompletingActionItemId(itemId);
    try {
      await completeActionItem(itemId);
      setActionItems((current) => current.filter((item) => item.id !== itemId));
      void refreshDashboard(true);
      setNotice(copy.notices.actionCompleted);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : copy.notices.actionFailed);
    } finally {
      setCompletingActionItemId(undefined);
    }
  };

  const urgentEmail = overview?.urgent_emails[0];
  const todayEvents = overview?.today_events ?? [];
  const tomorrowEvents = overview?.tomorrow_events ?? [];
  const attentionCount = overview
    ? overview.urgent_emails.length + overview.today_events.length + actionItems.length
    : undefined;
  const isBackendConnected = overview?.mode === 'backend';
  const isGoogleConnected = Boolean(googleStatus?.connected);
  const voiceMode: VoiceMode = voiceState === 'listening'
    ? 'listening'
    : busy || voiceState === 'transcribing'
      ? 'thinking'
      : ttsState !== 'idle'
        ? 'speaking'
        : wakeState === 'heard'
          ? 'heard'
          : wakeEnabled && wakeState === 'armed'
            ? 'armed'
            : 'idle';
  return (
    <main className={`aether-app${focusMode ? ' focus-mode' : ''}`}>
      <Sidebar language={uiLanguage} activeView={activeView} onViewChange={setActiveView} />

      <section className="main-stage">
        <Topbar
          isBackendConnected={isBackendConnected}
          isGoogleConnected={isGoogleConnected}
          googleStatus={googleStatus}
          wakeState={wakeState}
          wakeEnabled={wakeEnabled}
          toggleWakePhrase={toggleWakePhrase}
          ttsState={ttsState}
          ttsEnabled={ttsEnabled}
          toggleSpokenResponses={toggleSpokenResponses}
          lastAssistantText={lastAssistantText}
          speakAssistantResponse={speakAssistantResponse}
          focusMode={focusMode}
          setFocusMode={setFocusMode}
          language={uiLanguage}
          userName={session.user.profile.full_name}
          userOccupation={session.user.profile.occupation}
          onSignOut={onSignOut}
        />

        <div className="stage-content">
          {activeView === 'dashboard' ? <DashboardPanel
            data={dashboard}
            loading={dashboardLoading}
            refreshing={dashboardRefreshing}
            onRefresh={() => void refreshDashboard()}
            onCompleteActionItem={(itemId) => void handleCompleteActionItem(itemId)}
            completingActionItemId={completingActionItemId}
          />
          : <>
          <VoiceHero
            dateLabel={dateLabel}
            timeLabel={timeLabel}
            hour={greetingHour}
            input={input}
            setInput={setInput}
            handleSubmit={handleSubmit}
            handleKeyDown={handleKeyDown}
            busy={busy}
            voiceState={voiceState}
            voiceMode={voiceMode}
            wakeUsesRecorderFallback={wakeUsesRecorderFallback}
            toggleVoiceCommand={toggleVoiceCommand}
            languagePreference={languagePreference}
            setLanguagePreference={handleLanguagePreferenceChange}
            language={uiLanguage}
          />

          {notice && <div className="notice-toast" role="status">{notice}</div>}
          <div className="quick-prompts" aria-label={copy.quickPrompt}>
            {copy.commands.quickPrompts.map((prompt) => (
              <button type="button" key={prompt} onClick={() => void submitCommand(prompt)} disabled={busy}>
                {copy.quickPrompt} {prompt}
              </button>
            ))}
          </div>

          <BusinessResearchForm busy={busy} submitCommand={(command) => void submitCommand(command)} />

          <ConnectionsStrip
            isGoogleConnected={isGoogleConnected}
            googleStatus={googleStatus}
            googleConnecting={googleConnecting}
            handleGoogleConnect={handleGoogleConnect}
            handleGoogleDisconnect={handleGoogleDisconnect}
            invoiceAutomation={invoiceAutomation}
            invoiceAutomationUpdating={invoiceAutomationUpdating}
            handleInvoiceAutomationToggle={handleInvoiceAutomationToggle}
            overview={overview}
            language={uiLanguage}
          />

          <ConversationPanel
            messages={messages}
            pending={pending}
            busy={busy}
            handleConfirmation={handleConfirmation}
            onClear={() => {
              pendingRef.current = undefined;
              threadIdRef.current = undefined;
              setMessages([]);
              setPending(undefined);
            }}
            endRef={endRef}
            language={uiLanguage}
          />
          </>}
        </div>
      </section>

      {activeView === 'home' && <ContextRail
        overview={overview}
        attentionCount={attentionCount}
        urgentEmail={urgentEmail}
        todayEvents={todayEvents}
        tomorrowEvents={tomorrowEvents}
        actionItems={actionItems}
        completingActionItemId={completingActionItemId}
        submitCommand={submitCommand}
        handleCompleteActionItem={handleCompleteActionItem}
        language={uiLanguage}
      />}

      <nav className="mobile-nav" aria-label={copy.nav.aria}>
        <a href="#command" className={activeView === 'home' ? 'active' : ''} onClick={() => setActiveView('home')}><span aria-hidden="true">+</span><span>{copy.nav.home}</span></a>
        <a href="#dashboard" className={activeView === 'dashboard' ? 'active' : ''} onClick={(event) => { event.preventDefault(); setActiveView('dashboard'); }}><span aria-hidden="true">▦</span><span>{copy.nav.dashboard}</span></a>
        <a href="#briefing" onClick={() => setActiveView('home')}><span aria-hidden="true">○</span><span>{copy.nav.today}</span></a>
        <a href="#connections" onClick={() => setActiveView('home')}><span aria-hidden="true">~</span><span>{copy.nav.links}</span></a>
      </nav>
    </main>
  );
}

export default function Home() {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);

  useEffect(() => {
    let mounted = true;
    void getCurrentUser().then((user) => {
      if (!mounted) return;
      if (user) setSession({ access_token: '', token_type: 'bearer', user });
      setCheckingSession(false);
    });
    return () => { mounted = false; };
  }, []);

  if (checkingSession) {
    return <main className="auth-loading"><div className="brand-mark">Elara<span>X</span></div><span>Preparing your workspace…</span></main>;
  }
  if (!session) return <AuthPage onAuthenticated={setSession} />;

  return (
    <AssistantWorkspace
      session={session}
      onSignOut={() => {
        void signOut().finally(() => setSession(null));
      }}
    />
  );
}
