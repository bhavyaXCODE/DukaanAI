import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import './Settings.css';

const Settings = () => {
  const {
    shopInfo,
    setShopInfo,
    currentLanguage,
    setCurrentLanguage,
    demoMode,
    setDemoMode,
  } = useApp();

  const [savedNotification, setSavedNotification] = useState(false);

  // Check browser speech recognition & synthesis capabilities
  const hasSpeechRecognition =
    typeof window !== 'undefined' &&
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window);
  const hasSpeechSynthesis =
    typeof window !== 'undefined' && 'speechSynthesis' in window;
  const hasAudioContext =
    typeof window !== 'undefined' &&
    ('AudioContext' in window || 'webkitAudioContext' in window);

  const handleLanguageChange = (lang) => {
    setCurrentLanguage(lang);
    setSavedNotification(true);
    setTimeout(() => setSavedNotification(false), 2500);
  };

  const handleShopNameChange = (e) => {
    setShopInfo((prev) => ({ ...prev, name: e.target.value }));
  };

  const handleOwnerNameChange = (e) => {
    setShopInfo((prev) => ({ ...prev, ownerName: e.target.value }));
  };

  return (
    <div className="settings-page animate-fadeIn">
      {savedNotification && (
        <div className="toast-success animate-slideUp">
          <span className="toast-icon">✓</span>
          <span>Settings saved successfully!</span>
        </div>
      )}

      {/* Header */}
      <div className="settings-header">
        <div className="flex items-center gap-2">
          <span className="page-icon">⚙️</span>
          <h1 className="page-title">Settings & Preferences</h1>
        </div>
        <p className="page-subtitle">
          Configure shop details, default voice language, audio pipelines, and system modes
        </p>
      </div>

      <div className="settings-layout">
        {/* Left Column: Config Sections */}
        <div className="settings-main-column">
          {/* Section 1: Language Preference */}
          <div className="settings-card">
            <div className="settings-card-header">
              <span className="card-header-icon">🌐</span>
              <div>
                <h3 className="card-title">Default Voice Language</h3>
                <p className="card-subtitle">
                  Primary language used for speech recognition, NLP parsing, and audio feedback
                </p>
              </div>
            </div>

            <div className="language-options-group">
              <label
                className={`language-option-card ${currentLanguage === 'kn-IN' ? 'selected' : ''}`}
                onClick={() => handleLanguageChange('kn-IN')}
              >
                <input
                  type="radio"
                  name="language"
                  checked={currentLanguage === 'kn-IN'}
                  onChange={() => {}}
                />
                <div className="lang-details">
                  <div className="lang-title-row">
                    <span className="lang-title font-bold">ಕನ್ನಡ (Kannada)</span>
                    <span className="lang-code-pill">kn-IN</span>
                  </div>
                  <p className="lang-desc">
                    Default for Karnataka kirana stores. Full STT/TTS voice prompt support.
                  </p>
                  <div className="lang-preview-sample">
                    ಉದಾಹರಣೆ: "ಸುರೇಶ್ ಅವರಿಗೆ 250 ರೂಪಾಯಿ ಸಾಲ ಕೊಟ್ಟಿರುವೆ"
                  </div>
                </div>
              </label>

              <label
                className={`language-option-card ${currentLanguage === 'hi-IN' ? 'selected' : ''}`}
                onClick={() => handleLanguageChange('hi-IN')}
              >
                <input
                  type="radio"
                  name="language"
                  checked={currentLanguage === 'hi-IN'}
                  onChange={() => {}}
                />
                <div className="lang-details">
                  <div className="lang-title-row">
                    <span className="lang-title font-bold">हिंदी (Hindi)</span>
                    <span className="lang-code-pill">hi-IN</span>
                  </div>
                  <p className="lang-desc">
                    National vernacular support for North & Central Indian kirana shops.
                  </p>
                  <div className="lang-preview-sample">
                    उदाहरण: "सुरेश कुमार को 250 रुपये का उधार दिया"
                  </div>
                </div>
              </label>

              <label
                className={`language-option-card ${currentLanguage === 'en-IN' ? 'selected' : ''}`}
                onClick={() => handleLanguageChange('en-IN')}
              >
                <input
                  type="radio"
                  name="language"
                  checked={currentLanguage === 'en-IN'}
                  onChange={() => {}}
                />
                <div className="lang-details">
                  <div className="lang-title-row">
                    <span className="lang-title font-bold">English (Indian)</span>
                    <span className="lang-code-pill">en-IN</span>
                  </div>
                  <p className="lang-desc">
                    Indian English terminology and currency denominations.
                  </p>
                  <div className="lang-preview-sample">
                    Example: "Credit 250 rupees to Suresh Kumar"
                  </div>
                </div>
              </label>
            </div>
          </div>

          {/* Section 2: Shop Information */}
          <div className="settings-card">
            <div className="settings-card-header">
              <span className="card-header-icon">🏪</span>
              <div>
                <h3 className="card-title">Shop Information</h3>
                <p className="card-subtitle">Store identity and counter metadata</p>
              </div>
            </div>

            <div className="shop-info-form">
              <div className="form-group">
                <label>Shop / Dukaan Name</label>
                <input
                  type="text"
                  value={shopInfo.name}
                  onChange={handleShopNameChange}
                  placeholder="Enter store name"
                />
              </div>

              <div className="form-row-2">
                <div className="form-group">
                  <label>Owner Name</label>
                  <input
                    type="text"
                    value={shopInfo.ownerName}
                    onChange={handleOwnerNameChange}
                    placeholder="Owner name"
                  />
                </div>
                <div className="form-group">
                  <label>Username (System ID)</label>
                  <input
                    type="text"
                    value={`@${shopInfo.username}`}
                    disabled
                    className="input-disabled"
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Address / Landmark</label>
                <input
                  type="text"
                  value={shopInfo.address || '4th Main, Malleshwaram, Bengaluru'}
                  disabled
                  className="input-disabled"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Voice Diagnostics & About */}
        <div className="settings-sidebar-column">
          {/* Mode Indicator Card */}
          <div className="settings-card mode-card">
            <div className="settings-card-header">
              <span className="card-header-icon">⚡</span>
              <div>
                <h3 className="card-title">Operating Mode</h3>
                <p className="card-subtitle">Runtime environment configuration</p>
              </div>
            </div>

            <div className="mode-status-container">
              <div className="mode-toggle-row">
                <div className="flex items-center gap-2">
                  <span className="mode-indicator-dot active" />
                  <span className="mode-label font-semibold">
                    {demoMode ? 'Mock Voice / Demo Mode' : 'Production Backend Mode'}
                  </span>
                </div>
                <button
                  type="button"
                  className={`toggle-switch ${demoMode ? 'active' : ''}`}
                  onClick={() => setDemoMode(!demoMode)}
                  title="Toggle demo mode"
                >
                  <span className="switch-thumb" />
                </button>
              </div>

              <p className="mode-explainer">
                {demoMode
                  ? 'In Demo Mode, DukaanAI utilizes client-side Web Speech API & browser SpeechSynthesis for instant zero-latency testing.'
                  : 'In Production Mode, audio is streamed directly to the backend Python FastAPI NLP engine over WebSocket.'}
              </p>
            </div>
          </div>

          {/* Voice System Diagnostics */}
          <div className="settings-card">
            <div className="settings-card-header">
              <span className="card-header-icon">🎙️</span>
              <div>
                <h3 className="card-title">Voice System Diagnostics</h3>
                <p className="card-subtitle">Browser hardware & API support</p>
              </div>
            </div>

            <div className="diagnostics-list">
              <div className="diag-row">
                <span className="diag-name">Web Speech Recognition (STT):</span>
                <span className={`diag-badge ${hasSpeechRecognition ? 'ok' : 'missing'}`}>
                  {hasSpeechRecognition ? '✓ Supported' : '✕ Unsupported'}
                </span>
              </div>

              <div className="diag-row">
                <span className="diag-name">Browser SpeechSynthesis (TTS):</span>
                <span className={`diag-badge ${hasSpeechSynthesis ? 'ok' : 'missing'}`}>
                  {hasSpeechSynthesis ? '✓ Supported' : '✕ Unsupported'}
                </span>
              </div>

              <div className="diag-row">
                <span className="diag-name">Web AudioContext:</span>
                <span className={`diag-badge ${hasAudioContext ? 'ok' : 'missing'}`}>
                  {hasAudioContext ? '✓ Supported' : '✕ Unsupported'}
                </span>
              </div>

              <div className="diag-row">
                <span className="diag-name">WebSocket Connectivity:</span>
                <span className="diag-badge ok">✓ Active Client</span>
              </div>
            </div>
          </div>

          {/* About Section */}
          <div className="settings-card about-card">
            <div className="about-brand-row">
              <span className="about-logo">🎙️</span>
              <div>
                <h4 className="about-app-name">DukaanAI</h4>
                <p className="about-tag">The Intelligent Voice Khata v1.0.0</p>
              </div>
            </div>

            <p className="about-description">
              Engineered for Indian kirana shopkeepers. Empowering small store owners to record daily ledger transactions hands-free using natural voice in their native language.
            </p>

            <div className="about-meta-box">
              <div className="meta-line">
                <span className="meta-key">Built by:</span>
                <span className="meta-val font-semibold">Team Lumina</span>
              </div>
              <div className="meta-line">
                <span className="meta-key">Event:</span>
                <span className="meta-val">Build Bangalore Hackathon</span>
              </div>
              <div className="meta-line">
                <span className="meta-key">Theme:</span>
                <span className="meta-val">Dark Obsidian Kirana UI</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
