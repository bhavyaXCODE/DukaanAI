import React, { createContext, useContext, useState, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';

const VoiceContext = createContext();

export const VoiceProvider = ({ children }) => {
  const [sessionState, setSessionState] = useState('IDLE'); // IDLE, LISTENING, PROCESSING, CONFIRMING, DONE, ERROR
  const [conversationHistory, setConversationHistory] = useState([
    {
      id: 'welcome-1',
      sender: 'ai',
      text: 'ನಮಸ್ಕಾರ! ದುಕಾನ್ AI ಗೆ ಸುಸ್ವಾಗತ. ನೀವು ಯಾರಿಗಾದರೂ ಸಾಲ ನೀಡಿದ್ದೀರಾ ಅಥವಾ ಹಣ ಸ್ವೀಕರಿಸಿದ್ದೀರಾ? ಮೈಕ್ ಬಟನ್ ಒತ್ತಿ ಹೇಳಿ.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [currentDraft, setCurrentDraft] = useState(null);
  const [pendingDraft, setPendingDraft] = useState(null);

  const addMessage = useCallback((sender, text, extra = {}) => {
    const newMessage = {
      id: uuidv4(),
      sender,
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      ...extra,
    };
    setConversationHistory((prev) => [...prev, newMessage]);
  }, []);

  const clearConversation = useCallback(() => {
    setConversationHistory([]);
    setCurrentDraft(null);
    setPendingDraft(null);
    setSessionState('IDLE');
  }, []);

  const value = {
    sessionState,
    setSessionState,
    conversationHistory,
    setConversationHistory,
    currentDraft,
    setCurrentDraft,
    pendingDraft,
    setPendingDraft,
    addMessage,
    clearConversation,
  };

  return <VoiceContext.Provider value={value}>{children}</VoiceContext.Provider>;
};

export const useVoice = () => {
  const context = useContext(VoiceContext);
  if (!context) {
    throw new Error('useVoice must be used within a VoiceProvider');
  }
  return context;
};

export default VoiceContext;
