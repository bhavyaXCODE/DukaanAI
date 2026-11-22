import React, { useState, useEffect } from 'react';
import StatCard from '../components/StatCard';
import CreditPaymentChart from '../components/CreditPaymentChart';
import {
  getReportSummary,
  getReportCustomers,
  getReportDaily,
  formatINR,
} from '../services/api';
import { useApp } from '../context/AppContext';
import './Reports.css';

const Reports = () => {
  const { refreshTrigger } = useApp();
  // 7-day default range
  const todayStr = new Date().toISOString().split('T')[0];
  const lastWeekStr = new Date(Date.now() - 7 * 86400000)
    .toISOString()
    .split('T')[0];

  const [dateFrom, setDateFrom] = useState(lastWeekStr);
  const [dateTo, setDateTo] = useState(todayStr);

  const [summary, setSummary] = useState(null);
  const [customerReports, setCustomerReports] = useState([]);
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchReports = async () => {
    try {
      setLoading(true);
      const [sumRes, custRes, dailyRes] = await Promise.all([
        getReportSummary(dateFrom, dateTo),
        getReportCustomers(),
        getReportDaily(7),
      ]);
      setSummary(sumRes);
      setCustomerReports(custRes || []);
      setChartData(dailyRes || []);
    } catch (err) {
      console.error('Failed to load reports:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateFrom, dateTo, refreshTrigger]);

  return (
    <div className="reports-page animate-fadeIn">
      {/* Header & Date Picker */}
      <div className="reports-header">
        <div>
          <div className="flex items-center gap-2">
            <span className="page-icon">📊</span>
            <h1 className="page-title">Reports & Analytics</h1>
          </div>
          <p className="page-subtitle">
            Financial ledger insights, cashflow trends, and customer credit analysis
          </p>
        </div>

        {/* Date Range Picker */}
        <div className="date-filter-box">
          <div className="date-input-wrapper">
            <label>From:</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
          </div>
          <div className="date-input-wrapper">
            <label>To:</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
            />
          </div>
          <button
            type="button"
            className="btn-apply-date"
            onClick={fetchReports}
          >
            Apply
          </button>
        </div>
      </div>

      {/* 4 Summary Cards */}
      <div className="reports-stat-grid">
        <StatCard
          title="Total Credit Extended"
          value={summary?.total_credit || 0}
          description="Total goods given on credit"
          gradient="blue"
          icon="📤"
          isCurrency={true}
          loading={loading}
        />
        <StatCard
          title="Total Payments Collected"
          value={summary?.total_payments || 0}
          description="Total cash & UPI collections"
          gradient="green"
          icon="📥"
          isCurrency={true}
          loading={loading}
        />
        <StatCard
          title="Net Outstanding Balance"
          value={summary?.net_balance || 0}
          description="Current net receivables due"
          gradient="amber"
          icon="⚖️"
          isCurrency={true}
          loading={loading}
        />
        <StatCard
          title="Total Transactions"
          value={summary?.total_transactions || 0}
          description="Ledger entries in period"
          gradient="purple"
          icon="📈"
          isCurrency={false}
          loading={loading}
        />
      </div>

      {/* Chart Card */}
      <div className="report-chart-card">
        <div className="chart-header">
          <div>
            <h3 className="section-title">Credit vs Payment Flow</h3>
            <p className="section-subtitle">Comparative daily trends for the selected timeline</p>
          </div>
        </div>
        <div className="chart-body">
          {loading ? (
            <div className="skeleton" style={{ height: '320px', width: '100%' }} />
          ) : (
            <CreditPaymentChart data={chartData} height={340} />
          )}
        </div>
      </div>

      {/* Customer-wise Outstanding Table */}
      <div className="customer-breakdown-card">
        <div className="breakdown-header">
          <h3 className="section-title">Customer-Wise Ledger Breakdown</h3>
          <p className="section-subtitle">Cumulative credits, payments, and outstanding balances</p>
        </div>

        <div className="table-responsive">
          <table className="breakdown-table">
            <thead>
              <tr>
                <th>Customer</th>
                <th>Total Credit (ಸಾಲ)</th>
                <th>Total Paid (ಜಮಾ)</th>
                <th>Current Outstanding</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <tr key={i}>
                    <td colSpan="5">
                      <div className="skeleton" style={{ height: '24px', width: '100%' }} />
                    </td>
                  </tr>
                ))
              ) : customerReports.length === 0 ? (
                <tr>
                  <td colSpan="5" className="empty-cell">
                    No customer records available.
                  </td>
                </tr>
              ) : (
                customerReports.map((c) => {
                  const isSettled = (c.outstanding || 0) <= 0;
                  return (
                    <tr key={c.id}>
                      <td className="cust-name-cell">
                        <span className="font-semibold text-primary">{c.name}</span>
                        {c.alias && (
                          <span className="cust-alias-text">"{c.alias}"</span>
                        )}
                      </td>
                      <td className="text-red font-medium">{formatINR(c.total_credit)}</td>
                      <td className="text-green font-medium">{formatINR(c.total_payment)}</td>
                      <td className="cust-balance-cell">
                        <span className={`balance-tag ${isSettled ? 'settled' : 'due'}`}>
                          {formatINR(c.outstanding)}
                        </span>
                      </td>
                      <td>
                        <span className={`status-badge-mini ${isSettled ? 'clear' : 'due'}`}>
                          {isSettled ? 'Settled' : 'Pending'}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Reports;
