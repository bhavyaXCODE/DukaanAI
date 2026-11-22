import React from 'react';
import { NavLink } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import './Sidebar.css';

const Sidebar = () => {
  const { shopInfo, currentLanguage, demoMode } = useApp();

  const navItems = [
    { path: '/', label: 'Dashboard', icon: '🏠' },
    { path: '/voice', label: 'Voice Khata', icon: '🎙️', highlight: true },
    { path: '/scan', label: 'Upload Khata', icon: '🖼️' },
    { path: '/customers', label: 'Customers', icon: '👥' },
    { path: '/transactions', label: 'Transactions', icon: '📋' },
    { path: '/promises', label: 'Promises', icon: '🤝' },
    { path: '/reports', label: 'Reports & Analytics', icon: '📊' },
    { path: '/settings', label: 'Settings', icon: '⚙️' },
  ];

  const getLanguageLabel = (lang) => {
    switch (lang) {
      case 'kn-IN':
        return 'ಕನ್ನಡ (KN)';
      case 'hi-IN':
        return 'हिंदी (HI)';
      case 'en-IN':
        return 'English (EN)';
      default:
        return lang;
    }
  };

  return (
    <aside className="sidebar">
      {/* Brand Header */}
      <div className="sidebar-brand">
        <div className="brand-icon-wrapper">
          <span className="brand-icon">🎙️</span>
          <div className="brand-glow" />
        </div>
        <div className="brand-text-container">
          <h1 className="brand-title">DukaanAI</h1>
          <p className="brand-subtitle">The Intelligent Voice Khata</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        <div className="nav-section-label">MAIN MENU</div>
        <ul className="nav-list">
          {navItems.map((item) => (
            <li key={item.path} className="nav-item">
              <NavLink
                to={item.path}
                className={({ isActive }) =>
                  `nav-link ${isActive ? 'active' : ''} ${item.highlight ? 'nav-link-highlight' : ''}`
                }
                end={item.path === '/'}
              >
                <span className="nav-icon">{item.icon}</span>
                <span className="nav-label">{item.label}</span>
                {item.highlight && <span className="voice-live-badge">LIVE</span>}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Footer Profile Card */}
      <div className="sidebar-footer">
        <div className="shop-profile-card">
          <div className="profile-header">
            <div className="profile-avatar">🏪</div>
            <div className="profile-info">
              <h4 className="shop-name" title={shopInfo.name}>
                {shopInfo.name}
              </h4>
              <p className="shop-username">@{shopInfo.username}</p>
            </div>
          </div>

          <div className="profile-meta">
            <div className="meta-badge lang-badge">
              <span className="meta-dot green" />
              <span>{getLanguageLabel(currentLanguage)}</span>
            </div>

            {demoMode && (
              <div className="meta-badge demo-badge">
                <span>Demo Mode</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
