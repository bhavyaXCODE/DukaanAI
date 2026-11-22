import React, { useState, useEffect } from 'react';
import VoiceButton from '../components/VoiceButton';
import ConversationPanel from '../components/ConversationPanel';
import ConfirmationModal from '../components/ConfirmationModal';
import useSpeechRecognition from '../hooks/useSpeechRecognition';
import useVoiceWebSocket from '../hooks/useVoiceWebSocket';
import { useApp } from '../context/AppContext';
import { formatINR } from '../services/api';
import './VoiceKhata.css';

const VoiceKhata = () => {
  const { currentLanguage, setCurrentLanguage, shopInfo, incrementRefresh } = useApp();

  const {
    wsState,
    conversation,
    pendingDraft,
    sessionState,
    setSessionState,
    sendTranscript,
    confirmDraft,
    sendCancelDraft,
    clearMessages,
  } = useVoiceWebSocket(shopInfo?.id || 1, currentLanguage);

  const {
    isListening,
    transcript,
    isSupported,
    startListening,
    stopListening,
    resetTranscript,
    cancelListening,
  } = useSpeechRecognition(currentLanguage);

  const [modalOpen, setModalOpen] = useState(false);
  const [successToast, setSuccessToast] = useState(null);
  const [manualText, setManualText] = useState('');

  // Synchronize listening state with voice button state
  useEffect(() => {
    if (isListening) {
      setSessionState('LISTENING');
    }
  }, [isListening, setSessionState]);

  // When pendingDraft exists and sessionState is CONFIRMING, show modal
  useEffect(() => {
    if (pendingDraft && sessionState === 'CONFIRMING') {
      setModalOpen(true);
    } else {
      setModalOpen(false);
    }
  }, [pendingDraft, sessionState]);

  // When transaction/promise finishes, refresh global data
  useEffect(() => {
    if (sessionState === 'DONE') {
      incrementRefresh();
    }
  }, [sessionState, incrementRefresh]);

  // Clean Toggle: Click once to record, click again to stop & process
  const handleVoiceToggle = () => {
    if (isListening) {
      stopListening();
      if (transcript.trim()) {
        sendTranscript(transcript.trim());
        resetTranscript();
      } else {
        setSessionState('IDLE');
      }
    } else {
      resetTranscript();
      startListening();
    }
  };

  // Immediate Cancel: stop mic, clear transcript, discard bad speech input
  const handleCancelVoiceInput = () => {
    cancelListening();
    resetTranscript();
    setSessionState('IDLE');
    if (pendingDraft) {
      sendCancelDraft();
    }
  };

  // Quick prompt sample click handler
  const handleQuickSample = (sample) => {
    sendTranscript(sample);
  };

  const handleManualSubmit = (e) => {
    e.preventDefault();
    if (manualText.trim()) {
      sendTranscript(manualText.trim());
      setManualText('');
    }
  };

  const handleModalConfirm = () => {
    confirmDraft();
    setModalOpen(false);
    setSuccessToast('Transaction confirmed and saved to ledger!');
    setTimeout(() => setSuccessToast(null), 3000);
    setTimeout(() => incrementRefresh(), 1000);
  };

  const handleModalCancel = () => {
    sendCancelDraft();
    setModalOpen(false);
  };

  const handleModalCorrect = (updatedDraft) => {
    confirmDraft(updatedDraft);
    setModalOpen(false);
    setSuccessToast('Updated transaction saved to ledger!');
    setTimeout(() => setSuccessToast(null), 3000);
    setTimeout(() => incrementRefresh(), 1000);
  };

  const getStatusText = () => {
    if (isListening) return 'Listening... Click mic again when done speaking';
    if (sessionState === 'PROCESSING') return 'DukaanAI is processing with AI...';
    if (sessionState === 'CONFIRMING') return 'Verifying transaction details...';
    if (sessionState === 'DONE') return 'Khata entry successfully saved!';
    return 'Tap the microphone and start speaking';
  };

  const samplePrompts = {
    'kn-IN': [
      'ಸುರೇಶ್ ಅವರಿಗೆ 250 ರೂಪಾಯಿ ಸಾಲ',
      'ಲಕ್ಷ್ಮಮ್ಮ ಅವರಿಂದ 500 ರೂಪಾಯಿ ಜಮಾ ಬಂತು',
      'ಗೋವಿಂದ್ ನಾಳೆ 400 ಕೊಡುವುದಾಗಿ ಭರವಸೆ ನೀಡಿದ್ದಾರೆ',
      'ರಮೇಶ್ ಭರವಸೆ ಪೂರ್ಣಗೊಳಿಸಿ',
      'ಇಂದು ಯಾರು ಹಣ ಕೊಡಬೇಕು?',
    ],
    'hi-IN': [
      'सुरेश कुमार को 250 रुपये का उधार दिया',
      'लक्ष्मी जी से 500 रुपये जमा प्राप्त हुए',
      'रमेश ने 25 तारीख को 500 देने का वादा किया',
      'रमेश का वादा पूरा हो गया',
      'आज किसका पेमेंट आना है?',
    ],
    'en-IN': [
      'Credit 250 to Suresh Kumar',
      'Received payment 500 from Lakshmamma',
      'Ramesh promised to deposit 500 on 25 Nov',
      'Fulfill Ramesh promise',
      'Who has to pay today?',
    ],
  };

  return (
    <div className="voice-khata-page animate-fadeIn">
      {/* Success Toast */}
      {successToast && (
        <div className="toast-success animate-slideUp">
          <span className="toast-icon">✓</span>
          <span>{successToast}</span>
        </div>
      )}

      {/* Header */}
      <div className="voice-header-card">
        <div className="header-titles">
          <div className="flex items-center gap-2">
            <span className="page-icon">🎙️</span>
            <h1 className="page-title">Voice Khata</h1>
            <div className={`ws-badge ${wsState.toLowerCase()}`}>
              <span className="ws-dot" />
              <span>{wsState === 'CONNECTED' ? 'Live AI' : 'Offline / Demo'}</span>
            </div>
          </div>
          <p className="page-subtitle">
            Hands-free kirana accounting. Speak naturally in your native language.
          </p>
        </div>

        {/* Language selector tabs */}
        <div className="language-selector-tabs">
          <button
            type="button"
            className={`lang-tab ${currentLanguage === 'kn-IN' ? 'active' : ''}`}
            onClick={() => setCurrentLanguage('kn-IN')}
          >
            <span className="lang-icon">ಕ</span>
            <span className="lang-name">ಕನ್ನಡ</span>
          </button>
          <button
            type="button"
            className={`lang-tab ${currentLanguage === 'hi-IN' ? 'active' : ''}`}
            onClick={() => setCurrentLanguage('hi-IN')}
          >
            <span className="lang-icon">अ</span>
            <span className="lang-name">हिंदी</span>
          </button>
          <button
            type="button"
            className={`lang-tab ${currentLanguage === 'en-IN' ? 'active' : ''}`}
            onClick={() => setCurrentLanguage('en-IN')}
          >
            <span className="lang-icon">En</span>
            <span className="lang-name">English</span>
          </button>
        </div>
      </div>

      {/* AI Disclosure Banner */}
      <div className="ai-disclosure-banner">
        <span className="disclosure-icon">🤖</span>
        <span className="disclosure-text">
          <strong>AI Voice Assistant:</strong> All speech is converted to draft transactions with instant verification. Click the microphone to speak, click again to finish.
        </span>
      </div>

      {/* Pending Draft Banner */}
      {pendingDraft && (
        <div className="pending-draft-banner animate-slideUp">
          <div className="draft-banner-content">
            <span className="draft-pulse-icon">⏳</span>
            <div>
              <h4 className="draft-banner-title">Pending Unconfirmed Draft</h4>
              <p className="draft-banner-details">
                {pendingDraft.customer_name} — <strong>{formatINR(pendingDraft.amount)}</strong> ({pendingDraft.type})
              </p>
            </div>
          </div>
          <div className="draft-banner-buttons">
            <button
              type="button"
              className="btn btn-sm btn-confirm"
              onClick={handleModalConfirm}
            >
              Confirm
            </button>
            <button
              type="button"
              className="btn btn-sm btn-cancel"
              onClick={handleModalCancel}
            >
              Discard
            </button>
          </div>
        </div>
      )}

      {/* Main Grid: Voice Hub on Left, Conversation on Right */}
      <div className="voice-main-layout">
        {/* Left Column: Voice Hub */}
        <div className="voice-hub-panel">
          <div className="voice-hub-center">
            {/* Animated Mic Button */}
            <VoiceButton
              state={isListening ? 'listening' : sessionState === 'PROCESSING' ? 'processing' : sessionState.toLowerCase()}
              onClick={handleVoiceToggle}
            />

            {/* Status text */}
            <h3 className="voice-status-title">{getStatusText()}</h3>
            <p className="voice-status-hint">
              {isListening
                ? 'Click mic to stop & save, or click Cancel below to discard wrong input'
                : 'Click mic or pick a quick sample below'}
            </p>

            {/* Explicit Cancel / Discard Action Bar while listening or when wrong input is present */}
            {(isListening || transcript || pendingDraft) && (
              <div className="voice-action-bar animate-fadeIn">
                <button
                  type="button"
                  className="btn-cancel-voice"
                  onClick={handleCancelVoiceInput}
                  title="Cancel and remove wrong speech input"
                >
                  <span className="cancel-icon">✕</span>
                  <span>{isListening ? 'Cancel Recording' : 'Remove / Discard Input'}</span>
                </button>
                {isListening && transcript.trim() && (
                  <button
                    type="button"
                    className="btn-process-voice"
                    onClick={handleVoiceToggle}
                    title="Done speaking, process this input"
                  >
                    <span>✓ Done & Process</span>
                  </button>
                )}
              </div>
            )}

            {/* Live Transcript Display */}
            <div className={`live-transcript-box ${isListening ? 'active' : ''}`}>
              <div className="transcript-header">
                <div className="flex items-center gap-2">
                  <span className="rec-dot" />
                  <span>Live Speech Transcript</span>
                </div>
                {(transcript || isListening) && (
                  <button
                    type="button"
                    className="btn-clear-transcript"
                    onClick={handleCancelVoiceInput}
                    title="Remove wrong input"
                  >
                    ✕ Remove Input
                  </button>
                )}
              </div>
              <div className="transcript-text">
                {transcript || (
                  <span className="placeholder-text">
                    {isListening ? 'Listening for speech...' : 'Your speech will appear here in real-time...'}
                  </span>
                )}
              </div>
            </div>

            {!isSupported && (
              <div className="speech-support-warning">
                ⚠️ Web Speech API not detected in this browser window. You can use manual input or the quick sample buttons below!
              </div>
            )}
          </div>

          {/* Quick Voice Prompt Shortcuts */}
          <div className="quick-prompts-section">
            <span className="quick-prompts-label">Try speaking (or click to simulate):</span>
            <div className="prompts-grid">
              {(samplePrompts[currentLanguage] || samplePrompts['kn-IN']).map((sample, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="sample-prompt-pill"
                  onClick={() => handleQuickSample(sample)}
                >
                  <span className="pill-quote">"</span>
                  <span>{sample}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Manual Text Simulation Fallback */}
          <form className="manual-input-bar" onSubmit={handleManualSubmit}>
            <input
              type="text"
              placeholder="Or type voice text here (e.g., 'Suresh 250 credit')..."
              value={manualText}
              onChange={(e) => setManualText(e.target.value)}
            />
            <button type="submit" className="manual-send-btn">
              Send 🚀
            </button>
          </form>
        </div>

        {/* Right Column: Conversation Stream */}
        <div className="voice-conversation-column">
          <ConversationPanel
            messages={conversation}
            onClear={clearMessages}
            title="Session Transcript & Ledger Log"
          />
        </div>
      </div>

      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={modalOpen}
        transaction={pendingDraft}
        onConfirm={handleModalConfirm}
        onCancel={handleModalCancel}
        onCorrect={handleModalCorrect}
      />
    </div>
  );
};

export default VoiceKhata;
