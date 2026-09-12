import type { LanguagePreference } from './aether-api';

export type UiLanguage = 'en' | 'hi' | 'bn';
export type UiVoiceMode = 'idle' | 'armed' | 'heard' | 'listening' | 'thinking' | 'speaking';

export type UiCopy = {
  nav: {
    aria: string;
    intro: string;
    introBody: string;
    workspace: string;
    command: string;
    today: string;
    connections: string;
    robot: string;
    localWorkspace: string;
    settings: string;
    home: string;
    links: string;
  };
  status: {
    googleConnected: (email?: string | null) => string;
    ready: string;
    demo: string;
    wake: string;
    wakeStarting: string;
    wakeOn: string;
    wakeOff: string;
    notifications: string;
    mute: string;
    enableSpeech: string;
    replay: string;
    exitFocus: string;
    focus: string;
  };
  welcome: {
    today: string;
    greeting: (name: string) => string;
    clear: string;
    timezone: string;
  };
  voice: Record<UiVoiceMode, { eyebrow: string; title: string; description: string }>;
  input: {
    aria: string;
    type: string;
    placeholder: string;
    language: string;
    responseLanguage: string;
    speak: string;
    stop: string;
    send: string;
    mode: Record<string, string>;
  };
  quickPrompt: string;
  commands: {
    urgentEmails: string;
    calendar: string;
    briefing: string;
    robotStatus: string;
    quickPrompts: string[];
  };
  connections: {
    aria: string;
    connectedSurfaces: string;
    privateControls: string;
    gmailCalendar: string;
    gmailCalendarActive: string;
    connect: string;
    disconnect: string;
    waiting: string;
    invoiceAssistant: string;
    invoicePaused: string;
    invoiceOn: (count: number) => string;
    pauseInvoice: string;
    enableInvoice: string;
  };
  conversation: {
    aria: string;
    heading: string;
    clear: string;
    you: string;
    emailResults: (count: number) => string;
    noPreview: string;
    markedImportant: string;
    confirmationRequired: string;
    approvalPrompt: string;
    cancel: string;
    approve: string;
    localSupervisor: string;
    geminiSupervisor: string;
    steps: (count: number) => string;
    sources: (count: number) => string;
    research: string;
    keyTrends: string;
    sourceBackedFinding: string;
    swot: {
      strengths: string;
      weaknesses: string;
      opportunities: string;
      threats: string;
    };
    intentLabels: Record<string, string>;
    riskLabels: Record<string, string>;
    languageLabels: Record<string, string>;
  };
  context: {
    aria: string;
    title: string;
    countInView: (count?: number) => string;
    attention: string;
    attentionCount: (count: number) => string;
    loading: string;
    summary: string;
    playBriefing: string;
    voice: string;
    priorityInbox: string;
    urgentCount: (count: number) => string;
    inboxLoading: string;
    inboxClear: string;
    noPriority: string;
    nothingUrgent: string;
    recent: string;
    followUps: string;
    open: (count: number) => string;
    due: (date: string) => string;
    from: (subject: string) => string;
    schedule: string;
    askSchedule: string;
    todayParticipants: (count: number) => string;
    tomorrowParticipants: (count: number) => string;
    noMeetings: string;
    robot: string;
    simulatorReady: string;
    status: string;
    robotMode: (mode: string, motion: string) => string;
    privateSession: string;
  };
  notices: {
    speechUnavailable: string;
    emergencySent: string;
    emergencyFailed: string;
    busy: string;
    requestFailed: string;
    confirmationFailed: string;
    muted: string;
    speechEnabled: string;
    recordingUnsupported: string;
    recordingFailed: string;
    noAudioAfterWake: string;
    noAudio: string;
    transcribing: string;
    voiceFailed: string;
    listening: string;
    wakeListening: string;
    micDenied: string;
    micFailed: string;
    wakeDetected: string;
    checkingWake: string;
    wakeClipFailed: (detail: string) => string;
    wakeDisabled: (message: string) => string;
    localWakeUnavailable: string;
    micAccessUnavailable: string;
    startingListening: string;
    wakePermissionDenied: string;
    googleOpened: string;
    googleConnected: string;
    googleWaiting: string;
    googleStartFailed: string;
    googleDisconnectConfirm: string;
    googleDisconnected: string;
    googleDisconnectFailed: string;
    invoiceConfirm: string;
    invoiceOn: string;
    invoicePaused: string;
    invoiceUpdateFailed: string;
    actionCompleted: string;
    actionFailed: string;
  };
  robot: {
    simulation: string;
    stopped: string;
  };
};

const english: UiCopy = {
  nav: { aria: 'Primary navigation', intro: 'A calm second mind', introBody: 'For the moments between the meetings.', workspace: 'Workspace', command: 'Command', today: 'Today', connections: 'Connections', robot: 'Desk robot', localWorkspace: 'Local workspace', settings: 'Open settings', home: 'Home', links: 'Links' },
  status: { googleConnected: (email) => `Google connected${email ? ` — ${email}` : ''}`, ready: 'LangGraph ready — Google not connected', demo: 'Safe demo mode', wake: 'Hey Elara / DeskBot', wakeStarting: 'Starting…', wakeOn: 'Listening for Hey Elara or Hey DeskBot', wakeOff: 'Turn on hands-free voice commands', notifications: 'Notifications', mute: 'Mute spoken responses', enableSpeech: 'Enable spoken responses', replay: 'Replay last response', exitFocus: 'Exit focus', focus: 'Focus mode' },
  welcome: { today: 'Today', greeting: (name) => `Good evening, ${name}.`, clear: 'Your desk is clear. What should we take care of?', timezone: 'India Standard Time' },
  voice: {
    idle: { eyebrow: 'Ready when you are', title: 'What should we take care of?', description: 'Speak naturally or type a request in English, Bengali, Hindi, or a mix.' },
    armed: { eyebrow: 'Wake phrase is on', title: 'I’m listening for “Hey Elara” or “Hey DeskBot”.', description: 'Your microphone is open locally. Say either wake phrase, then your request.' },
    heard: { eyebrow: 'Wake phrase heard', title: 'I’m with you.', description: 'Checking that short moment of speech before I act on anything.' },
    listening: { eyebrow: 'Command listening', title: 'Go ahead. I’m listening.', description: 'Speak naturally. I’ll stop the recording when you pause.' },
    thinking: { eyebrow: 'Working on it', title: 'Let me look into that.', description: 'I’m checking the right source and preparing a safe response.' },
    speaking: { eyebrow: 'ElaraX is speaking', title: 'Here’s what I found.', description: 'You can mute or replay my response from the controls above.' },
  },
  input: { aria: 'Voice command', type: 'Type a request', placeholder: 'English, Bengali, Hindi, or a mixed request…', language: 'Language', responseLanguage: 'Response and voice language', speak: 'Speak', stop: 'Stop', send: 'Send', mode: { auto: 'Auto detect / স্বয়ংক্রিয় / स्वतः', en: 'English', hi: 'हिन्दी (Hindi)', bn: 'বাংলা (Bengali)', mixed: 'Mixed / মিশ্র / मिश्रित', voiceFirst: 'Voice first', cloudFallback: 'Cloud fallback', localWake: 'Local wake spotting' } },
  quickPrompt: 'Try',
  commands: { urgentEmails: 'Show urgent emails', calendar: 'What’s on my calendar?', briefing: 'Start my daily briefing', robotStatus: 'Robot status', quickPrompts: ['Show urgent emails', 'What’s on my calendar?', 'Start my daily briefing'] },
  connections: { aria: 'Connections and automations', connectedSurfaces: 'Connected surfaces', privateControls: 'Private controls', gmailCalendar: 'Gmail and Calendar', gmailCalendarActive: 'Gmail and Calendar active', connect: 'Connect', disconnect: 'Disconnect', waiting: 'Waiting…', invoiceAssistant: 'Invoice assistant', invoicePaused: 'Safe acknowledgement replies paused', invoiceOn: (count) => `Auto-replies on — ${count} sent`, pauseInvoice: 'Pause invoice auto-replies', enableInvoice: 'Enable invoice auto-replies' },
  conversation: { aria: 'Conversation', heading: 'Conversation', clear: 'Clear', you: 'You', emailResults: (count) => `${count} email results`, noPreview: 'No preview available.', markedImportant: 'Marked important', confirmationRequired: 'Confirmation required', approvalPrompt: 'ElaraX will only continue after your explicit approval.', cancel: 'Cancel', approve: 'Approve', localSupervisor: 'Local supervisor', geminiSupervisor: 'Gemini supervisor', steps: (count) => `${count} steps`, sources: (count) => `${count} sources`, research: 'Market research', keyTrends: 'Key trends', sourceBackedFinding: 'No source-backed finding.', swot: { strengths: 'Strengths', weaknesses: 'Weaknesses', opportunities: 'Opportunities', threats: 'Threats' }, intentLabels: {}, riskLabels: {}, languageLabels: { en: 'English', hi: 'Hindi', bn: 'Bengali', mixed: 'Mixed' } },
  context: { aria: 'Today and desk robot', title: 'Keep your day in view.', countInView: (count) => `${count ?? '…'} in view`, attention: 'Attention', attentionCount: (count) => `${count} things need your attention.`, loading: 'Loading your daily context…', summary: 'Your inbox, calendar, and follow-ups in one small view.', playBriefing: 'Play today’s briefing', voice: 'Voice', priorityInbox: 'Priority inbox', urgentCount: (count) => `${count} urgent`, inboxLoading: 'Loading', inboxClear: 'Inbox clear', noPriority: 'No priority email', nothingUrgent: 'Nothing urgent needs your attention.', recent: 'recently', followUps: 'Follow-ups', open: (count) => `${count} open`, due: (date) => `Due ${date}`, from: (subject) => `From: ${subject}`, schedule: 'Schedule', askSchedule: 'Ask schedule', todayParticipants: (count) => `Today — ${count} participant${count === 1 ? '' : 's'}`, tomorrowParticipants: (count) => `Tomorrow — ${count} participant${count === 1 ? '' : 's'}`, noMeetings: 'No meetings on the horizon.', robot: 'Desk robot', simulatorReady: 'Simulator ready', status: 'Status', robotMode: (mode, motion) => `${mode} mode — ${motion}`, privateSession: 'Private by design — local session' },
  notices: { speechUnavailable: 'Spoken output is unavailable in this browser.', emergencySent: 'Emergency stop sent to the desk robot.', emergencyFailed: 'The emergency stop could not be sent.', busy: 'ElaraX is finishing the current request. Say Hey Elara again in a moment.', requestFailed: 'ElaraX could not process that request.', confirmationFailed: 'ElaraX could not complete the confirmation.', muted: 'Spoken responses muted.', speechEnabled: 'Spoken responses enabled.', recordingUnsupported: 'This browser does not support microphone recording.', recordingFailed: 'Microphone recording failed. Please try again.', noAudioAfterWake: 'I did not hear enough audio after the wake phrase. Try again.', noAudio: 'I did not hear enough audio. Please try again.', transcribing: 'Transcribing your voice command…', voiceFailed: 'The voice command could not be processed.', listening: 'Listening… Speak your command, then tap the microphone to finish.', wakeListening: 'Wake phrase heard — listening for your command…', micDenied: 'Microphone permission was denied. Allow access and try again.', micFailed: 'The microphone could not be opened.', wakeDetected: 'Wake phrase detected — checking your voice…', checkingWake: 'Checking the wake phrase…', wakeClipFailed: (detail) => `The wake clip could not be checked${detail}. Listening…`, wakeDisabled: (message) => `Hey Elara was disabled because the listener stopped: ${message}`, localWakeUnavailable: 'Local wake spotting is unavailable here. Using the microphone clip fallback.', micAccessUnavailable: 'Hey Elara needs microphone access, which is unavailable in this browser.', startingListening: 'Starting continuous listening mode…', wakePermissionDenied: 'Microphone permission denied. Allow access to turn on Hey Elara.', googleOpened: 'Google sign-in opened in your normal browser. Finish there; ElaraX will detect it automatically.', googleConnected: 'Google connected. Your real Gmail and Calendar are now active.', googleWaiting: 'Google sign-in is still waiting. Finish consent, then connect again.', googleStartFailed: 'Google sign-in could not be started.', googleDisconnectConfirm: 'Disconnect Gmail and Calendar from this local ElaraX?', googleDisconnected: 'Google disconnected. ElaraX returned to safe demo data.', googleDisconnectFailed: 'Google could not be disconnected.', invoiceConfirm: 'Enable automatic invoice acknowledgements? ElaraX will send one fixed receipt acknowledgement to each new unread invoice email.', invoiceOn: 'Invoice auto-replies are on. New unread invoice emails will be acknowledged automatically.', invoicePaused: 'Invoice auto-replies are paused. No new acknowledgements will be sent.', invoiceUpdateFailed: 'Invoice auto-replies could not be updated.', actionCompleted: 'Action item completed.', actionFailed: 'The action item could not be completed.' },
  robot: { simulation: 'simulation', stopped: 'stopped' },
};

const hindi: UiCopy = {
  ...english,
  nav: { aria: 'मुख्य नेविगेशन', intro: 'एक शांत दूसरा मन', introBody: 'मीटिंग्स के बीच के पलों के लिए।', workspace: 'वर्कस्पेस', command: 'कमांड', today: 'आज', connections: 'कनेक्शन', robot: 'डेस्क रोबोट', localWorkspace: 'लोकल वर्कस्पेस', settings: 'सेटिंग्स खोलें', home: 'होम', links: 'लिंक्स' },
  status: { ...english.status, googleConnected: (email) => `Google कनेक्टेड${email ? ` — ${email}` : ''}`, ready: 'LangGraph तैयार — Google कनेक्टेड नहीं है', demo: 'सुरक्षित डेमो मोड', wake: 'Hey Elara / DeskBot', wakeStarting: 'शुरू हो रहा है…', wakeOn: 'Hey Elara या Hey DeskBot सुन रहा है', wakeOff: 'हैंड्स-फ्री वॉइस कमांड चालू करें', notifications: 'सूचनाएँ', mute: 'बोले गए जवाब बंद करें', enableSpeech: 'बोले गए जवाब चालू करें', replay: 'पिछला जवाब फिर चलाएँ', exitFocus: 'फोकस से बाहर', focus: 'फोकस मोड' },
  welcome: { today: 'आज', greeting: (name) => `शुभ संध्या, ${name}।`, clear: 'आपका डेस्क साफ़ है। किस काम से शुरू करें?', timezone: 'भारतीय मानक समय' },
  voice: { idle: { eyebrow: 'मैं तैयार हूँ', title: 'आज किस काम से शुरू करें?', description: 'हिंदी, English या मिश्रित भाषा में बोलें या लिखें।' }, armed: { eyebrow: 'वेक वाक्य चालू है', title: 'मैं “Hey Elara” या “Hey DeskBot” सुन रही हूँ।', description: 'वेक वाक्य के बाद अपना अनुरोध बोलें।' }, heard: { eyebrow: 'वेक वाक्य सुना', title: 'मैं आपके साथ हूँ।', description: 'कार्रवाई से पहले आपकी बात जाँच रही हूँ।' }, listening: { eyebrow: 'कमांड सुन रही हूँ', title: 'बोलिए, मैं सुन रही हूँ।', description: 'स्वाभाविक रूप से बोलें; रुकने पर रिकॉर्डिंग बंद होगी।' }, thinking: { eyebrow: 'काम चल रहा है', title: 'मैं इसे देख रही हूँ।', description: 'सही स्रोत जाँचकर सुरक्षित उत्तर तैयार कर रही हूँ।' }, speaking: { eyebrow: 'ElaraX बोल रही है', title: 'यह जानकारी मिली है।', description: 'ऊपर के नियंत्रण से आवाज़ बंद या दोबारा चला सकते हैं।' } },
  input: { aria: 'वॉइस कमांड', type: 'अनुरोध लिखें', placeholder: 'हिंदी, English या मिश्रित अनुरोध…', language: 'भाषा', responseLanguage: 'जवाब और आवाज़ की भाषा', speak: 'बोलें', stop: 'रोकें', send: 'भेजें', mode: { auto: 'स्वचालित पहचान / Auto detect', en: 'English', hi: 'हिन्दी', bn: 'বাংলা (Bengali)', mixed: 'मिश्रित / Mixed', voiceFirst: 'वॉइस पहले', cloudFallback: 'क्लाउड फॉलबैक', localWake: 'लोकल वेक पहचान' } },
  quickPrompt: 'आजमाएँ',
  commands: { urgentEmails: 'ज़रूरी ईमेल दिखाएँ', calendar: 'मेरे कैलेंडर पर क्या है?', briefing: 'आज की दैनिक ब्रीफिंग शुरू करें', robotStatus: 'रोबोट की स्थिति', quickPrompts: ['ज़रूरी ईमेल दिखाएँ', 'मेरे कैलेंडर पर क्या है?', 'आज की दैनिक ब्रीफिंग शुरू करें'] },
  connections: { ...english.connections, aria: 'कनेक्शन और ऑटोमेशन', connectedSurfaces: 'जुड़ी हुई सेवाएँ', privateControls: 'निजी नियंत्रण', gmailCalendar: 'Gmail और Calendar', gmailCalendarActive: 'Gmail और Calendar सक्रिय', connect: 'कनेक्ट करें', disconnect: 'डिस्कनेक्ट करें', waiting: 'प्रतीक्षा…', invoiceAssistant: 'इनवॉइस सहायक', invoicePaused: 'सुरक्षित स्वीकृति जवाब रुके हैं', invoiceOn: (count) => `ऑटो-जवाब चालू — ${count} भेजे गए`, pauseInvoice: 'इनवॉइस ऑटो-जवाब रोकें', enableInvoice: 'इनवॉइस ऑटो-जवाब चालू करें' },
  conversation: { ...english.conversation, aria: 'बातचीत', heading: 'बातचीत', clear: 'साफ़ करें', you: 'आप', emailResults: (count) => `${count} ईमेल परिणाम`, noPreview: 'कोई प्रीव्यू उपलब्ध नहीं।', markedImportant: 'महत्वपूर्ण चिह्नित', confirmationRequired: 'पुष्टि आवश्यक', approvalPrompt: 'आपकी स्पष्ट अनुमति के बाद ही ElaraX आगे बढ़ेगा।', cancel: 'रद्द करें', approve: 'अनुमोदित करें', safeFallback: 'सुरक्षित फॉलबैक', geminiSupervisor: 'Gemini सुपरवाइज़र', steps: (count) => `${count} चरण`, sources: (count) => `${count} स्रोत`, research: 'बाज़ार शोध', keyTrends: 'मुख्य रुझान', sourceBackedFinding: 'स्रोत-आधारित निष्कर्ष उपलब्ध नहीं।', languageLabels: { en: 'English', hi: 'हिन्दी', bn: 'বাংলা', mixed: 'मिश्रित' } },
  context: { ...english.context, aria: 'आज और डेस्क रोबोट', title: 'अपने दिन पर नज़र रखें।', countInView: (count) => `${count ?? '…'} नज़र में`, attention: 'ध्यान दें', attentionCount: (count) => `${count} चीज़ों पर आपका ध्यान चाहिए।`, loading: 'आपका दैनिक संदर्भ लोड हो रहा है…', summary: 'आपका इनबॉक्स, कैलेंडर और फॉलो-अप एक ही जगह।', playBriefing: 'आज की ब्रीफिंग चलाएँ', voice: 'आवाज़', priorityInbox: 'प्राथमिक इनबॉक्स', urgentCount: (count) => `${count} ज़रूरी`, inboxLoading: 'लोड हो रहा है', inboxClear: 'इनबॉक्स साफ़ है', noPriority: 'कोई प्राथमिक ईमेल नहीं', nothingUrgent: 'आपके ध्यान के लिए कुछ ज़रूरी नहीं है।', recent: 'हाल में', followUps: 'फॉलो-अप', open: (count) => `${count} खुले`, due: (date) => `समय सीमा ${date}`, from: (subject) => `प्रेषक: ${subject}`, schedule: 'शेड्यूल', askSchedule: 'शेड्यूल पूछें', todayParticipants: (count) => `आज — ${count} प्रतिभागी`, tomorrowParticipants: (count) => `कल — ${count} प्रतिभागी`, noMeetings: 'आगे कोई मीटिंग नहीं है।', robot: 'डेस्क रोबोट', simulatorReady: 'सिम्युलेटर तैयार', status: 'स्थिति', robotMode: (mode, motion) => `${mode} मोड — ${motion}`, privateSession: 'निजी डिज़ाइन — लोकल सत्र' },
  notices: { ...english.notices, speechUnavailable: 'इस ब्राउज़र में आवाज़ उपलब्ध नहीं है।', emergencySent: 'डेस्क रोबोट को आपातकालीन रोक भेज दी गई।', emergencyFailed: 'आपातकालीन रोक नहीं भेजी जा सकी।', busy: 'ElaraX पिछला अनुरोध पूरा कर रही है। थोड़ी देर में Hey Elara फिर कहें।', requestFailed: 'ElaraX यह अनुरोध पूरा नहीं कर सकी।', confirmationFailed: 'ElaraX पुष्टि पूरी नहीं कर सकी।', muted: 'बोले गए जवाब बंद हैं।', speechEnabled: 'बोले गए जवाब चालू हैं।', recordingUnsupported: 'यह ब्राउज़र माइक्रोफ़ोन रिकॉर्डिंग का समर्थन नहीं करता।', recordingFailed: 'माइक्रोफ़ोन रिकॉर्डिंग विफल हुई। फिर कोशिश करें।', noAudioAfterWake: 'वेक वाक्य के बाद पर्याप्त आवाज़ नहीं मिली। फिर कोशिश करें।', noAudio: 'पर्याप्त आवाज़ नहीं मिली। फिर कोशिश करें।', transcribing: 'आपका वॉइस कमांड लिखा जा रहा है…', voiceFailed: 'वॉइस कमांड पूरा नहीं हो सका।', listening: 'सुन रही हूँ… अपना कमांड बोलें और माइक्रोफ़ोन रोकें।', wakeListening: 'वेक वाक्य सुना — कमांड सुन रही हूँ…', micDenied: 'माइक्रोफ़ोन अनुमति नहीं मिली। अनुमति देकर फिर कोशिश करें।', micFailed: 'माइक्रोफ़ोन नहीं खुल सका।', wakeDetected: 'वेक वाक्य मिला — आवाज़ जाँच रही हूँ…', checkingWake: 'वेक वाक्य जाँच रही हूँ…', wakeClipFailed: (detail) => `वेक क्लिप जाँची नहीं जा सकी${detail}। सुन रही हूँ…`, wakeDisabled: (message) => `लिस्नर रुकने के कारण Hey Elara बंद है: ${message}`, localWakeUnavailable: 'लोकल वेक पहचान उपलब्ध नहीं है। माइक्रोफ़ोन क्लिप फॉलबैक उपयोग हो रहा है।', micAccessUnavailable: 'इस ब्राउज़र में Hey Elara के लिए माइक्रोफ़ोन उपलब्ध नहीं है।', startingListening: 'लगातार सुनना शुरू हो रहा है…', wakePermissionDenied: 'माइक्रोफ़ोन अनुमति नहीं मिली। Hey Elara चालू करने के लिए अनुमति दें।', googleOpened: 'Google साइन-इन सामान्य ब्राउज़र में खुला है। वहाँ पूरा करें; ElaraX अपने आप पहचान लेगी।', googleConnected: 'Google कनेक्टेड है। आपका असली Gmail और Calendar सक्रिय है।', googleWaiting: 'Google साइन-इन अभी प्रतीक्षा में है। अनुमति पूरी करके फिर कनेक्ट करें।', googleStartFailed: 'Google साइन-इन शुरू नहीं हो सका।', googleDisconnectConfirm: 'इस लोकल ElaraX से Gmail और Calendar डिस्कनेक्ट करें?', googleDisconnected: 'Google डिस्कनेक्टेड है। ElaraX सुरक्षित डेमो डेटा पर लौट गई।', googleDisconnectFailed: 'Google डिस्कनेक्ट नहीं हो सका।', invoiceConfirm: 'स्वचालित इनवॉइस स्वीकृति चालू करें? ElaraX हर नए अपठित इनवॉइस ईमेल के लिए एक निश्चित रसीद जवाब भेजेगी।', invoiceOn: 'इनवॉइस ऑटो-जवाब चालू हैं। नए अपठित इनवॉइस ईमेल को अपने आप जवाब मिलेगा।', invoicePaused: 'इनवॉइस ऑटो-जवाब रुके हैं। कोई नया जवाब नहीं भेजा जाएगा।', invoiceUpdateFailed: 'इनवॉइस ऑटो-जवाब अपडेट नहीं हो सके।', actionCompleted: 'कार्य पूरा हुआ।', actionFailed: 'कार्य पूरा नहीं हो सका।' },
  robot: { simulation: 'सिम्युलेशन', stopped: 'रुका हुआ' },
};

const bengali: UiCopy = {
  ...english,
  nav: { aria: 'প্রধান নেভিগেশন', intro: 'একটি শান্ত দ্বিতীয় মন', introBody: 'মিটিংয়ের মাঝের মুহূর্তগুলোর জন্য।', workspace: 'ওয়ার্কস্পেস', command: 'কমান্ড', today: 'আজ', connections: 'সংযোগ', robot: 'ডেস্ক রোবট', localWorkspace: 'লোকাল ওয়ার্কস্পেস', settings: 'সেটিংস খুলুন', home: 'হোম', links: 'লিংকস' },
  status: { ...english.status, googleConnected: (email) => `Google সংযুক্ত${email ? ` — ${email}` : ''}`, ready: 'LangGraph প্রস্তুত — Google সংযুক্ত নয়', demo: 'নিরাপদ ডেমো মোড', wake: 'Hey Elara / DeskBot', wakeStarting: 'শুরু হচ্ছে…', wakeOn: 'Hey Elara বা Hey DeskBot শুনছি', wakeOff: 'হ্যান্ডস-ফ্রি ভয়েস কমান্ড চালু করুন', notifications: 'বিজ্ঞপ্তি', mute: 'কথার উত্তর বন্ধ করুন', enableSpeech: 'কথার উত্তর চালু করুন', replay: 'শেষ উত্তর আবার চালান', exitFocus: 'ফোকাস থেকে বের হন', focus: 'ফোকাস মোড' },
  welcome: { today: 'আজ', greeting: (name) => `শুভ সন্ধ্যা, ${name}।`, clear: 'আপনার ডেস্ক পরিষ্কার। কোন কাজটি আগে করব?', timezone: 'ভারতীয় মান সময়' },
  voice: { idle: { eyebrow: 'আমি প্রস্তুত', title: 'আজ কোন কাজটি আগে করি?', description: 'বাংলা, English বা মিশ্র ভাষায় বলুন বা লিখুন।' }, armed: { eyebrow: 'ওয়েক ফ্রেজ চালু', title: 'আমি “Hey Elara” বা “Hey DeskBot” শুনছি।', description: 'ওয়েক ফ্রেজের পরে আপনার অনুরোধ বলুন।' }, heard: { eyebrow: 'ওয়েক ফ্রেজ শোনা হয়েছে', title: 'আমি আপনার সঙ্গে আছি।', description: 'কাজ করার আগে আপনার কথাটি যাচাই করছি।' }, listening: { eyebrow: 'কমান্ড শুনছি', title: 'বলুন, আমি শুনছি।', description: 'স্বাভাবিকভাবে বলুন; থামলে রেকর্ডিং বন্ধ হবে।' }, thinking: { eyebrow: 'কাজ চলছে', title: 'আমি এটি দেখে নিচ্ছি।', description: 'সঠিক উৎস পরীক্ষা করে নিরাপদ উত্তর তৈরি করছি।' }, speaking: { eyebrow: 'ElaraX বলছে', title: 'এই তথ্যটি পেয়েছি।', description: 'উপরের নিয়ন্ত্রণ থেকে শব্দ বন্ধ বা আবার চালু করুন।' } },
  input: { aria: 'ভয়েস কমান্ড', type: 'অনুরোধ লিখুন', placeholder: 'বাংলা, English বা মিশ্র অনুরোধ…', language: 'ভাষা', responseLanguage: 'উত্তর ও কণ্ঠের ভাষা', speak: 'বলুন', stop: 'থামান', send: 'পাঠান', mode: { auto: 'স্বয়ংক্রিয় শনাক্ত / Auto detect', en: 'English', hi: 'हिन्दी (Hindi)', bn: 'বাংলা', mixed: 'মিশ্র / Mixed', voiceFirst: 'ভয়েস আগে', cloudFallback: 'ক্লাউড ফোলব্যাক', localWake: 'লোকাল ওয়েক শনাক্ত' } },
  quickPrompt: 'চেষ্টা করুন',
  commands: { urgentEmails: 'জরুরি ইমেল দেখান', calendar: 'আমার ক্যালেন্ডারে কী আছে?', briefing: 'আজকের দৈনিক ব্রিফিং শুরু করুন', robotStatus: 'রোবটের অবস্থা', quickPrompts: ['জরুরি ইমেল দেখান', 'আমার ক্যালেন্ডারে কী আছে?', 'আজকের দৈনিক ব্রিফিং শুরু করুন'] },
  connections: { ...english.connections, aria: 'সংযোগ ও অটোমেশন', connectedSurfaces: 'সংযুক্ত সেবা', privateControls: 'ব্যক্তিগত নিয়ন্ত্রণ', gmailCalendar: 'Gmail ও Calendar', gmailCalendarActive: 'Gmail ও Calendar সক্রিয়', connect: 'সংযুক্ত করুন', disconnect: 'বিচ্ছিন্ন করুন', waiting: 'অপেক্ষা…', invoiceAssistant: 'ইনভয়েস সহকারী', invoicePaused: 'নিরাপদ স্বীকৃতি উত্তর থামানো', invoiceOn: (count) => `অটো-উত্তর চালু — ${count} পাঠানো হয়েছে`, pauseInvoice: 'ইনভয়েস অটো-উত্তর থামান', enableInvoice: 'ইনভয়েস অটো-উত্তর চালু করুন' },
  conversation: { ...english.conversation, aria: 'কথোপকথন', heading: 'কথোপকথন', clear: 'পরিষ্কার করুন', you: 'আপনি', emailResults: (count) => `${count}টি ইমেল ফলাফল`, noPreview: 'কোনও প্রিভিউ নেই।', markedImportant: 'গুরুত্বপূর্ণ হিসেবে চিহ্নিত', confirmationRequired: 'নিশ্চিতকরণ প্রয়োজন', approvalPrompt: 'আপনার স্পষ্ট অনুমতি না পাওয়া পর্যন্ত ElaraX এগোবে না।', cancel: 'বাতিল', approve: 'অনুমোদন', safeFallback: 'নিরাপদ ফোলব্যাক', geminiSupervisor: 'Gemini সুপারভাইজার', steps: (count) => `${count}টি ধাপ`, sources: (count) => `${count}টি উৎস`, research: 'বাজার গবেষণা', keyTrends: 'প্রধান প্রবণতা', sourceBackedFinding: 'উৎস-সমর্থিত তথ্য নেই।', languageLabels: { en: 'English', hi: 'हिन्दी', bn: 'বাংলা', mixed: 'মিশ্র' } },
  context: { ...english.context, aria: 'আজ ও ডেস্ক রোবট', title: 'আপনার দিনটি নজরে রাখুন।', countInView: (count) => `${count ?? '…'}টি নজরে`, attention: 'মনোযোগ', attentionCount: (count) => `${count}টি বিষয়ে আপনার মনোযোগ প্রয়োজন।`, loading: 'আপনার দৈনিক তথ্য লোড হচ্ছে…', summary: 'ইনবক্স, ক্যালেন্ডার ও ফলো-আপ এক জায়গায়।', playBriefing: 'আজকের ব্রিফিং চালান', voice: 'ভয়েস', priorityInbox: 'প্রাথমিক ইনবক্স', urgentCount: (count) => `${count}টি জরুরি`, inboxLoading: 'লোড হচ্ছে', inboxClear: 'ইনবক্স পরিষ্কার', noPriority: 'কোনও প্রাথমিক ইমেল নেই', nothingUrgent: 'আপনার মনোযোগের জন্য জরুরি কিছু নেই।', recent: 'সম্প্রতি', followUps: 'ফলো-আপ', open: (count) => `${count}টি খোলা`, due: (date) => `সময়সীমা ${date}`, from: (subject) => `থেকে: ${subject}`, schedule: 'সময়সূচি', askSchedule: 'সময়সূচি জিজ্ঞেস করুন', todayParticipants: (count) => `আজ — ${count} জন অংশগ্রহণকারী`, tomorrowParticipants: (count) => `আগামীকাল — ${count} জন অংশগ্রহণকারী`, noMeetings: 'সামনে কোনও মিটিং নেই।', robot: 'ডেস্ক রোবট', simulatorReady: 'সিমুলেটর প্রস্তুত', status: 'অবস্থা', robotMode: (mode, motion) => `${mode} মোড — ${motion}`, privateSession: 'নিরাপদ নকশা — লোকাল সেশন' },
  notices: { ...english.notices, speechUnavailable: 'এই ব্রাউজারে ভয়েস আউটপুট নেই।', emergencySent: 'ডেস্ক রোবটকে জরুরি থামার নির্দেশ পাঠানো হয়েছে।', emergencyFailed: 'জরুরি থামার নির্দেশ পাঠানো যায়নি।', busy: 'ElaraX আগের অনুরোধ শেষ করছে। একটু পরে Hey Elara বলুন।', requestFailed: 'ElaraX অনুরোধটি সম্পন্ন করতে পারেনি।', confirmationFailed: 'ElaraX নিশ্চিতকরণ সম্পন্ন করতে পারেনি।', muted: 'কথার উত্তর বন্ধ।', speechEnabled: 'কথার উত্তর চালু।', recordingUnsupported: 'এই ব্রাউজারে মাইক্রোফোন রেকর্ডিং সমর্থিত নয়।', recordingFailed: 'মাইক্রোফোন রেকর্ডিং ব্যর্থ হয়েছে। আবার চেষ্টা করুন।', noAudioAfterWake: 'ওয়েক ফ্রেজের পরে যথেষ্ট শব্দ শোনা যায়নি। আবার চেষ্টা করুন।', noAudio: 'যথেষ্ট শব্দ শোনা যায়নি। আবার চেষ্টা করুন।', transcribing: 'আপনার ভয়েস কমান্ড লেখা হচ্ছে…', voiceFailed: 'ভয়েস কমান্ড সম্পন্ন করা যায়নি।', listening: 'শুনছি… কমান্ড বলুন, তারপর মাইক্রোফোন থামান।', wakeListening: 'ওয়েক ফ্রেজ শোনা হয়েছে — কমান্ড শুনছি…', micDenied: 'মাইক্রোফোনের অনুমতি নেই। অনুমতি দিয়ে আবার চেষ্টা করুন।', micFailed: 'মাইক্রোফোন খোলা যায়নি।', wakeDetected: 'ওয়েক ফ্রেজ পাওয়া গেছে — আপনার কথা যাচাই করছি…', checkingWake: 'ওয়েক ফ্রেজ যাচাই করছি…', wakeClipFailed: (detail) => `ওয়েক ক্লিপ যাচাই করা যায়নি${detail}। শুনছি…`, wakeDisabled: (message) => `লিসেনার থেমে যাওয়ায় Hey Elara বন্ধ হয়েছে: ${message}`, localWakeUnavailable: 'লোকাল ওয়েক শনাক্তকরণ নেই। মাইক্রোফোন ক্লিপ ফোলব্যাক ব্যবহার হচ্ছে।', micAccessUnavailable: 'এই ব্রাউজারে Hey Elara-এর জন্য মাইক্রোফোন নেই।', startingListening: 'একটানা শোনা শুরু হচ্ছে…', wakePermissionDenied: 'মাইক্রোফোনের অনুমতি নেই। Hey Elara চালু করতে অনুমতি দিন।', googleOpened: 'Google সাইন-ইন সাধারণ ব্রাউজারে খোলা হয়েছে। সেখানে শেষ করুন; ElaraX নিজে বুঝে নেবে।', googleConnected: 'Google সংযুক্ত। আসল Gmail ও Calendar এখন সক্রিয়।', googleWaiting: 'Google সাইন-ইন এখনও অপেক্ষায়। অনুমতি শেষ করে আবার সংযুক্ত করুন।', googleStartFailed: 'Google সাইন-ইন শুরু করা যায়নি।', googleDisconnectConfirm: 'এই লোকাল ElaraX থেকে Gmail ও Calendar বিচ্ছিন্ন করবেন?', googleDisconnected: 'Google বিচ্ছিন্ন। ElaraX নিরাপদ ডেমো ডেটায় ফিরেছে।', googleDisconnectFailed: 'Google বিচ্ছিন্ন করা যায়নি।', invoiceConfirm: 'স্বয়ংক্রিয় ইনভয়েস স্বীকৃতি চালু করবেন? ElaraX প্রতিটি নতুন অপঠিত ইনভয়েস ইমেলের জন্য একটি নির্দিষ্ট রসিদ উত্তর পাঠাবে।', invoiceOn: 'ইনভয়েস অটো-উত্তর চালু। নতুন অপঠিত ইনভয়েসে স্বয়ংক্রিয় উত্তর যাবে।', invoicePaused: 'ইনভয়েস অটো-উত্তর থামানো। নতুন উত্তর যাবে না।', invoiceUpdateFailed: 'ইনভয়েস অটো-উত্তর আপডেট করা যায়নি।', actionCompleted: 'কাজ সম্পন্ন হয়েছে।', actionFailed: 'কাজটি সম্পন্ন করা যায়নি।' },
  robot: { simulation: 'সিমুলেশন', stopped: 'থামানো' },
};

const englishIntentLabels: Record<string, string> = {
  CHECK_EMAIL: 'Check email', READ_EMAIL: 'Read email', READ_UNREAD_EMAILS: 'Read unread emails', FIND_EMAIL: 'Find email',
  SUMMARIZE_EMAIL: 'Summarize email', SUMMARIZE_THREAD: 'Summarize thread', PRIORITIZE_EMAILS: 'Prioritize emails', GET_URGENT_EMAILS: 'Get urgent emails',
  DRAFT_REPLY: 'Draft reply', SEND_REPLY: 'Send reply', COMPOSE_EMAIL: 'Compose email', SEND_EMAIL: 'Send email', FORWARD_EMAIL: 'Forward email',
  LIST_SENT_EMAILS: 'List sent emails', LIST_DRAFT_EMAILS: 'List drafts', LIST_STARRED_EMAILS: 'List starred emails',
  MARK_READ: 'Mark as read', MARK_UNREAD: 'Mark as unread', STAR_EMAIL: 'Star email', UNSTAR_EMAIL: 'Unstar email', ARCHIVE_EMAIL: 'Archive email', TRASH_EMAIL: 'Move to trash', DELETE_EMAIL: 'Delete email',
  CHECK_CALENDAR: 'Check calendar', GET_TODAY_SCHEDULE: "Today's schedule", GET_TOMORROW_SCHEDULE: "Tomorrow's schedule", CHECK_AVAILABILITY: 'Check availability',
  CREATE_MEETING: 'Create meeting', RESCHEDULE_MEETING: 'Reschedule meeting', CANCEL_MEETING: 'Cancel meeting',
  MOVE_FORWARD: 'Move forward', MOVE_BACKWARD: 'Move backward', TURN_LEFT: 'Turn left', TURN_RIGHT: 'Turn right', COME_HERE: 'Come here', LOOK_AT_USER: 'Look at user', STATUS: 'Status', STOP: 'Emergency stop',
  MARKET_RESEARCH: 'Market research', COMPETITOR_ANALYSIS: 'Competitor analysis', SWOT_ANALYSIS: 'SWOT analysis', GENERAL_QUERY: 'General request', HELP: 'Help', UNKNOWN: 'Unrecognized request',
};

const hindiIntentLabels: Record<string, string> = {
  CHECK_EMAIL: 'ईमेल देखें', READ_EMAIL: 'ईमेल पढ़ें', READ_UNREAD_EMAILS: 'अपठित ईमेल पढ़ें', FIND_EMAIL: 'ईमेल खोजें',
  SUMMARIZE_EMAIL: 'ईमेल का सारांश', SUMMARIZE_THREAD: 'थ्रेड का सारांश', PRIORITIZE_EMAILS: 'ईमेल प्राथमिकता दें', GET_URGENT_EMAILS: 'ज़रूरी ईमेल देखें',
  DRAFT_REPLY: 'उत्तर का मसौदा', SEND_REPLY: 'उत्तर भेजें', COMPOSE_EMAIL: 'ईमेल लिखें', SEND_EMAIL: 'ईमेल भेजें', FORWARD_EMAIL: 'ईमेल अग्रेषित करें',
  LIST_SENT_EMAILS: 'भेजे गए ईमेल', LIST_DRAFT_EMAILS: 'मसौदे', LIST_STARRED_EMAILS: 'तारांकित ईमेल',
  MARK_READ: 'पढ़ा हुआ चिह्नित करें', MARK_UNREAD: 'अपठित चिह्नित करें', STAR_EMAIL: 'ईमेल को तारा दें', UNSTAR_EMAIL: 'तारा हटाएँ', ARCHIVE_EMAIL: 'ईमेल संग्रहित करें', TRASH_EMAIL: 'कूड़ेदान में भेजें', DELETE_EMAIL: 'ईमेल हटाएँ',
  CHECK_CALENDAR: 'कैलेंडर देखें', GET_TODAY_SCHEDULE: 'आज का कार्यक्रम', GET_TOMORROW_SCHEDULE: 'कल का कार्यक्रम', CHECK_AVAILABILITY: 'उपलब्धता देखें',
  CREATE_MEETING: 'मीटिंग बनाएँ', RESCHEDULE_MEETING: 'मीटिंग का समय बदलें', CANCEL_MEETING: 'मीटिंग रद्द करें',
  MOVE_FORWARD: 'आगे बढ़ें', MOVE_BACKWARD: 'पीछे जाएँ', TURN_LEFT: 'बाएँ मुड़ें', TURN_RIGHT: 'दाएँ मुड़ें', COME_HERE: 'यहाँ आएँ', LOOK_AT_USER: 'उपयोगकर्ता की ओर देखें', STATUS: 'स्थिति', STOP: 'आपातकालीन रोक',
  MARKET_RESEARCH: 'बाज़ार शोध', COMPETITOR_ANALYSIS: 'प्रतियोगी विश्लेषण', SWOT_ANALYSIS: 'SWOT विश्लेषण', GENERAL_QUERY: 'सामान्य अनुरोध', HELP: 'सहायता', UNKNOWN: 'अपरिचित अनुरोध',
};

const bengaliIntentLabels: Record<string, string> = {
  CHECK_EMAIL: 'ইমেইল দেখুন', READ_EMAIL: 'ইমেইল পড়ুন', READ_UNREAD_EMAILS: 'অপঠিত ইমেইল পড়ুন', FIND_EMAIL: 'ইমেইল খুঁজুন',
  SUMMARIZE_EMAIL: 'ইমেইলের সারাংশ', SUMMARIZE_THREAD: 'থ্রেডের সারাংশ', PRIORITIZE_EMAILS: 'ইমেইল অগ্রাধিকার দিন', GET_URGENT_EMAILS: 'জরুরি ইমেইল দেখুন',
  DRAFT_REPLY: 'উত্তরের খসড়া', SEND_REPLY: 'উত্তর পাঠান', COMPOSE_EMAIL: 'ইমেইল লিখুন', SEND_EMAIL: 'ইমেইল পাঠান', FORWARD_EMAIL: 'ইমেইল ফরওয়ার্ড করুন',
  LIST_SENT_EMAILS: 'পাঠানো ইমেইল', LIST_DRAFT_EMAILS: 'খসড়া', LIST_STARRED_EMAILS: 'তারকাচিহ্নিত ইমেইল',
  MARK_READ: 'পড়া হিসেবে চিহ্নিত করুন', MARK_UNREAD: 'অপঠিত হিসেবে চিহ্নিত করুন', STAR_EMAIL: 'ইমেইলে তারকা দিন', UNSTAR_EMAIL: 'তারকা সরান', ARCHIVE_EMAIL: 'ইমেইল সংরক্ষণ করুন', TRASH_EMAIL: 'আবর্জনায় পাঠান', DELETE_EMAIL: 'ইমেইল মুছুন',
  CHECK_CALENDAR: 'ক্যালেন্ডার দেখুন', GET_TODAY_SCHEDULE: 'আজকের সময়সূচি', GET_TOMORROW_SCHEDULE: 'আগামীকালের সময়সূচি', CHECK_AVAILABILITY: 'উপলভ্যতা দেখুন',
  CREATE_MEETING: 'মিটিং তৈরি করুন', RESCHEDULE_MEETING: 'মিটিং পুনঃনির্ধারণ করুন', CANCEL_MEETING: 'মিটিং বাতিল করুন',
  MOVE_FORWARD: 'সামনে যান', MOVE_BACKWARD: 'পিছনে যান', TURN_LEFT: 'বাঁয়ে ঘুরুন', TURN_RIGHT: 'ডানে ঘুরুন', COME_HERE: 'এখানে আসুন', LOOK_AT_USER: 'ব্যবহারকারীর দিকে তাকান', STATUS: 'অবস্থা', STOP: 'জরুরি থামানো',
  MARKET_RESEARCH: 'বাজার গবেষণা', COMPETITOR_ANALYSIS: 'প্রতিযোগী বিশ্লেষণ', SWOT_ANALYSIS: 'SWOT বিশ্লেষণ', GENERAL_QUERY: 'সাধারণ অনুরোধ', HELP: 'সহায়তা', UNKNOWN: 'অপরিচিত অনুরোধ',
};

const englishRiskLabels: Record<string, string> = { READ_ONLY: 'Read only', LOW_RISK: 'Low risk', CONSEQUENTIAL: 'Confirmation required', HIGH_RISK: 'High risk', SAFETY_CRITICAL: 'Safety critical' };
const hindiRiskLabels: Record<string, string> = { READ_ONLY: 'केवल पढ़ें', LOW_RISK: 'कम जोखिम', CONSEQUENTIAL: 'पुष्टि आवश्यक', HIGH_RISK: 'उच्च जोखिम', SAFETY_CRITICAL: 'सुरक्षा महत्वपूर्ण' };
const bengaliRiskLabels: Record<string, string> = { READ_ONLY: 'শুধু পড়ুন', LOW_RISK: 'কম ঝুঁকি', CONSEQUENTIAL: 'নিশ্চিতকরণ প্রয়োজন', HIGH_RISK: 'উচ্চ ঝুঁকি', SAFETY_CRITICAL: 'নিরাপত্তা-গুরুত্বপূর্ণ' };

const dictionaries: Record<UiLanguage, UiCopy> = {
  en: { ...english, conversation: { ...english.conversation, intentLabels: englishIntentLabels, riskLabels: englishRiskLabels } },
  hi: { ...hindi, conversation: { ...hindi.conversation, intentLabels: hindiIntentLabels, riskLabels: hindiRiskLabels, swot: { strengths: 'ताकत', weaknesses: 'कमज़ोरियाँ', opportunities: 'अवसर', threats: 'खतरे' } } },
  bn: { ...bengali, conversation: { ...bengali.conversation, intentLabels: bengaliIntentLabels, riskLabels: bengaliRiskLabels, swot: { strengths: 'শক্তি', weaknesses: 'দুর্বলতা', opportunities: 'সুযোগ', threats: 'হুমকি' } } },
};

export function getUiCopy(language: UiLanguage): UiCopy {
  return dictionaries[language] || english;
}

export function uiLanguageFor(preference: LanguagePreference, detectedLanguage?: string | null): UiLanguage {
  if (preference === 'hi') return 'hi';
  if (preference === 'bn') return 'bn';
  if (preference === 'en') return 'en';
  if (detectedLanguage === 'hi') return 'hi';
  if (detectedLanguage === 'bn') return 'bn';
  return 'en';
}

export function localeForUiLanguage(language: UiLanguage): string {
  return language === 'hi' ? 'hi-IN' : language === 'bn' ? 'bn-IN' : 'en-IN';
}

export function displayLanguage(language?: string | null, copy: UiCopy = english): string {
  if (!language) return '';
  return copy.conversation.languageLabels[language] || language;
}

export function displayIntent(intent: string, copy: UiCopy): string {
  return copy.conversation.intentLabels[intent] || intent.replaceAll('_', ' ');
}

export function displayRisk(risk: string, copy: UiCopy): string {
  return copy.conversation.riskLabels[risk] || risk.replaceAll('_', ' ');
}
