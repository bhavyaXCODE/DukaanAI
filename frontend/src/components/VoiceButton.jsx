import React from 'react';
import './VoiceButton.css';

const VoiceButton = ({
  state = 'idle', // 'idle' | 'listening' | 'processing' | 'confirming' | 'error'
  onClick,
  disabled = false,
}) => {
  const getButtonContent = () => {
    switch (state) {
      case 'listening':
        return (
          <>
            <div className="pulse-ring ring-1" />
            <div className="pulse-ring ring-2" />
            <div className="pulse-ring ring-3" />
            <span className="voice-icon mic-active">🎙️</span>
          </>
        );
      case 'processing':
        return (
          <>
            <div className="spinner-ring" />
            <span className="voice-icon spin-icon">⚡</span>
          </>
        );
      case 'confirming':
        return (
          <>
            <div className="confirm-pulse-ring" />
            <span className="voice-icon">❓</span>
          </>
        );
      case 'error':
        return <span className="voice-icon">⚠️</span>;
      case 'idle':
      default:
        return <span className="voice-icon">🎙️</span>;
    }
  };

  return (
    <div className="voice-button-container">
      <button
        type="button"
        className={`voice-button state-${state}`}
        onClick={onClick}
        disabled={disabled || state === 'processing'}
        aria-label={`Microphone button - ${state}`}
      >
        {getButtonContent()}
      </button>
    </div>
  );
};

export default VoiceButton;
