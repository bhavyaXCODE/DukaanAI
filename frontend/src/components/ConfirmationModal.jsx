import React, { useState, useEffect } from 'react';
import { formatINR } from '../services/api';
import './ConfirmationModal.css';

const ConfirmationModal = ({
  isOpen,
  transaction,
  onConfirm,
  onCancel,
  onCorrect,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editAmount, setEditAmount] = useState('');
  const [editCustomer, setEditCustomer] = useState('');
  const [editType, setEditType] = useState('CREDIT');

  useEffect(() => {
    if (transaction) {
      setEditAmount(transaction.amount || '');
      setEditCustomer(transaction.customer_name || transaction.customer || '');
      setEditType(transaction.type || 'CREDIT');
      setIsEditing(false);
    }
  }, [transaction]);

  if (!isOpen || !transaction) return null;

  const handleSaveCorrection = () => {
    if (onCorrect) {
      onCorrect({
        ...transaction,
        amount: parseFloat(editAmount) || transaction.amount,
        customer_name: editCustomer || transaction.customer_name,
        type: editType,
      });
    }
    setIsEditing(false);
  };

  const isCredit = (isEditing ? editType : transaction.type) === 'CREDIT';

  return (
    <div className="modal-backdrop">
      <div className="modal-card animate-slideUp">
        {/* Modal Header */}
        <div className="modal-header">
          <div className="modal-icon-badge">
            <span>{isCredit ? '📤' : '📥'}</span>
          </div>
          <div>
            <h3 className="modal-title">Confirm Voice Transaction</h3>
            <p className="modal-subtitle">DukaanAI parsed your speech. Please verify:</p>
          </div>
        </div>

        {/* Modal Content */}
        <div className="modal-content">
          {!isEditing ? (
            <div className="summary-card">
              <div className="summary-type-row">
                <span className={`transaction-badge ${isCredit ? 'credit' : 'payment'}`}>
                  {isCredit ? 'CREDIT (ಸಾಲ / उधार)' : 'PAYMENT (ಸ್ವೀಕೃತಿ / जमा)'}
                </span>
                <span className="summary-date">Just now</span>
              </div>

              <div className="summary-amount-row">
                <span className="summary-amount-label">Amount:</span>
                <span className="summary-amount-value">{formatINR(transaction.amount)}</span>
              </div>

              <div className="summary-customer-box">
                <div className="summary-row">
                  <span className="label">Customer:</span>
                  <span className="value bold">{transaction.customer_name || transaction.customer}</span>
                </div>
                {transaction.customer_alias && (
                  <div className="summary-row">
                    <span className="label">Alias / Shop:</span>
                    <span className="value text-muted">"{transaction.customer_alias}"</span>
                  </div>
                )}
                {transaction.notes && (
                  <div className="summary-row">
                    <span className="label">Items / Notes:</span>
                    <span className="value text-secondary">{transaction.notes}</span>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="edit-form-box">
              <div className="form-group">
                <label>Type:</label>
                <div className="type-toggle-group">
                  <button
                    type="button"
                    className={`type-btn ${editType === 'CREDIT' ? 'active-credit' : ''}`}
                    onClick={() => setEditType('CREDIT')}
                  >
                    Credit (ಸಾಲ)
                  </button>
                  <button
                    type="button"
                    className={`type-btn ${editType === 'PAYMENT' ? 'active-payment' : ''}`}
                    onClick={() => setEditType('PAYMENT')}
                  >
                    Payment (ಜಮಾ)
                  </button>
                </div>
              </div>

              <div className="form-group">
                <label>Customer Name:</label>
                <input
                  type="text"
                  value={editCustomer}
                  onChange={(e) => setEditCustomer(e.target.value)}
                  placeholder="Customer name"
                />
              </div>

              <div className="form-group">
                <label>Amount (₹):</label>
                <input
                  type="number"
                  value={editAmount}
                  onChange={(e) => setEditAmount(e.target.value)}
                  placeholder="Amount"
                />
              </div>

              <div className="flex gap-2 justify-end" style={{ marginTop: '8px' }}>
                <button
                  type="button"
                  className="btn btn-secondary text-sm"
                  onClick={() => setIsEditing(false)}
                >
                  Cancel Edit
                </button>
                <button
                  type="button"
                  className="btn btn-blue text-sm"
                  onClick={handleSaveCorrection}
                >
                  Apply Changes
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Modal Actions */}
        <div className="modal-actions">
          <button
            type="button"
            className="btn btn-confirm"
            onClick={() => onConfirm(transaction)}
          >
            <span className="btn-icon">✓</span>
            <span>Confirm & Save</span>
          </button>

          {!isEditing && (
            <button
              type="button"
              className="btn btn-change"
              onClick={() => setIsEditing(true)}
            >
              <span className="btn-icon">✏️</span>
              <span>Change / Correct</span>
            </button>
          )}

          <button
            type="button"
            className="btn btn-cancel"
            onClick={onCancel}
          >
            <span className="btn-icon">✕</span>
            <span>Discard</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmationModal;
