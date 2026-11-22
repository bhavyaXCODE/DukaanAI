import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import TransactionTable from '../components/TransactionTable';
import {
  getTransactions,
  confirmTransaction,
  deleteTransaction,
} from '../services/api';
import './Transactions.css';
import { useApp } from '../context/AppContext';

const Transactions = () => {
  const navigate = useNavigate();
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [notification, setNotification] = useState(null);

  const fetchTransactionList = async () => {
    try {
      setLoading(true);
      const res = await getTransactions();
      if (res && res.items) {
        setTransactions(res.items);
      } else if (Array.isArray(res)) {
        setTransactions(res);
      }
    } catch (err) {
      console.error('Failed to load transactions:', err);
    } finally {
      setLoading(false);
    }
  };

  const { refreshTrigger } = useApp();

  useEffect(() => {
    fetchTransactionList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshTrigger]);

  const handleConfirm = async (id) => {
    try {
      await confirmTransaction(id);
      setTransactions((prev) =>
        prev.map((tx) => (tx.id === id ? { ...tx, status: 'CONFIRMED' } : tx))
      );
      setNotification('Transaction confirmed successfully!');
      setTimeout(() => setNotification(null), 3000);
    } catch (err) {
      console.error('Error confirming transaction:', err);
    }
  };

  const handleDelete = async (id) => {
    try {
      await deleteTransaction(id);
      setTransactions((prev) =>
        prev.map((tx) => (tx.id === id ? { ...tx, status: 'CANCELLED' } : tx))
      );
      setNotification('Transaction cancelled/deleted.');
      setTimeout(() => setNotification(null), 3000);
    } catch (err) {
      console.error('Error cancelling transaction:', err);
    }
  };

  return (
    <div className="transactions-page animate-fadeIn">
      {/* Toast Notification */}
      {notification && (
        <div className="toast-success animate-slideUp">
          <span className="toast-icon">✓</span>
          <span>{notification}</span>
        </div>
      )}

      {/* Page Header */}
      <div className="transactions-header">
        <div>
          <div className="flex items-center gap-2">
            <span className="page-icon">📋</span>
            <h1 className="page-title">Ledger Transactions</h1>
            <span className="count-badge">{transactions.length} Records</span>
          </div>
          <p className="page-subtitle">
            All credit and payment entries made via voice khata and manual entries
          </p>
        </div>

        <div className="header-actions">
          <button
            type="button"
            className="btn-refresh"
            onClick={fetchTransactionList}
            title="Refresh transaction ledger"
          >
            🔄 Refresh
          </button>
          <button
            type="button"
            className="btn-voice-quick"
            onClick={() => navigate('/voice')}
          >
            🎙️ Add by Voice
          </button>
        </div>
      </div>

      {/* Transaction Table */}
      <TransactionTable
        transactions={transactions}
        loading={loading}
        onConfirm={handleConfirm}
        onDelete={handleDelete}
        itemsPerPage={10}
      />
    </div>
  );
};

export default Transactions;
