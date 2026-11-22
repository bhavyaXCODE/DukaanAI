import React, { useState, useMemo } from 'react';
import { formatINR, formatDateTime } from '../services/api';
import './TransactionTable.css';

const TransactionTable = ({
  transactions = [],
  onConfirm,
  onDelete,
  loading = false,
  itemsPerPage = 8,
}) => {
  const [filterType, setFilterType] = useState('ALL');
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  const filteredTransactions = useMemo(() => {
    return transactions.filter((tx) => {
      // Type filter
      if (filterType !== 'ALL' && tx.type !== filterType) {
        return false;
      }
      // Status filter
      if (filterStatus !== 'ALL' && tx.status !== filterStatus) {
        return false;
      }
      // Search term
      if (searchTerm.trim()) {
        const query = searchTerm.toLowerCase();
        const customerName = (tx.customer_name || tx.customer || '').toLowerCase();
        const alias = (tx.customer_alias || '').toLowerCase();
        const notes = (tx.notes || '').toLowerCase();
        if (
          !customerName.includes(query) &&
          !alias.includes(query) &&
          !notes.includes(query)
        ) {
          return false;
        }
      }
      return true;
    });
  }, [transactions, filterType, filterStatus, searchTerm]);

  // Pagination calculation
  const totalPages = Math.ceil(filteredTransactions.length / itemsPerPage) || 1;
  const paginatedTransactions = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filteredTransactions.slice(start, start + itemsPerPage);
  }, [filteredTransactions, currentPage, itemsPerPage]);

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  };

  return (
    <div className="transaction-table-container">
      {/* Filter and Search Bar */}
      <div className="table-controls-bar">
        <div className="search-box">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            placeholder="Search by customer, alias, or items..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
          />
        </div>

        <div className="filters-group">
          {/* Type filter */}
          <div className="filter-select-wrapper">
            <label>Type:</label>
            <select
              value={filterType}
              onChange={(e) => {
                setFilterType(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="ALL">All Types</option>
              <option value="CREDIT">Credit (ಸಾಲ)</option>
              <option value="PAYMENT">Payment (ಜಮಾ)</option>
            </select>
          </div>

          {/* Status filter */}
          <div className="filter-select-wrapper">
            <label>Status:</label>
            <select
              value={filterStatus}
              onChange={(e) => {
                setFilterStatus(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="ALL">All Status</option>
              <option value="CONFIRMED">Confirmed</option>
              <option value="DRAFT">Draft</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
          </div>
        </div>
      </div>

      {/* Table Element */}
      <div className="table-responsive">
        <table className="transaction-table">
          <thead>
            <tr>
              <th>Date / Time</th>
              <th>Customer</th>
              <th>Type</th>
              <th>Amount</th>
              <th>Status</th>
              <th>Notes</th>
              <th className="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              // Skeleton rows
              Array.from({ length: 5 }).map((_, idx) => (
                <tr key={idx} className="skeleton-row">
                  <td><div className="skeleton skeleton-td" style={{ width: '90px' }} /></td>
                  <td><div className="skeleton skeleton-td" style={{ width: '130px' }} /></td>
                  <td><div className="skeleton skeleton-td" style={{ width: '70px' }} /></td>
                  <td><div className="skeleton skeleton-td" style={{ width: '80px' }} /></td>
                  <td><div className="skeleton skeleton-td" style={{ width: '80px' }} /></td>
                  <td><div className="skeleton skeleton-td" style={{ width: '120px' }} /></td>
                  <td><div className="skeleton skeleton-td" style={{ width: '60px', marginLeft: 'auto' }} /></td>
                </tr>
              ))
            ) : paginatedTransactions.length === 0 ? (
              <tr>
                <td colSpan="7" className="empty-table-cell">
                  <div className="table-empty-box">
                    <span>📋</span>
                    <p>No transactions found matching your criteria</p>
                  </div>
                </td>
              </tr>
            ) : (
              paginatedTransactions.map((tx) => (
                <tr key={tx.id} className="transaction-row">
                  <td className="date-cell">
                    {formatDateTime(tx.created_at || tx.timestamp)}
                  </td>
                  <td className="customer-cell">
                    <div className="customer-primary-name">
                      {tx.customer_name || tx.customer || 'Unknown'}
                    </div>
                    {tx.customer_alias && (
                      <div className="customer-alias-tag">({tx.customer_alias})</div>
                    )}
                  </td>
                  <td>
                    <span className={`badge-type ${tx.type === 'CREDIT' ? 'badge-credit' : 'badge-payment'}`}>
                      {tx.type === 'CREDIT' ? 'CREDIT' : 'PAYMENT'}
                    </span>
                  </td>
                  <td className="amount-cell">
                    <span className={`amount-value ${tx.type === 'CREDIT' ? 'amount-credit' : 'amount-payment'}`}>
                      {tx.type === 'CREDIT' ? '+' : '-'} {formatINR(tx.amount)}
                    </span>
                  </td>
                  <td>
                    <span className={`badge-status status-${(tx.status || 'CONFIRMED').toLowerCase()}`}>
                      {tx.status || 'CONFIRMED'}
                    </span>
                  </td>
                  <td className="notes-cell" title={tx.notes || ''}>
                    {tx.notes || '-'}
                  </td>
                  <td className="actions-cell text-right">
                    <div className="action-buttons-group">
                      {tx.status === 'DRAFT' && onConfirm && (
                        <button
                          type="button"
                          className="table-action-btn confirm"
                          onClick={() => onConfirm(tx.id)}
                          title="Confirm draft transaction"
                        >
                          ✓ Confirm
                        </button>
                      )}
                      {onDelete && tx.status !== 'CANCELLED' && (
                        <button
                          type="button"
                          className="table-action-btn delete"
                          onClick={() => onDelete(tx.id)}
                          title="Delete or cancel transaction"
                        >
                          ✕
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      {!loading && filteredTransactions.length > 0 && (
        <div className="table-pagination">
          <div className="pagination-info">
            Showing{' '}
            <span className="font-semibold">
              {(currentPage - 1) * itemsPerPage + 1}
            </span>{' '}
            to{' '}
            <span className="font-semibold">
              {Math.min(currentPage * itemsPerPage, filteredTransactions.length)}
            </span>{' '}
            of <span className="font-semibold">{filteredTransactions.length}</span> entries
          </div>

          <div className="pagination-buttons">
            <button
              type="button"
              className="page-btn"
              disabled={currentPage === 1}
              onClick={() => handlePageChange(currentPage - 1)}
            >
              Previous
            </button>
            {Array.from({ length: totalPages }).map((_, i) => {
              const p = i + 1;
              if (
                p === 1 ||
                p === totalPages ||
                (p >= currentPage - 1 && p <= currentPage + 1)
              ) {
                return (
                  <button
                    key={p}
                    type="button"
                    className={`page-num ${currentPage === p ? 'active' : ''}`}
                    onClick={() => handlePageChange(p)}
                  >
                    {p}
                  </button>
                );
              }
              if (p === currentPage - 2 || p === currentPage + 2) {
                return (
                  <span key={p} className="page-ellipsis">
                    ...
                  </span>
                );
              }
              return null;
            })}
            <button
              type="button"
              className="page-btn"
              disabled={currentPage === totalPages}
              onClick={() => handlePageChange(currentPage + 1)}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default TransactionTable;
