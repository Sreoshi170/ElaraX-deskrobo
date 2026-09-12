import re

# Read the file
with open('frontend/app/page.tsx', 'r', encoding='utf-8') as f:
    code = f.read()

# Add import
import_stmt = "import { useMicVAD, utils } from '@ricky0123/vad-react';\n"
code = code.replace("import {\n  extractWakeCommand,", import_stmt + "import {\n  extractWakeCommand,")

# Replace Refs (Lines 172-188)
ref_pattern = r"(const wakeRecognitionRef = useRef.*?processVoiceTranscriptRef = useRef<\(transcript: string\) => Promise<void>>\(\);)"
new_refs = """processVoiceTranscriptRef = useRef<(transcript: string) => Promise<void>>();"""
code = re.sub(ref_pattern, new_refs, code, flags=re.DOTALL)

# Replace functions
functions_pattern = r"const stopWakeFallbackCapture =.*?const toggleWakePhrase = \(\) => {"
new_functions = """const vad = useMicVAD({
    startOnLoad: false,
    positiveSpeechThreshold: 0.8,
    negativeSpeechThreshold: 0.8,
    minSpeechFrames: 8,
    onSpeechStart: () => {
      if (!busyRef.current && voiceStateRef.current === 'idle') {
         setWakeState('heard');
         setNotice('Hey Elara heard — listening for your command…');
      }
    },
    onSpeechEnd: async (audio) => {
      if (busyRef.current || voiceStateRef.current !== 'idle') return;
      try {
        const wavBuffer = utils.encodeWAV(audio);
        const blob = new Blob([wavBuffer], { type: 'audio/wav' });
        
        setNotice('Transcribing your voice command…');
        const result = await transcribeVoice(blob);
        const command = extractWakeCommand(result.transcript);
        if (command !== undefined) {
           setNotice(command ? `Hey Elara heard — “${command}”` : 'Hey Elara heard — listening for your command…');
           if (command) {
             await processVoiceTranscriptRef.current?.(command);
             setWakeState('armed');
           } else {
             await startVoiceRecordingRef.current?.(true);
           }
        } else {
           setWakeState('armed');
           setNotice('“Hey Elara” is listening. Say the wake phrase followed by your command.');
        }
      } catch (error) {
        setWakeState('armed');
        const detail = error instanceof Error ? ` (${error.message})` : '';
        setNotice(`“Hey Elara” could not process the clip${detail}. Listening…`);
      }
    }
  });

  const disableWakePhrase = (noticeText = '“Hey Elara” wake phrase turned off.') => {
    wakeEnabledRef.current = false;
    vad.pause();
    setWakeEnabled(false);
    setWakeState('off');
    setNotice(noticeText);
  };

  const enableWakePhrase = async () => {
    processVoiceTranscriptRef.current = processVoiceTranscript;
    startVoiceRecordingRef.current = startVoiceRecording;
    if (!navigator.mediaDevices?.getUserMedia) {
      setNotice('“Hey Elara” needs microphone access, which is unavailable in this browser.');
      return;
    }
    
    setWakeState('starting');
    setNotice('Starting continuous listening mode…');
    try {
      const permissionStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      permissionStream.getTracks().forEach((track) => track.stop());
      
      wakeEnabledRef.current = true;
      setWakeEnabled(true);
      vad.start();
      setWakeState('armed');
      setNotice('“Hey Elara” is on. Say the wake phrase followed by your command.');
    } catch {
      disableWakePhrase('Microphone permission denied. Allow access to turn on “Hey Elara”.');
    }
  };

  const toggleWakePhrase = () => {"""

code = re.sub(functions_pattern, new_functions, code, flags=re.DOTALL)

# useEffect cleanup modification
cleanup_pattern = r"(if \(wakePhraseTimeoutRef\.current\).*?URL\.revokeObjectURL\(ttsUrlRef\.current\);)"
new_cleanup = """wakeEnabledRef.current = false;
    const recorder = voiceRecorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      recorder.ondataavailable = null;
      recorder.onstop = null;
      recorder.stop();
    }
    voiceStreamRef.current?.getTracks().forEach((track) => track.stop());
    ttsRequestRef.current += 1;
    ttsAudioRef.current?.pause();
    if (ttsUrlRef.current) URL.revokeObjectURL(ttsUrlRef.current);"""
code = re.sub(cleanup_pattern, new_cleanup, code, flags=re.DOTALL)

# write it back
with open('frontend/app/page.tsx', 'w', encoding='utf-8') as f:
    f.write(code)

print("done")
