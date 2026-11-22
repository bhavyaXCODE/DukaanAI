import React from 'react';
import { formatINR } from '../services/api';
import './CustomerCard.css';

export const getAlphabetLetter = (name = '') => {
  if (!name) return '#';
  const clean = name.trim();
  const firstChar = clean.charAt(0);
  const map = {
    'अ': 'A', 'आ': 'A', 'इ': 'I', 'ई': 'I', 'उ': 'U', 'ऊ': 'U',
    'ए': 'E', 'ऐ': 'A', 'ओ': 'O', 'औ': 'A',
    'क': 'K', 'ख': 'K', 'ग': 'G', 'घ': 'G',
    'च': 'C', 'छ': 'C', 'ज': 'J', 'झ': 'J',
    'ट': 'T', 'ठ': 'T', 'ड': 'D', 'ढ': 'D', 'ण': 'N',
    'त': 'T', 'थ': 'T', 'द': 'D', 'ध': 'D', 'न': 'N',
    'प': 'P', 'फ': 'P', 'ब': 'B', 'भ': 'B', 'म': 'M',
    'य': 'Y', 'र': 'R', 'ल': 'L', 'व': 'V', 'श': 'S', 'ष': 'S', 'स': 'S', 'ह': 'H',
    'ಅ': 'A', 'ಆ': 'A', 'ಇ': 'I', 'ಈ': 'I', 'ಉ': 'U', 'ಊ': 'U',
    'ಎ': 'E', 'ಏ': 'E', 'ಐ': 'A', 'ಒ': 'O', 'ಓ': 'O', 'ಔ': 'A',
    'ಕ': 'K', 'ಖ': 'K', 'ಗ': 'G', 'ಘ': 'G',
    'ಚ': 'C', 'ಛ': 'C', 'ಜ': 'J', 'ಝ': 'J',
    'ಟ': 'T', 'ಠ': 'T', 'ಡ': 'D', 'ಢ': 'D', 'ಣ': 'N',
    'ತ': 'T', 'ಥ': 'T', 'ದ': 'D', 'ಧ': 'D', 'ನ': 'N',
    'ಪ': 'P', 'ಫ': 'P', 'ಬ': 'B', 'ಭ': 'B', 'ಮ': 'M',
    'ಯ': 'Y', 'ರ': 'R', 'ಲ': 'L', 'ವ': 'V', 'ಶ': 'S', 'ಷ': 'S', 'ಸ': 'S', 'ಹ': 'H', 'ಳ': 'L',
  };
  if (map[firstChar]) return map[firstChar];
  if (/[a-zA-Z]/.test(firstChar)) return firstChar.toUpperCase();
  return firstChar.toUpperCase();
};

export const toTitleCase = (str = '') => {
  if (!str) return '';
  return str
    .split(' ')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
};

export const isPromiseDueToday = (dateStr) => {
  if (!dateStr) return false;
  const s = String(dateStr).trim().toLowerCase();
  const now = new Date();
  const day = now.getDate();
  const monthShort = now.toLocaleString('en-US', { month: 'short' }).toLowerCase();
  const todayDisp = `${day} ${monthShort}`;
  const todayIso = now.toISOString().slice(0, 10);
  return (
    s.includes(todayDisp) ||
    s.includes(todayIso) ||
    s.includes('today') ||
    s.includes('aaj') ||
    s.includes('आज') ||
    s.includes('ivattu')
  );
};

const CustomerCard = ({ customer, onClick, onSelectForVoice }) => {
  const balance = customer.outstanding_balance !== undefined ? customer.outstanding_balance : (customer.balance || 0);
  const hasOutstanding = balance > 0;
  const alphabetLetter = getAlphabetLetter(customer.name);
  const promisedAmt = Number(customer.promised_amount || 0);
  const hasPromise = promisedAmt > 0;
  const isDueToday = hasPromise && isPromiseDueToday(customer.promised_date);

  return (
    <div
      className={`customer-card ${hasOutstanding ? 'has-balance' : 'settled'} ${isDueToday ? 'promise-due-card' : ''}`}
      onClick={() => onClick && onClick(customer)}
    >
      <div className="customer-card-header">
        <div className="customer-avatar-box">
          <span className="customer-avatar-initial">
            {alphabetLetter}
          </span>
        </div>
        <div className="customer-titles">
          <h4 className="customer-name">{toTitleCase(customer.name)}</h4>
          {customer.alias && (
            <span className="customer-alias">"{customer.alias}"</span>
          )}
        </div>
        <div className="status-badges-group">
          {isDueToday && (
            <span className="due-today-badge animate-pulse" title="Payment promised today!">
              🔔 DUE TODAY
            </span>
          )}
          <span className="letter-badge">{alphabetLetter}</span>
          <div className={`status-pill ${hasOutstanding ? 'due' : 'cleared'}`}>
            {hasOutstanding ? 'DUE' : 'CLEAR'}
          </div>
        </div>
      </div>

      <div className="customer-card-details">
        {customer.landmark && (
          <div className="detail-item">
            <span className="detail-icon">📍</span>
            <span className="detail-text">{customer.landmark}</span>
          </div>
        )}
        {customer.phone && (
          <div className="detail-item">
            <span className="detail-icon">📞</span>
            <span className="detail-text">{customer.phone}</span>
          </div>
        )}
      </div>

      {/* Promised Amount & Date Section */}
      {hasPromise && (
        <div className={`customer-promise-box ${isDueToday ? 'promise-box-today' : ''}`}>
          <div className="promise-box-top">
            <span className="promise-tag">
              {isDueToday ? '🔔 PAYMENT PROMISE (TODAY)' : '🤝 PAYMENT PROMISE'}
            </span>
            <span className="promise-date-pill">{customer.promised_date || 'Scheduled'}</span>
          </div>
          <div className="promise-box-row">
            <span className="promise-lbl">Promised to deposit:</span>
            <span className="promise-val">{formatINR(promisedAmt)}</span>
          </div>
          {isDueToday && (
            <div className="promise-today-notice">
              ⚠️ <strong>Remind today:</strong> {toTitleCase(customer.name)} promised to give {formatINR(promisedAmt)}!
            </div>
          )}
        </div>
      )}

      {/* Ledger Stats: Total Credited & Total Paid */}
      <div className="customer-ledger-stats">
        <div className="ledger-stat-item">
          <span className="ledger-stat-label">Total Credited</span>
          <span className="ledger-stat-value credit-val">{formatINR(customer.total_credit || 0)}</span>
        </div>
        <div className="ledger-stat-divider" />
        <div className="ledger-stat-item">
          <span className="ledger-stat-label">Total Paid</span>
          <span className="ledger-stat-value paid-val">{formatINR(customer.total_payments || 0)}</span>
        </div>
      </div>

      <div className="customer-card-balance-box">
        <div className="balance-info">
          <span className="balance-label">Outstanding Balance:</span>
          <span className={`balance-amount ${hasOutstanding ? 'amount-due' : 'amount-zero'}`}>
            {formatINR(balance)}
          </span>
        </div>
      </div>

      <div className="customer-card-actions" onClick={(e) => e.stopPropagation()}>
        <button
          type="button"
          className="card-quick-action voice-btn"
          onClick={() => onSelectForVoice && onSelectForVoice(customer)}
          title="Voice entry for this customer"
        >
          🎙️ Voice Entry
        </button>
      </div>
    </div>
  );
};

export default CustomerCard;
