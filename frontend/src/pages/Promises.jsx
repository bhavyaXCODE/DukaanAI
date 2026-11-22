import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getAllPromises,
  fulfillPromise,
  dismissPromise,
  formatINR,
  formatDateTime,
} from '../services/api';
import { isPromiseDueToday } from '../components/CustomerCard';
import { useApp } from '../context/AppContext';
import './Promises.css';

const Promises = () => {
  const navigate = useNavigate();
  const { shopInfo, refreshTrigger, incrementRefresh } = useApp();

  const [promises, setPromises] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('ALL'); // ALL | DUE_TODAY | PENDING | FULFILLED
  const [searchTerm, setSearchTerm] = useState('');
  const [notification, setNotification] = useState(null);

  const fetchPromisesList = async () => {
    try {
      setLoading(true);
      const res = await getAllPromises(shopInfo?.id || 1);
      if (Array.isArray(res)) {
        setPromises(res);
      } else {
        setPromises([]);
      }
    } catch (err) {
      console.error('Failed to load payment promises:', err);
      setPromises([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPromisesList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshTrigger, shopInfo?.id]);

  const handleFulfill = async (promiseId, customerName, amount) => {
    try {
      await fulfillPromise(promiseId);
      setPromises((prev) =>
        prev.map((p) => (p.id === promiseId ? { ...p, status: 'FULFILLED' } : p))
      );
      setNotification(`Payment of ${formatINR(amount)} from ${customerName} marked as received/fulfilled!`);
      setTimeout(() => setNotification(null), 3500);
      incrementRefresh();
    } catch (err) {
      console.error('Failed to fulfill promise:', err);
    }
  };

  const handleDismiss = async (promiseId) => {
    try {
      await dismissPromise(promiseId);
      setPromises((prev) =>
        prev.map((p) => (p.id === promiseId ? { ...p, status: 'DISMISSED' } : p))
      );
      setNotification('Promise dismissed.');
      setTimeout(() => setNotification(null), 3000);
      incrementRefresh();
    } catch (err) {
      console.error('Failed to dismiss promise:', err);
    }
  };

  // Stat calculations
  const totalPromises = promises.length;
  const dueTodayCount = useMemo(() => {
    return promises.filter((p) => p.status === 'PENDING' && (p.is_due_today || isPromiseDueToday(p.promise_date))).length;
  }, [promises]);
  const pendingTotalAmount = useMemo(() => {
    return promises
      .filter((p) => p.status === 'PENDING')
      .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);
  }, [promises]);
  const fulfilledCount = useMemo(() => {
    return promises.filter((p) => p.status === 'FULFILLED').length;
  }, [promises]);

  // Filtered list
  const filteredPromises = useMemo(() => {
    return promises.filter((p) => {
      const isDue = p.status === 'PENDING' && (p.is_due_today || isPromiseDueToday(p.promise_date));

      // Status filter
      if (statusFilter === 'DUE_TODAY' && !isDue) return false;
      if (statusFilter === 'PENDING' && p.status !== 'PENDING') return false;
      if (statusFilter === 'FULFILLED' && p.status !== 'FULFILLED') return false;
      if (statusFilter === 'DISMISSED' && p.status !== 'DISMISSED') return false;

      // Search term filter
      if (searchTerm.trim()) {
        const q = searchTerm.toLowerCase();
        const name = (p.customer_name || '').toLowerCase();
        const phone = (p.customer_phone || '').toLowerCase();
        const transcript = (p.voice_transcript || '').toLowerCase();
        const pDate = (p.promise_date || '').toLowerCase();
        if (
          !name.includes(q) &&
          !phone.includes(q) &&
          !transcript.includes(q) &&
          !pDate.includes(q)
        ) {
          return false;
        }
      }

      return true;
    });
  }, [promises, statusFilter, searchTerm]);

  return (
    <div className="promises-page animate-fadeIn">
      {/* Toast Notification */}
      {notification && (
        <div className="toast-success animate-slideUp">
          <span className="toast-icon">✓</span>
          <span>{notification}</span>
        </div>
      )}

      {/* Page Header */}
      <div className="promises-header">
        <div>
          <div className="flex items-center gap-2">
            <span className="page-icon">🤝</span>
            <h1 className="page-title">Payment Promises</h1>
            <span className="count-badge">{totalPromises} Records</span>
            {dueTodayCount > 0 && (
              <span className="due-alert-pill animate-pulse">
                🔔 {dueTodayCount} Due Today
              </span>
            )}
          </div>
          <p className="page-subtitle">
            All customer payment promises and deposit commitments recorded via voice khata
          </p>
        </div>

        <div className="header-actions">
          <button
            type="button"
            className="btn-refresh"
            onClick={fetchPromisesList}
            title="Refresh payment promises"
          >
            🔄 Refresh
          </button>
          <button
            type="button"
            className="btn-voice-quick"
            onClick={() => navigate('/voice')}
            title="Record new promise with voice"
          >
            🎙️ Record by Voice
          </button>
        </div>
      </div>

      {/* Summary Stat Cards */}
      <div className="promises-stat-row">
        <div className="promise-stat-card card-blue">
          <div className="stat-card-icon">💰</div>
          <div className="stat-card-info">
            <span className="stat-card-label">Total Promised Pending</span>
            <span className="stat-card-value">{formatINR(pendingTotalAmount)}</span>
          </div>
        </div>

        <div className={`promise-stat-card ${dueTodayCount > 0 ? 'card-amber due-pulse' : 'card-dark'}`}>
          <div className="stat-card-icon">🔔</div>
          <div className="stat-card-info">
            <span className="stat-card-label">Due Today</span>
            <span className="stat-card-value">{dueTodayCount} Customers</span>
          </div>
        </div>

        <div className="promise-stat-card card-green">
          <div className="stat-card-icon">✓</div>
          <div className="stat-card-info">
            <span className="stat-card-label">Fulfilled Promises</span>
            <span className="stat-card-value">{fulfilledCount} Received</span>
          </div>
        </div>

        <div className="promise-stat-card card-purple">
          <div className="stat-card-icon">📋</div>
          <div className="stat-card-info">
            <span className="stat-card-label">Total Promises Recorded</span>
            <span className="stat-card-value">{totalPromises} Records</span>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="promises-controls-bar">
        <div className="search-box">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            placeholder="Search by customer name, phone, or voice transcript..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          {searchTerm && (
            <button
              type="button"
              className="clear-search-btn"
              onClick={() => setSearchTerm('')}
            >
              ✕
            </button>
          )}
        </div>

        <div className="status-filter-tabs">
          <button
            type="button"
            className={`filter-tab ${statusFilter === 'ALL' ? 'active' : ''}`}
            onClick={() => setStatusFilter('ALL')}
          >
            All ({promises.length})
          </button>
          <button
            type="button"
            className={`filter-tab ${statusFilter === 'DUE_TODAY' ? 'active' : ''} ${dueTodayCount > 0 ? 'has-due' : ''}`}
            onClick={() => setStatusFilter('DUE_TODAY')}
          >
            🔔 Due Today ({dueTodayCount})
          </button>
          <button
            type="button"
            className={`filter-tab ${statusFilter === 'PENDING' ? 'active' : ''}`}
            onClick={() => setStatusFilter('PENDING')}
          >
            ⏳ Pending ({promises.filter((p) => p.status === 'PENDING').length})
          </button>
          <button
            type="button"
            className={`filter-tab ${statusFilter === 'FULFILLED' ? 'active' : ''}`}
            onClick={() => setStatusFilter('FULFILLED')}
          >
            ✓ Fulfilled ({fulfilledCount})
          </button>
        </div>
      </div>

      {/* Promises Content Area */}
      {loading ? (
        <div className="promises-loading-skeleton">
          <div className="skeleton-row" />
          <div className="skeleton-row" />
          <div className="skeleton-row" />
        </div>
      ) : filteredPromises.length === 0 ? (
        <div className="empty-promises-container">
          <span className="empty-icon">🤝</span>
          <h3>No payment promises found</h3>
          <p>
            {searchTerm || statusFilter !== 'ALL'
              ? 'No promises match your selected filters. Try clearing filters.'
              : 'Record customer payment commitments naturally using Voice Khata.'}
          </p>
          <div className="voice-tip-box">
            <span>💡 Try saying:</span>
            <code>"Ramesh promised to deposit 500 on 25 Nov"</code>
            <span>or</span>
            <code>"Govind kal 400 dega"</code>
          </div>
          <button
            type="button"
            className="btn-voice-quick mt-4"
            onClick={() => navigate('/voice')}
          >
            🎙️ Go to Voice Khata
          </button>
        </div>
      ) : (
        <div className="promises-table-card">
          <div className="table-responsive">
            <table className="promises-table">
              <thead>
                <tr>
                  <th>CUSTOMER</th>
                  <th>PROMISED AMOUNT</th>
                  <th>PROMISED DATE</th>
                  <th>STATUS</th>
                  <th>VOICE TRANSCRIPT / NOTES</th>
                  <th>RECORDED AT</th>
                  <th className="text-right">ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {filteredPromises.map((promise) => {
                  const isDue =
                    promise.status === 'PENDING' &&
                    (promise.is_due_today || isPromiseDueToday(promise.promise_date));

                  return (
                    <tr
                      key={promise.id}
                      className={`promise-row ${isDue ? 'row-due-today' : ''} ${promise.status.toLowerCase()}`}
                    >
                      {/* Customer Info */}
                      <td>
                        <div className="customer-cell">
                          <div className="customer-avatar-mini">
                            {(promise.customer_name || 'C').charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <span className="customer-name-text">
                              {promise.customer_name}
                            </span>
                            {promise.customer_phone && (
                              <span className="customer-phone-sub">
                                📞 {promise.customer_phone}
                              </span>
                            )}
                          </div>
                        </div>
                      </td>

                      {/* Promised Amount */}
                      <td>
                        <span className="promise-amount-tag">
                          {formatINR(promise.amount)}
                        </span>
                      </td>

                      {/* Promised Date */}
                      <td>
                        <div className="date-cell">
                          <span className="promise-date-main">
                            📅 {promise.promise_date}
                          </span>
                          {isDue && (
                            <span className="due-warning-tag">
                              Due Today!
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Status */}
                      <td>
                        {promise.status === 'FULFILLED' ? (
                          <span className="status-badge fulfilled">
                            ✓ FULFILLED
                          </span>
                        ) : promise.status === 'DISMISSED' ? (
                          <span className="status-badge dismissed">
                            ✕ DISMISSED
                          </span>
                        ) : isDue ? (
                          <span className="status-badge due-today animate-pulse">
                            🔔 DUE TODAY
                          </span>
                        ) : (
                          <span className="status-badge pending">
                            ⏳ PENDING
                          </span>
                        )}
                      </td>

                      {/* Voice Transcript / Notes */}
                      <td>
                        <div className="transcript-cell">
                          <span className="transcript-text" title={promise.voice_transcript || '-'}>
                            {promise.voice_transcript || '-'}
                          </span>
                        </div>
                      </td>

                      {/* Created At */}
                      <td>
                        <span className="created-at-text">
                          {formatDateTime(promise.created_at)}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="text-right">
                        <div className="action-buttons-cell">
                          {promise.status === 'PENDING' ? (
                            <>
                              <button
                                type="button"
                                className="action-btn-fulfill"
                                onClick={() => handleFulfill(promise.id, promise.customer_name, promise.amount)}
                                title="Mark as received and update customer account"
                              >
                                ✓ Received
                              </button>
                              <button
                                type="button"
                                className="action-btn-voice"
                                onClick={() => navigate('/voice')}
                                title="Collect via Voice"
                              >
                                🎙️ Collect
                              </button>
                              <button
                                type="button"
                                className="action-btn-dismiss"
                                onClick={() => handleDismiss(promise.id)}
                                title="Dismiss promise"
                              >
                                ✕
                              </button>
                            </>
                          ) : (
                            <span className="settled-cell-tag">
                              {promise.status === 'FULFILLED' ? '✓ Received' : '✕ Dismissed'}
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default Promises;
