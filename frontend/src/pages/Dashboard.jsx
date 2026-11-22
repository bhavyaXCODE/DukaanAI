import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import StatCard from '../components/StatCard';
import CreditPaymentChart from '../components/CreditPaymentChart';
import {
  getDashboardStats,
  getDashboardChart,
  getTodayPromises,
  fulfillPromise,
  dismissPromise,
  formatINR,
} from '../services/api';
import { useApp } from '../context/AppContext';
import './Dashboard.css';

const Dashboard = () => {
  const navigate = useNavigate();
  const { shopInfo, refreshTrigger, incrementRefresh } = useApp();

  const [stats, setStats] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [todayPromises, setTodayPromises] = useState([]);
  const [loading, setLoading] = useState(true);
  const [reminderToast, setReminderToast] = useState(null);

  // Dynamic greeting based on time of day
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Shubhodaya (ಶುಭೋದಯ)';
    if (hour < 17) return 'Namaskara (ನಮಸ್ಕಾರ)';
    return 'Shubhasanje (ಶುಭಸಂಜೆ)';
  };

  // Real formatted date: e.g., "Monday, 17 November 2026"
  const formattedToday = new Date().toLocaleDateString('en-IN', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

  useEffect(() => {
    let isMounted = true;

    const fetchData = async () => {
      try {
        setLoading(true);
        const [statsRes, chartRes, promisesRes] = await Promise.all([
          getDashboardStats(),
          getDashboardChart(),
          getTodayPromises(shopInfo?.id || 1),
        ]);
        if (isMounted) {
          setStats(statsRes);
          setChartData(chartRes || []);
          setTodayPromises(promisesRes || []);
          setLoading(false);
        }
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      isMounted = false;
    };
  }, [refreshTrigger, shopInfo?.id]);

  const handleFulfillPromise = async (promiseId, customerName, amount) => {
    try {
      await fulfillPromise(promiseId);
      setTodayPromises((prev) => prev.filter((p) => p.id !== promiseId));
      setReminderToast(`Marked payment of ${formatINR(amount)} from ${customerName} as fulfilled!`);
      setTimeout(() => setReminderToast(null), 3500);
      incrementRefresh();
    } catch (err) {
      console.error('Failed to fulfill promise:', err);
    }
  };

  const handleDismissPromise = async (promiseId) => {
    try {
      await dismissPromise(promiseId);
      setTodayPromises((prev) => prev.filter((p) => p.id !== promiseId));
    } catch (err) {
      console.error('Failed to dismiss promise:', err);
    }
  };

  return (
    <div className="dashboard-page animate-fadeIn">
      {/* Header section */}
      <div className="dashboard-header">
        <div className="header-left">
          <div className="header-date">
            <span className="calendar-icon">📅</span>
            <span>{formattedToday}</span>
          </div>
          <h1 className="header-greeting">
            {getGreeting()}, <span className="greeting-name">{shopInfo.ownerName || 'Shopkeeper'}</span>
          </h1>
          <p className="header-tagline">
            Your shop. Your language. Your voice. Speak a credit or a payment – DukaanAI writes the khata for you.
          </p>
        </div>

        <div className="header-right">
          <div className="live-status-pill">
            <span className="live-dot" />
            <span>Live khata data</span>
          </div>
          <button
            type="button"
            className="btn-start-voice"
            onClick={() => navigate('/voice')}
          >
            <span className="btn-voice-icon">🎙️</span>
            <span>Start Voice Khata</span>
          </button>
        </div>
      </div>

      {/* Reminder Action Toast */}
      {reminderToast && (
        <div className="dashboard-reminder-toast animate-slideDown">
          <span>✓ {reminderToast}</span>
        </div>
      )}

      {/* Today's Payment Reminders Section */}
      {todayPromises.length > 0 && (
        <div className="payment-reminders-banner animate-slideDown">
          <div className="reminders-banner-header">
            <div className="reminders-title-group">
              <span className="reminders-icon">🔔</span>
              <div>
                <h3 className="reminders-title">
                  Today's Payment Reminders <span className="reminders-count-badge">{todayPromises.length} Due</span>
                </h3>
                <p className="reminders-subtitle">
                  Customers who promised to deposit money today ({formattedToday})
                </p>
              </div>
            </div>
            <button
              type="button"
              className="btn-quick-voice-collect"
              onClick={() => navigate('/voice')}
              title="Collect payments using voice"
            >
              🎙️ Voice Khata
            </button>
          </div>

          <div className="reminders-cards-list">
            {todayPromises.map((p) => (
              <div key={p.id} className="reminder-item-card">
                <div className="reminder-card-left">
                  <div className="reminder-avatar">
                    {(p.customer_name || 'C').charAt(0).toUpperCase()}
                  </div>
                  <div className="reminder-customer-info">
                    <h4 className="reminder-name">{p.customer_name}</h4>
                    <span className="reminder-note">
                      Promised: {p.promise_date} {p.customer_phone ? `• 📞 ${p.customer_phone}` : ''}
                    </span>
                  </div>
                </div>

                <div className="reminder-card-right">
                  <div className="reminder-amount-block">
                    <span className="reminder-amount-label">Promised:</span>
                    <span className="reminder-amount-val">{formatINR(p.amount)}</span>
                  </div>

                  <div className="reminder-actions-btns">
                    <button
                      type="button"
                      className="btn-reminder-action fulfill-btn"
                      onClick={() => handleFulfillPromise(p.id, p.customer_name, p.amount)}
                      title="Mark as paid / received"
                    >
                      ✓ Received
                    </button>
                    <button
                      type="button"
                      className="btn-reminder-action voice-collect-btn"
                      onClick={() => navigate('/voice')}
                      title="Record payment via voice"
                    >
                      🎙️ Collect
                    </button>
                    <button
                      type="button"
                      className="btn-reminder-action dismiss-btn"
                      onClick={() => handleDismissPromise(p.id)}
                      title="Dismiss reminder"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 5 Stat cards row */}
      <div className="stat-cards-grid">
        <StatCard
          title="Total Outstanding Credit"
          value={stats?.total_outstanding || 0}
          description="Pending collection from all customers"
          gradient="blue"
          icon="💰"
          isCurrency={true}
          loading={loading}
        />
        <StatCard
          title="Credit Given Today"
          value={stats?.credit_today || 0}
          change={stats?.credit_change_pct || 12.5}
          changeLabel="vs yesterday"
          description="Total credit extended today"
          gradient="purple"
          icon="📤"
          isCurrency={true}
          loading={loading}
        />
        <StatCard
          title="Payments Received Today"
          value={stats?.payments_today || 0}
          change={stats?.payments_change_pct || 8.2}
          changeLabel="vs yesterday"
          description="Cash & UPI collected today"
          gradient="green"
          icon="📥"
          isCurrency={true}
          loading={loading}
        />
        <StatCard
          title="Active Customers"
          value={stats?.active_customers || 0}
          description="Customers with ledger activity"
          gradient="amber"
          icon="👥"
          isCurrency={false}
          loading={loading}
        />
        <StatCard
          title="Transactions Today"
          value={stats?.transactions_today || 0}
          description="Entries processed via voice & manual"
          gradient="dark"
          icon="📋"
          isCurrency={false}
          loading={loading}
        />
      </div>

      {/* Main Grid: Chart + Quick Actions */}
      <div className="dashboard-main-grid">
        {/* Chart Section */}
        <div className="dashboard-chart-card">
          <div className="chart-header">
            <div>
              <h3 className="section-title">Daily Credit vs Payments</h3>
              <p className="section-subtitle">Last 7 days of ledger movement</p>
            </div>
            <div className="chart-legend-badge">
              <span>₹ Ledger In/Out</span>
            </div>
          </div>

          <div className="chart-body">
            {loading ? (
              <div className="skeleton chart-skeleton" />
            ) : (
              <CreditPaymentChart data={chartData} height={320} />
            )}
          </div>
        </div>

        {/* Quick Actions & Shop Info */}
        <div className="dashboard-sidebar-column">
          <div className="quick-actions-card">
            <h3 className="section-title">Quick Actions</h3>
            <p className="section-subtitle">Shortcuts for the counter</p>

            <div className="actions-button-list">
              <button
                type="button"
                className="action-tile action-voice"
                onClick={() => navigate('/voice')}
              >
                <div className="tile-icon-box voice-glow">🎙️</div>
                <div className="tile-text">
                  <span className="tile-title">Start Voice Khata</span>
                  <span className="tile-desc">Speak in Kannada, Hindi, or English</span>
                </div>
                <span className="tile-arrow">→</span>
              </button>

              <button
                type="button"
                className="action-tile"
                onClick={() => navigate('/customers')}
              >
                <div className="tile-icon-box">➕</div>
                <div className="tile-text">
                  <span className="tile-title">Add Customer</span>
                  <span className="tile-desc">Register new customer & contact</span>
                </div>
                <span className="tile-arrow">→</span>
              </button>

              <button
                type="button"
                className="action-tile"
                onClick={() => navigate('/transactions')}
              >
                <div className="tile-icon-box">📋</div>
                <div className="tile-text">
                  <span className="tile-title">View Transactions</span>
                  <span className="tile-desc">Review, confirm, or filter entries</span>
                </div>
                <span className="tile-arrow">→</span>
              </button>
            </div>
          </div>

          {/* Quick Counter Tip */}
          <div className="counter-tip-card">
            <div className="tip-header">
              <span className="tip-icon">💡</span>
              <span className="tip-title">Voice Khata Tip</span>
            </div>
            <p className="tip-content">
              Say customer aliases naturally! For instance: <em>"Meshtru ge 300 roopayi saala kotte"</em> — DukaanAI automatically identifies Suresh Kumar.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
