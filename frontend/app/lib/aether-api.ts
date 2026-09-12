export type PendingAction = {
  action: string;
  [key: string]: unknown;
};

export type ResearchReport = {
  query: string;
  topic?: string;
  status?: string;
  executive_summary: string;
  market_overview: string;
  key_trends: string[];
  competitors: string[];
  swot: {
    strengths: string[];
    weaknesses: string[];
    opportunities: string[];
    threats: string[];
  };
  sources: Array<{ url: string; title?: string; snippet?: string; source?: string }>;
  warnings?: string[];
  sources_used_count?: number;
  business_profile?: Record<string, string>;
  recommendations?: string[];
  competitive_strategy?: string[];
  risks_and_assumptions?: string[];
  next_steps?: string[];
};

export type EmailResult = {
  id: string;
  thread_id?: string | null;
  sender: string;
  sender_name?: string | null;
  subject: string;
  snippet: string;
  date?: string | null;
  unread?: boolean;
  urgent?: boolean;
};

export type ChatResult = {
  thread_id: string;
  request_id?: string;
  success?: boolean;
  status?: 'completed' | 'waiting_for_confirmation' | 'error';
  intent: string;
  agent?: string;
  intent_confidence: number;
  input_language?: string | null;
  risk_level?: string | null;
  requires_confirmation: boolean;
  pending_action?: PendingAction | null;
  response: string;
  message?: string | null;
  data?: { research?: ResearchReport | null; swot?: ResearchReport['swot'] | null; sources?: ResearchReport['sources']; robot?: Record<string, unknown> | null };
  sources?: ResearchReport['sources'];
  research_report?: ResearchReport | null;
  response_language?: string | null;
  emails?: EmailResult[];
  agent_mode?: 'deterministic' | 'gemini';
  task_results?: Array<{
    intent?: string | null;
    email_count?: number;
    event_count?: number;
    requires_confirmation?: boolean;
    error?: string | null;
  }>;
  mode?: 'backend' | 'demo';
};

export type LanguagePreference = 'auto' | 'en' | 'bn' | 'hi' | 'mixed';

export type ConfirmationResult = {
  thread_id: string;
  decision: 'approved' | 'rejected';
  response: string;
  result?: Record<string, unknown> | null;
  mode?: 'backend' | 'demo';
};

export type VoiceTranscriptionResult = {
  transcript: string;
};

export type VoiceSynthesisResult = {
  audio_base64: string;
  mime_type: string;
};

export type Overview = {
  urgent_emails: EmailResult[];
  today_events: Array<{
    id: string;
    title: string;
    time: string;
    participants: string[];
  }>;
  tomorrow_events: Array<{
    id: string;
    title: string;
    time: string;
    participants: string[];
  }>;
  robot: {
    connected: boolean;
    mode: string;
    motion: string;
  };
  google?: GoogleConnectionStatus;
  provider?: 'google' | 'mock';
  integration_error?: string | null;
  mode?: 'backend' | 'demo';
};

export type GoogleConnectionStatus = {
  configured: boolean;
  connected: boolean;
  email?: string | null;
  scopes: string[];
  expires_at?: string | null;
  error?: string | null;
};

export type InvoiceAutomationStatus = {
  enabled: boolean;
  connected: boolean;
  poll_interval_seconds: number;
  reply_template: string;
  total_replies_sent: number;
  last_run_at?: string | null;
  last_error?: string | null;
  recent_replies: Array<{
    thread_id: string;
    recipient: string;
    subject: string;
    sent_at: string;
  }>;
};

export type ActionItem = {
  id: string;
  description: string;
  due_date?: string | null;
  source_email_id: string;
  source_subject: string;
  status: 'open' | 'done';
  created_at: string;
};

export type DashboardActivity = {
  id: string;
  activity_type: string;
  title: string;
  detail: string;
  status: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type OwnerProgress = {
  profile_setup: number;
  action_completion: number;
  activity_momentum: number;
  active_days: number;
  tracked_days: Array<{ date: string; count: number }>;
  goal: string;
  current_challenge: string;
  next_action: string;
};

export type DashboardData = {
  updated_at: string;
  user: AuthUser;
  overview: Overview;
  action_items: ActionItem[];
  activity: DashboardActivity[];
  google: GoogleConnectionStatus;
  invoice_automation: InvoiceAutomationStatus;
  owner_progress: OwnerProgress;
  health: {
    status: string;
    graph: string;
    mode: string;
    reasoning: string;
    research_retrieval: string;
    research_analysis: string;
  };
  stats: {
    open_action_items: number;
    completed_action_items: number;
    urgent_emails: number;
    today_events: number;
    tomorrow_events: number;
    activity_count: number;
    profile_completion: number;
  };
};

export type UserProfile = {
  full_name: string;
  email: string;
  phone: string;
  country: string;
  timezone: string;
  occupation: string;
  company_name: string;
  website: string;
  industry: string;
  company_size: string;
  business_stage: string;
  business_model: string;
  revenue_model: string;
  products_services: string;
  target_customers: string;
  goals: string;
  challenges: string;
  business_context: string;
};

export type AuthUser = {
  id: string;
  created_at?: string | null;
  updated_at?: string | null;
  profile: UserProfile;
};

export type AuthSession = {
  access_token: string;
  token_type: 'bearer';
  user: AuthUser;
};

export type SignUpInput = UserProfile & { password: string };

const AUTH_TOKEN_KEY = 'elarax-auth-token';

const demoOverview: Overview = {
  urgent_emails: [
    {
      id: 'email-001',
      sender: 'alice@example.com',
      subject: 'Launch review',
      snippet: 'Please review the launch checklist before 3 PM.',
    },
  ],
  today_events: [
    {
      id: 'event-001',
      title: 'Product stand-up',
      time: '10:00 AM',
      participants: ['product@example.com'],
    },
  ],
  tomorrow_events: [
    {
      id: 'event-002',
      title: 'Launch readiness review',
      time: '4:00 PM',
      participants: ['alice@example.com'],
    },
  ],
  robot: { connected: false, mode: 'simulation', motion: 'stopped' },
  mode: 'demo',
};

const wait = (milliseconds: number) =>
  new Promise((resolve) => window.setTimeout(resolve, milliseconds));

function localApiUrl(path: string): string | null {
  if (typeof window === 'undefined') return null;
  return ['localhost', '127.0.0.1'].includes(window.location.hostname)
    ? path
    : null;
}

function authHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const token = window.localStorage.getItem(AUTH_TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function authResponse(response: Response): Promise<AuthSession> {
  const data = await response.json() as AuthSession & { detail?: string };
  if (!response.ok || !data.access_token) {
    throw new Error(data.detail ?? 'Authentication could not be completed.');
  }
  window.localStorage.setItem(AUTH_TOKEN_KEY, data.access_token);
  return data;
}

export async function signUp(input: SignUpInput): Promise<AuthSession> {
  const endpoint = localApiUrl('/api/auth/signup');
  if (!endpoint) throw new Error('Account creation requires the local ElaraX backend.');
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
    signal: AbortSignal.timeout(12_000),
  });
  return authResponse(response);
}

export async function signIn(email: string, password: string): Promise<AuthSession> {
  const endpoint = localApiUrl('/api/auth/signin');
  if (!endpoint) throw new Error('Sign in requires the local ElaraX backend.');
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
    signal: AbortSignal.timeout(12_000),
  });
  return authResponse(response);
}

export async function getCurrentUser(): Promise<AuthUser | null> {
  const endpoint = localApiUrl('/api/auth/me');
  if (!endpoint || typeof window === 'undefined' || !window.localStorage.getItem(AUTH_TOKEN_KEY)) return null;
  try {
    const response = await fetch(endpoint, {
      headers: authHeaders(),
      signal: AbortSignal.timeout(8_000),
    });
    if (!response.ok) {
      window.localStorage.removeItem(AUTH_TOKEN_KEY);
      return null;
    }
    return await response.json() as AuthUser;
  } catch {
    return null;
  }
}

export async function getDashboard(): Promise<DashboardData> {
  const endpoint = localApiUrl('/api/dashboard');
  if (!endpoint) throw new Error('The live dashboard requires the local ElaraX backend.');
  const response = await fetch(endpoint, {
    headers: authHeaders(),
    signal: AbortSignal.timeout(20_000),
  });
  const data = await response.json() as DashboardData & { detail?: string };
  if (!response.ok) throw new Error(data.detail ?? `The dashboard returned HTTP ${response.status}.`);
  return {
    ...data,
    overview: { ...data.overview, mode: 'backend' },
  };
}

export async function signOut(): Promise<void> {
  const endpoint = localApiUrl('/api/auth/signout');
  try {
    if (endpoint) {
      await fetch(endpoint, {
        method: 'POST',
        headers: authHeaders(),
        signal: AbortSignal.timeout(5_000),
      });
    }
  } finally {
    window.localStorage.removeItem(AUTH_TOKEN_KEY);
  }
}

function demoLanguage(message: string): string {
  const hasBengali = /[\u0980-\u09ff]/.test(message);
  const hasHindi = /[\u0900-\u097f]/.test(message);
  const hasEnglish = /[a-z]/i.test(message);
  if ((hasBengali || hasHindi) && hasEnglish) return 'mixed';
  if (hasBengali) return 'bn';
  if (hasHindi) return 'hi';
  return 'en';
}

async function demoChat(message: string, threadId?: string): Promise<ChatResult> {
  await wait(460);
  const text = message.toLocaleLowerCase();
  const base = {
    thread_id: threadId ?? crypto.randomUUID(),
    intent_confidence: 0.95,
    input_language: demoLanguage(message),
    requires_confirmation: false,
    risk_level: 'READ_ONLY',
    mode: 'demo' as const,
  };

  if (/^(please\s+)?(?:stop\s+moving|stop|halt)(?:\s+(?:now|robot|elarax|elara|aetherbot|bot))?[.!?]?$/i.test(message.trim())) {
    return { ...base, intent: 'STOP', risk_level: 'SAFETY_CRITICAL', response: 'Emergency stop acknowledged by the robot simulator.' };
  }
  if (/\b(?:research|market|competitor|swot|analy[sz]e|compare|industry)\b/i.test(message)) {
    const report: ResearchReport = {
      query: message,
      topic: message,
      status: 'limited',
      executive_summary: 'The local preview cannot retrieve live market sources.',
      market_overview: 'Start the backend to run source-grounded research.',
      key_trends: [],
      competitors: [],
      swot: { strengths: [], weaknesses: [], opportunities: [], threats: [] },
      sources: [],
      warnings: ['Live source retrieval requires the local backend.'],
      sources_used_count: 0,
    };
    return { ...base, intent: /swot/i.test(message) ? 'SWOT_ANALYSIS' : 'MARKET_RESEARCH', research_report: report, sources: [], data: { research: report, swot: report.swot, sources: [] }, response: report.executive_summary };
  }
  if (/^(please\s+)?(stop|halt|ruko|thamo)[.!]?$/i.test(message.trim()) || /^(থামো|রुको)[।.!]?$/.test(message.trim())) {
    return { ...base, intent: 'STOP', risk_level: 'SAFETY_CRITICAL', response: 'Emergency stop acknowledged by the robot simulator.' };
  }
  if (text.includes('schedule meeting') || text.includes('create meeting')) {
    const pending_action = { action: 'CREATE_MEETING', details: { source: message } };
    return { ...base, intent: 'CREATE_MEETING', risk_level: 'CONSEQUENTIAL', requires_confirmation: true, pending_action, response: 'The meeting is prepared and waiting for your confirmation.' };
  }
  if (text.includes('turn left') || text.includes('turn right') || text.includes('move forward')) {
    const command = text.includes('left') ? 'TURN_LEFT' : text.includes('right') ? 'TURN_RIGHT' : 'MOVE_FORWARD';
    return { ...base, intent: command, risk_level: 'HIGH_RISK', requires_confirmation: true, pending_action: { action: 'ROBOT_COMMAND', command }, response: 'The robot command is waiting for confirmation and was not executed.' };
  }
  if (text.includes('briefing')) {
    return { ...base, intent: 'DAILY_BRIEFING', emails: demoOverview.urgent_emails, response: 'Daily briefing: 1 important email and 1 meeting today. Focus on launch readiness.' };
  }
  if (text.includes('meeting') || text.includes('calendar') || text.includes('aaj')) {
    return { ...base, intent: 'GET_TODAY_SCHEDULE', response: 'Your calendar shows Product stand-up at 10:00 AM.' };
  }
  if (text.includes('email') || text.includes('inbox')) {
    return { ...base, intent: 'GET_URGENT_EMAILS', emails: demoOverview.urgent_emails, response: 'I found 1 urgent email: Launch review from Alice.' };
  }
  if (text.includes('help')) {
    return { ...base, intent: 'HELP', response: 'I can help with mock email, calendar, briefings, and safe robot commands.' };
  }
  return { ...base, intent: 'GENERAL_QUERY', intent_confidence: 0.55, response: 'The general AI model is not connected yet. Try an email, calendar, briefing, or robot command.' };
}

export async function getOverview(): Promise<Overview> {
  const endpoint = localApiUrl('/api/overview');
  if (endpoint) {
    try {
      const response = await fetch(endpoint, { signal: AbortSignal.timeout(15_000) });
      const data: Overview & { detail?: string } = await response.json();
      if (response.ok) return { ...data, mode: 'backend' };
      throw new Error(data.detail ?? `The local backend returned HTTP ${response.status}.`);
    } catch (error) {
      if (error instanceof Error && error.name !== 'AbortError' && error.message !== 'Failed to fetch') {
        throw error;
      }
      throw new Error('The local ElaraX backend is unavailable. Start it and refresh the page.');
    }
  }
  await wait(160);
  return demoOverview;
}

export async function getGoogleStatus(): Promise<GoogleConnectionStatus> {
  const endpoint = localApiUrl('/api/v1/auth/google/status');
  if (!endpoint) {
    return { configured: false, connected: false, scopes: [] };
  }
  try {
    const response = await fetch(endpoint, { signal: AbortSignal.timeout(5_000) });
    if (response.ok) return response.json();
  } catch {
    // The UI will display the local-backend requirement.
  }
  return { configured: false, connected: false, scopes: [], error: 'Local backend unavailable.' };
}

export async function launchGoogleConnection(): Promise<void> {
  const endpoint = localApiUrl('/api/v1/auth/google/launch');
  if (!endpoint) throw new Error('Google can only be connected from the local ElaraX app.');
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'X-ElaraX-Local': '1' },
    signal: AbortSignal.timeout(10_000),
  });
  const data: { detail?: string } = await response.json();
  if (!response.ok) throw new Error(data.detail ?? 'Google sign-in could not be started.');
}

export async function disconnectGoogle(): Promise<GoogleConnectionStatus> {
  const endpoint = localApiUrl('/api/v1/auth/google/disconnect');
  if (!endpoint) throw new Error('The local backend is unavailable.');
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: authHeaders(),
    signal: AbortSignal.timeout(12_000),
  });
  const data: GoogleConnectionStatus & { detail?: string } = await response.json();
  if (!response.ok) throw new Error(data.detail ?? 'Google could not be disconnected.');
  return data;
}

export async function getInvoiceAutomationStatus(): Promise<InvoiceAutomationStatus | undefined> {
  const endpoint = localApiUrl('/api/automation/invoice');
  if (!endpoint) return undefined;
  try {
    const response = await fetch(endpoint, { signal: AbortSignal.timeout(8_000) });
    if (response.ok) return response.json();
  } catch {
    // The automation card stays unavailable while the local API is offline.
  }
  return undefined;
}

export async function setInvoiceAutomationEnabled(enabled: boolean): Promise<InvoiceAutomationStatus> {
  const endpoint = localApiUrl('/api/automation/invoice');
  if (!endpoint) throw new Error('Invoice auto-replies require the local ElaraX backend.');
  const response = await fetch(endpoint, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
    signal: AbortSignal.timeout(12_000),
  });
  const data: InvoiceAutomationStatus & { detail?: string } = await response.json();
  if (!response.ok) throw new Error(data.detail ?? 'Invoice auto-replies could not be updated.');
  return data;
}

export async function listActionItems(): Promise<ActionItem[]> {
  const endpoint = localApiUrl('/api/action-items?status=open');
  if (!endpoint) return [];
  try {
    const response = await fetch(endpoint, { signal: AbortSignal.timeout(8_000) });
    if (response.ok) {
      const data: { items?: ActionItem[] } = await response.json();
      return Array.isArray(data.items) ? data.items : [];
    }
  } catch {
    // The compact Today checklist stays empty while the local API is offline.
  }
  return [];
}

export async function completeActionItem(id: string): Promise<ActionItem> {
  const endpoint = localApiUrl(`/api/action-items/${encodeURIComponent(id)}/complete`);
  if (!endpoint) throw new Error('Action items require the local ElaraX backend.');
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: authHeaders(),
    signal: AbortSignal.timeout(12_000),
  });
  const data: { item?: ActionItem; detail?: string } = await response.json();
  if (!response.ok || !data.item) throw new Error(data.detail ?? 'The action item could not be completed.');
  return data.item;
}

export async function sendChat(
  message: string,
  threadId?: string,
  inputSource: 'typed' | 'voice' = 'typed',
  language: LanguagePreference = 'auto',
  userId?: string,
): Promise<ChatResult> {
  const endpoint = localApiUrl('/api/chat');
  if (endpoint) {
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ message, thread_id: threadId, user_id: userId, input_source: inputSource, language }),
        signal: AbortSignal.timeout(45_000),
      });
      const data: ChatResult & { detail?: string } = await response.json();
      if (response.ok) return { ...data, mode: 'backend' };
      throw new Error(data.detail ?? `The local backend returned HTTP ${response.status}.`);
    } catch (error) {
      if (error instanceof Error && error.message !== 'Failed to fetch') throw error;
      throw new Error('The local ElaraX backend is unavailable. Start it and refresh the page.');
    }
  }
  return demoChat(message, threadId);
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  const chunkSize = 0x8000;
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize));
  }
  return window.btoa(binary);
}

export async function transcribeVoice(
  recording: Blob,
  language: LanguagePreference = 'auto',
): Promise<VoiceTranscriptionResult> {
  const endpoint = localApiUrl('/api/voice/transcribe');
  if (!endpoint) throw new Error('Voice commands require the local ElaraX backend.');
  const audioBuffer = await recording.arrayBuffer();
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      audio_base64: arrayBufferToBase64(audioBuffer),
      mime_type: recording.type || 'audio/webm',
      language,
    }),
    signal: AbortSignal.timeout(45_000),
  });
  const data: VoiceTranscriptionResult & { detail?: string } = await response.json();
  if (!response.ok) throw new Error(data.detail ?? 'The recording could not be transcribed.');
  return data;
}

function base64ToBlob(encoded: string, mimeType: string): Blob {
  const binary = window.atob(encoded);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return new Blob([bytes], { type: mimeType });
}

export async function synthesizeVoice(text: string, language?: string | null): Promise<Blob> {
  const endpoint = localApiUrl('/api/voice/synthesize');
  if (!endpoint) throw new Error('Spoken responses require the local ElaraX backend.');
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: text.slice(0, 3_000),
      ...(language ? { language } : {}),
    }),
    signal: AbortSignal.timeout(45_000),
  });
  const data: VoiceSynthesisResult & { detail?: string } = await response.json();
  if (!response.ok) throw new Error(data.detail ?? 'The response could not be spoken.');
  return base64ToBlob(data.audio_base64, data.mime_type);
}

export async function confirmAction(
  threadId: string,
  decision: 'approve' | 'reject',
): Promise<ConfirmationResult> {
  const endpoint = localApiUrl('/api/confirm');
  if (endpoint) {
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: threadId, decision }),
        signal: AbortSignal.timeout(30_000),
      });
      if (response.ok) return { ...(await response.json()), mode: 'backend' };
    } catch {
      // Fall through to the browser simulator.
    }
  }
  await wait(300);
  return {
    thread_id: threadId,
    decision: decision === 'approve' ? 'approved' : 'rejected',
    response: decision === 'approve'
      ? 'Action approved in simulation. No external service was changed.'
      : 'Action cancelled. Nothing was changed.',
    result: decision === 'approve' ? { ok: true, mock: true } : null,
    mode: 'demo',
  };
}
