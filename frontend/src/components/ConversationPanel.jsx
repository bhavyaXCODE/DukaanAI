import React, { useEffect, useRef } from 'react';
import { formatINR } from '../services/api';
import './ConversationPanel.css';

const ConversationPanel = ({
  messages = [],
  onClear,
  title = 'Voice Conversation',
}) => {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <div className="conversation-panel">
      {/* Panel Header */}
      <div className="conversation-header">
        <div className="flex items-center gap-2">
          <span className="convo-icon">💬</span>
          <h3 className="convo-title">{title}</h3>
          <span className="convo-count">{messages.length}</span>
        </div>
        {messages.length > 0 && onClear && (
          <button
            type="button"
            className="convo-clear-btn"
            onClick={onClear}
            title="Clear conversation history"
          >
            Clear History
          </button>
        )}
      </div>

      {/* Messages Container */}
      <div className="conversation-body">
        {messages.length === 0 ? (
          <div className="convo-empty-state">
            <div className="empty-icon-circle">🎙️</div>
            <p className="empty-primary-text">Start speaking to begin your voice khata session</p>
            <p className="empty-sub-text">
              Try saying: "ಸುರೇಶ್ ಅವರಿಗೆ 250 ರೂಪಾಯಿ ಸಾಲ" or "Suresh paid 500"
            </p>
          </div>
        ) : (
          <div className="messages-stream">
            {messages.map((msg) => {
              const isUser = msg.sender === 'user';
              return (
                <div
                  key={msg.id}
                  className={`message-row ${isUser ? 'user-row' : 'ai-row'} animate-fadeIn`}
                >
                  {!isUser && (
                    <div className="avatar-ai">
                      <span>🤖</span>
                    </div>
                  )}

                  <div className={`message-bubble ${isUser ? 'user-bubble' : 'ai-bubble'}`}>
                    <div className="message-text">{msg.text}</div>

                    {/* Draft snippet if attached */}
                    {msg.draft && (
                      <div className="inline-draft-badge">
                        <span className={`type-tag ${msg.draft.type?.toLowerCase()}`}>
                          {msg.draft.type}
                        </span>
                        <span className="customer-name">{msg.draft.customer_name}</span>
                        <span className="amount">{formatINR(msg.draft.amount)}</span>
                      </div>
                    )}

                    <div className="message-meta">
                      <span className="message-time">{msg.timestamp}</span>
                    </div>
                  </div>

                  {isUser && (
                    <div className="avatar-user">
                      <span>👤</span>
                    </div>
                  )}
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>
    </div>
  );
};

export default ConversationPanel;
