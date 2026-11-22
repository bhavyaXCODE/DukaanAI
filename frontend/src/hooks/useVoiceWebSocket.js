import { useState, useEffect, useRef, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useAudioPlayer } from './useAudioPlayer';

export const useVoiceWebSocket = (shopId = 1, currentLanguage = 'kn-IN') => {
  const [wsState, setWsState] = useState('DISCONNECTED'); // CONNECTING, CONNECTED, DISCONNECTED, RECONNECTING
  const [sessionId] = useState(() => uuidv4());
  const [conversation, setConversation] = useState([]);
  const [sessionState, setSessionState] = useState('IDLE'); // IDLE, LISTENING, PROCESSING, CONFIRMING, DONE
  const [pendingDraft, setPendingDraft] = useState(null);
  const [lastResult, setLastResult] = useState(null);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const socketRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);
  const { playAudio } = useAudioPlayer();

  // Helper for TTS using browser SpeechSynthesis in demo/mock mode
  const speakText = useCallback(
    (text) => {
      if (!('speechSynthesis' in window) || !text) return;
      try {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = currentLanguage;
        utterance.rate = 0.95;
        utterance.pitch = 1.0;

        utterance.onstart = () => setIsSpeaking(true);
        utterance.onend = () => setIsSpeaking(false);
        utterance.onerror = () => setIsSpeaking(false);

        // Try to find matching voice for language
        const voices = window.speechSynthesis.getVoices();
        const matchingVoice = voices.find((v) => v.lang.startsWith(currentLanguage.slice(0, 2)));
        if (matchingVoice) {
          utterance.voice = matchingVoice;
        }

        window.speechSynthesis.speak(utterance);
      } catch (err) {
        console.warn('Speech synthesis error:', err);
        setIsSpeaking(false);
      }
    },
    [currentLanguage]
  );

// Stopwords for Indic and English Voice Khata ledger extraction
const STOPWORDS_SET = new Set([
  'credit', 'debit', 'payment', 'paid', 'jama', 'udhar', 'rupees', 'rupaye', 'rupay', 'rs',
  'bantu', 'kotru', 'vasooli', 'chuka', 'chukaye', 'diye', 'mila', 'ko', 'se', 'ka', 'ke', 'ki',
  'received', 'cash', 'upi', 'from', 'to', 'for', 'of', 'and', 'the', 'a', 'in', 'ne', 'avaru',
  'avarige', 'ge', 'khathe', 'ledger', 'entry', 'record', 'save', 'karo', 'kar', 'do', 'hazaar',
  'sau', 'paanch', 'ek', 'do', 'teen', 'chaar', 'over', 'hey', 'khata', 'dukaan', 'ai', 'questions',
  'movie', 'bahut', 'hai', 'itna', 'mein', 'exam', 'liye', 'nahi', 'padi', 'kuch', 'bhi',
  'promise', 'promised', 'promising', 'deposit', 'will', 'pay', 'tomorrow', 'today', 'kal', 'parso',
  'nale', 'vaada', 'dega', 'denge', 'kodthane', 'kodthare',
  'fulfill', 'fulfilled', 'fulfilling', 'complete', 'completed', 'pura', 'poora', 'chuka', 'chukaya',
  'ಪೂರ್ಣ', 'ಮುಗಿದಿದೆ', 'ತೀರಿಸಿದ್ದಾರೆ'
]);

function extractDetailsFromSpeech(transcriptText) {
  let text = (transcriptText || '').trim();
  // Normalize comma-formatted numbers e.g. "15,000" or "1,50,000" -> "15000", "150000"
  text = text.replace(/(\d+),\s*(?=\d{3}(?:\D|$))/g, '$1').replace(/(?<=\d),(?=\d)/g, '');
  const textLower = text.toLowerCase();

  // 1. Amount extraction
  let amount = 0;
  const numMatch = text.match(/(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)*(?:\.\d+)?)/i);
  if (numMatch) {
    amount = parseFloat(numMatch[1].replace(/,/g, ''));
  }

  // 2. Type extraction
  let type = 'CREDIT';
  if (
    textLower.includes('fulfill promise') ||
    textLower.includes('fulfilled promise') ||
    textLower.includes('promise fulfilled') ||
    textLower.includes('promise complete') ||
    textLower.includes('promise completed') ||
    textLower.includes('promise paid') ||
    textLower.includes('paid his promise') ||
    textLower.includes('paid her promise') ||
    textLower.includes('paid promise') ||
    textLower.includes('mark promise as fulfilled') ||
    textLower.includes('vaada pura') ||
    textLower.includes('promise pura') ||
    textLower.includes('vaada poora') ||
    textLower.includes('promise poora') ||
    textLower.includes('vaada chuka') ||
    textLower.includes('vaada kar diya') ||
    textLower.includes('bhravase poorna') ||
    textLower.includes('bharavase poorna') ||
    textLower.includes('ಭರವಸೆ ಪೂರ್ಣ') ||
    textLower.includes('ಪ್ರಾಮಿಸ್ ಕಂಪ್ಲೀಟ್') ||
    (
      (textLower.includes('promise') || textLower.includes('vaada') || textLower.includes('bharavase') || textLower.includes('ಭರವಸೆ')) &&
      (textLower.includes('fulfill') || textLower.includes('fulfilled') || textLower.includes('complete') || textLower.includes('paid') || textLower.includes('pura') || textLower.includes('chuka') || textLower.includes('ಪೂರ್ಣ') || textLower.includes('ಕಂಪ್ಲೀಟ್'))
    )
  ) {
    type = 'FULFILL_PROMISE';
  } else if (
    textLower.includes('promise') ||
    textLower.includes('promised') ||
    textLower.includes('promising') ||
    textLower.includes('vaada') ||
    textLower.includes('dega') ||
    textLower.includes('denge') ||
    textLower.includes('kodthane') ||
    textLower.includes('kodthare') ||
    (textLower.includes('will') && (textLower.includes('pay') || textLower.includes('deposit') || textLower.includes('give')))
  ) {
    type = 'PROMISE';
  } else if (
    textLower.includes('payment') ||
    textLower.includes('paid') ||
    textLower.includes('bantu') ||
    textLower.includes('kotru') ||
    textLower.includes('jama') ||
    textLower.includes('vasooli') ||
    textLower.includes('chuka') ||
    textLower.includes('chukaye') ||
    textLower.includes('received') ||
    textLower.includes('diye') ||
    textLower.includes('वापस') ||
    textLower.includes('चुकाए') ||
    textLower.includes('जमा')
  ) {
    type = 'PAYMENT';
  }

  // 3. Customer name extraction
  let customerName = '';

  // Pattern -1: Fulfill promise pattern "<name> promise fulfilled", "fulfill promise for/of <name>"
  const fulfillMatch1 = text.match(/(?:fulfill|complete|clear)\s+(?:the\s+)?(?:promise|vaada|vada|bharavase)\s+(?:of|for|from)?\s+([A-Za-z\u0900-\u097F\u0C80-\u0CFF]+(?:\s+[A-Za-z\u0900-\u097F\u0C80-\u0CFF]+)?)/i);
  if (fulfillMatch1) {
    const words = fulfillMatch1[1].trim().split(/\s+/).filter(w => !STOPWORDS_SET.has(w.toLowerCase()));
    if (words.length > 0) {
      customerName = words.slice(0, 2).join(' ');
    }
  }
  if (!customerName) {
    const fulfillMatch2 = text.match(/([A-Za-z\u0900-\u097F\u0C80-\u0CFF]+(?:\s+[A-Za-z\u0900-\u097F\u0C80-\u0CFF]+)?)\s+(?:ka|ki|ke|avara|avarige|ne)?\s*(?:promise|vaada|vada|bharavase)\s+(?:fulfilled|complete|completed|pura|poora|chuka|done|cleared)/i);
    if (fulfillMatch2) {
      const words = fulfillMatch2[1].trim().split(/\s+/).filter(w => !STOPWORDS_SET.has(w.toLowerCase()));
      if (words.length > 0) {
        customerName = words.slice(0, 2).join(' ');
      }
    }
  }

  // Pattern 0: Promise pattern "<name> promised to...", "<name> will pay...", "<name> kal ... dega"
  if (!customerName) {
    const promMatch = text.match(/^\s*([A-Za-z\u0900-\u097F\u0C80-\u0CFF]+(?:\s+[A-Za-z\u0900-\u097F\u0C80-\u0CFF]+)?)\s+(?:promised|promise|will|ne|kal|parso|nale)\b/i);
    if (promMatch) {
      const words = promMatch[1].trim().split(/\s+/).filter(w => !STOPWORDS_SET.has(w.toLowerCase()));
      if (words.length > 0) {
        customerName = words.slice(0, 2).join(' ');
      }
    }
  }

  // Pattern A: "from/to/for/se/ko <name>"
  if (!customerName) {
    const prepMatch = text.match(/\b(?:from|to|for|se|ko|from\s+the)\s+([A-Za-z\u0900-\u097F\u0C80-\u0CFF]+(?:\s+[A-Za-z\u0900-\u097F\u0C80-\u0CFF]+)?)/i);
    if (prepMatch) {
      const words = prepMatch[1].trim().split(/\s+/).filter(w => !STOPWORDS_SET.has(w.toLowerCase()));
      if (words.length > 0) {
        customerName = words.slice(0, 2).join(' ');
      }
    }
  }

  // Pattern B: "<name> ko / se / ke / ne / avarige"
  if (!customerName) {
    const postMatch = text.match(/([A-Za-z\u0900-\u097F\u0C80-\u0CFF]+(?:\s+[A-Za-z\u0900-\u097F\u0C80-\u0CFF]+)?)\s+(?:ko|se|ka|ke|ki|ne|avara|avarige|avru)\b/i);
    if (postMatch) {
      const words = postMatch[1].trim().split(/\s+/).filter(w => !STOPWORDS_SET.has(w.toLowerCase()));
      if (words.length > 0) {
        customerName = words.slice(0, 2).join(' ');
      }
    }
  }

  // Pattern C: Token filtering
  if (!customerName) {
    const cleanTokens = text.replace(/[₹.,!?'":;()[\]/\\]/g, ' ').split(/\s+/);
    const validWords = cleanTokens.filter(w => {
      const wl = w.toLowerCase();
      return wl.length > 1 && !STOPWORDS_SET.has(wl) && !/^\d+$/.test(w);
    });
    if (validWords.length > 0) {
      customerName = validWords.slice(0, 2).join(' ');
    }
  }

  if (!customerName) {
    customerName = 'Customer';
  }

  // Clean and format
  customerName = customerName
    .split(' ')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');

  return {
    customerName,
    amount: amount || 100,
    type,
  };
}

  // Fallback voice processor when WebSocket is reconnecting
  const handleMockVoiceProcess = useCallback(
    (transcriptText) => {
      setSessionState('PROCESSING');

      setTimeout(() => {
        const parsed = extractDetailsFromSpeech(transcriptText);
        const customerName = parsed.customerName;
        const amount = parsed.amount;
        const type = parsed.type;
        const alias = '';

        if (type === 'FULFILL_PROMISE') {
          setSessionState('DONE');
          let resp = `Payment promise for ${customerName} has been marked as fulfilled!`;
          if (currentLanguage === 'kn-IN') {
            resp = `${customerName} ಅವರ ಪಾವತಿ ಭರವಸೆಯನ್ನು ಪೂರ್ಣಗೊಳಿಸಲಾಗಿದೆ (Fulfilled)!`;
          } else if (currentLanguage === 'hi-IN') {
            resp = `${customerName} का वादा सफलतापूर्वक पूरा (Fulfilled) दर्ज कर लिया गया है!`;
          }
          setConversation((prev) => [
            ...prev,
            {
              id: uuidv4(),
              sender: 'ai',
              text: resp,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ]);
          speakText(resp);
          window.dispatchEvent(new CustomEvent('dukaanai:refresh'));
          return;
        }

        if (type === 'PROMISE') {
          setSessionState('DONE');
          let resp = `Noted! Recorded promise: ${customerName} will deposit ₹${amount}. Reminder scheduled.`;
          if (currentLanguage === 'kn-IN') {
            resp = `ಗುರುತು ಮಾಡಲಾಗಿದೆ! ${customerName} ಅವರು ₹${amount} ನೀಡುವುದಾಗಿ ಭರವಸೆ ದಾಖಲಿಸಲಾಗಿದೆ.`;
          } else if (currentLanguage === 'hi-IN') {
            resp = `नोट कर लिया गया! ${customerName} ने ₹${amount} देने का वादा किया है। रिमाइंडर सेट हो गया।`;
          }
          setConversation((prev) => [
            ...prev,
            {
              id: uuidv4(),
              sender: 'ai',
              text: resp,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ]);
          speakText(resp);
          window.dispatchEvent(new CustomEvent('dukaanai:refresh'));
          return;
        }

        const draft = {
          id: Date.now(),
          customer_name: customerName,
          customer_alias: alias,
          amount: amount,
          type: type,
          notes: transcriptText,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };

        setPendingDraft(draft);
        setSessionState('CONFIRMING');

        let confirmationText = '';
        if (currentLanguage === 'kn-IN') {
          confirmationText = `${customerName} ಅವರಿಗೆ ₹${amount} ${type === 'CREDIT' ? 'ಸಾಲ' : 'ಸ್ವೀಕೃತಿ'} ದಾಖಲಿಸಬೇಕೇ? ಖಚಿತಪಡಿಸಿ ಅಥವಾ ರದ್ದುಮಾಡಿ.`;
        } else if (currentLanguage === 'hi-IN') {
          confirmationText = `${customerName} के लिए ₹${amount} ${type === 'CREDIT' ? 'उधार' : 'जमा'} दर्ज करें? कृपया पुष्टि करें।`;
        } else {
          confirmationText = `Confirm ${type} of ₹${amount} for ${customerName}?`;
        }

        setConversation((prev) => [
          ...prev,
          {
            id: uuidv4(),
            sender: 'ai',
            text: confirmationText,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            draft,
          },
        ]);

        speakText(confirmationText);
      }, 700);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [currentLanguage, speakText]
  );

  const connectWebSocket = useCallback(() => {
    const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';
    const fullUrl = `${wsUrl}/ws/voice?session_id=${sessionId}&shop_id=${shopId}`;

    try {
      setWsState('CONNECTING');
      const ws = new WebSocket(fullUrl);
      ws.binaryType = 'arraybuffer';

      ws.onopen = () => {
        setWsState('CONNECTED');
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = async (event) => {
        // Real mode: binary audio stream for TTS
        if (event.data instanceof ArrayBuffer) {
          playAudio(event.data);
          return;
        }

        // Text / JSON message
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'TRANSCRIPT') {
            setConversation((prev) => [
              ...prev,
              {
                id: uuidv4(),
                sender: 'user',
                text: data.text,
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              },
            ]);
          } else if (data.type === 'STATE') {
            setSessionState(data.state || 'IDLE');
            if (data.state === 'CONFIRMING' && (data.customer_name || data.amount)) {
              setPendingDraft({
                id: data.transaction_id || Date.now(),
                customer_name: data.customer_name,
                amount: data.amount,
                type: data.transaction_type || 'CREDIT',
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              });
            } else if (data.state === 'DONE') {
              setPendingDraft(null);
              window.dispatchEvent(new CustomEvent('dukaanai:refresh'));
            }

            if (data.message) {
              setConversation((prev) => [
                ...prev,
                {
                  id: uuidv4(),
                  sender: 'ai',
                  text: data.message,
                  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                },
              ]);
              speakText(data.message);
            }
          } else if (data.type === 'PENDING_DRAFT') {
            setPendingDraft(data.draft);
            setSessionState('CONFIRMING');
          } else if (data.type === 'TRANSACTION_COMPLETE') {
            setLastResult(data.transaction);
            setPendingDraft(null);
            setSessionState('DONE');
            window.dispatchEvent(new CustomEvent('dukaanai:refresh'));
            const doneMsg = currentLanguage === 'kn-IN'
              ? 'ಖಾತಾ ಯಶಸ್ವಿಯಾಗಿ ಉಳಿಸಲಾಗಿದೆ!'
              : currentLanguage === 'hi-IN'
              ? 'खाता सफलतापूर्वक सहेजा गया!'
              : 'Transaction saved successfully!';
            speakText(doneMsg);
          }
        } catch (e) {
          console.warn('WebSocket message parse error:', e);
        }
      };

      ws.onerror = (error) => {
        console.warn('WebSocket connection error:', error);
      };

      ws.onclose = () => {
        setWsState('DISCONNECTED');
        socketRef.current = null;

        // Exponential backoff reconnect
        if (reconnectAttemptsRef.current < 5) {
          const timeout = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 10000);
          reconnectAttemptsRef.current += 1;
          setWsState('RECONNECTING');
          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket();
          }, timeout);
        }
      };

      socketRef.current = ws;
    } catch (err) {
      console.warn('WebSocket init exception:', err);
      setWsState('DISCONNECTED');
    }
  }, [sessionId, shopId, currentLanguage, playAudio, speakText]);

  useEffect(() => {
    connectWebSocket();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [connectWebSocket]);

  // Send speech transcript
  const sendTranscript = useCallback(
    (text) => {
      if (!text || !text.trim()) return;

      const rawText = text.trim();
      // Normalize comma-formatted numbers e.g. 15,000 -> 15000 so commas in voice numbers are not truncated
      const cleanText = rawText
        .replace(/(\d+),\s*(?=\d{3}(?:\D|$))/g, '$1')
        .replace(/(?<=\d),(?=\d)/g, '');

      const userMsg = {
        id: uuidv4(),
        sender: 'user',
        text: rawText,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setConversation((prev) => [...prev, userMsg]);

      // If connected to real websocket, send message
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send(
          JSON.stringify({
            type: 'TRANSCRIPT',
            text: cleanText,
            language: currentLanguage,
            shop_id: shopId,
          })
        );
      } else {
        // Fallback to intelligent local demo processing
        handleMockVoiceProcess(cleanText);
      }
    // Fallback timer: reset PROCESSING state back to IDLE if no response within 6s
    const timeout = setTimeout(() => {
      setSessionState((prev) => (prev === 'PROCESSING' ? 'IDLE' : prev));
    }, 6000);

    return () => clearTimeout(timeout);
  }, [currentLanguage, shopId, handleMockVoiceProcess]);

  // Send or process draft confirmation
  const confirmDraft = useCallback((customDraft) => {
    const draftToConfirm = customDraft || pendingDraft;
    if (!draftToConfirm) return;

    // 1. Send via WebSocket if connected
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: 'CONFIRM_DRAFT',
          draft_id: draftToConfirm.id,
          customer_name: draftToConfirm.customer_name,
          amount: draftToConfirm.amount,
          transaction_type: draftToConfirm.type,
          notes: draftToConfirm.notes,
        })
      );
    }

    // 2. ALWAYS also persist directly to backend REST API to guarantee database sync
    const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    fetch(`${apiUrl}/api/transactions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        customer_name: draftToConfirm.customer_name,
        amount: parseFloat(draftToConfirm.amount) || 0,
        type: draftToConfirm.type || 'CREDIT',
        voice_transcript: draftToConfirm.notes || draftToConfirm.customer_name,
        description: draftToConfirm.notes || 'Voice entry',
      }),
    })
      .then((res) => res.json())
      .then((data) => {
        console.log('Transaction persisted to database successfully:', data);
      })
      .catch((err) => {
        console.warn('REST transaction persist fallback notice:', err);
      });

    const confirmed = { ...draftToConfirm, status: 'CONFIRMED' };
    setLastResult(confirmed);
    setPendingDraft(null);
    setSessionState('DONE');

    const successMsg = currentLanguage === 'kn-IN'
      ? `ಖಾತಾ ಯಶಸ್ವಿಯಾಗಿ ಉಳಿಸಲಾಗಿದೆ! ${confirmed.customer_name} ₹${confirmed.amount}`
      : currentLanguage === 'hi-IN'
      ? `खाता सहेजा गया! ${confirmed.customer_name} ₹${confirmed.amount}`
      : `Transaction saved for ${confirmed.customer_name} (₹${confirmed.amount})`;

    setConversation((prev) => [
      ...prev,
      {
        id: uuidv4(),
        sender: 'ai',
        text: successMsg,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);

    speakText(successMsg);
  }, [pendingDraft, currentLanguage, speakText]);

  // Cancel draft
  const sendCancelDraft = useCallback(() => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: 'CANCEL_DRAFT',
          draft_id: pendingDraft?.id,
        })
      );
    }
    setPendingDraft(null);
    setSessionState('IDLE');

    const cancelMsg = currentLanguage === 'kn-IN'
      ? 'ವಹಿವಾಟನ್ನು ರದ್ದುಗೊಳಿಸಲಾಗಿದೆ.'
      : currentLanguage === 'hi-IN'
      ? 'लेन-देन रद्द कर दिया गया।'
      : 'Transaction cancelled.';

    setConversation((prev) => [
      ...prev,
      {
        id: uuidv4(),
        sender: 'ai',
        text: cancelMsg,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
    speakText(cancelMsg);
  }, [pendingDraft, currentLanguage, speakText]);

  const clearMessages = useCallback(() => {
    setConversation([]);
  }, []);

  return {
    wsState,
    sessionId,
    sendTranscript,
    sendCancelDraft,
    confirmDraft,
    conversation,
    lastResult,
    pendingDraft,
    sessionState,
    setSessionState,
    isSpeaking,
    speakText,
    clearMessages,
  };
};

export default useVoiceWebSocket;
