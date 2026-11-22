import React from 'react';
import { formatINR } from '../services/api';
import './StatCard.css';

const StatCard = ({
  title,
  value,
  description,
  change,
  changeLabel = 'vs yesterday',
  gradient = 'blue',
  icon = '📈',
  isCurrency = false,
  loading = false,
}) => {
  const isPositive = typeof change === 'number' && change >= 0;

  const displayValue = () => {
    if (loading) return null;
    if (typeof value === 'number' && isCurrency) {
      return formatINR(value);
    }
    return value;
  };

  return (
    <div className={`stat-card gradient-${gradient} ${loading ? 'stat-card-loading' : ''}`}>
      {/* Top row: Title and Icon */}
      <div className="stat-card-header">
        <span className="stat-title">{title}</span>
        <div className="stat-icon-wrapper">
          <span className="stat-icon">{icon}</span>
        </div>
      </div>

      {/* Main Value */}
      <div className="stat-card-body">
        {loading ? (
          <div className="skeleton stat-value-skeleton" />
        ) : (
          <div className="stat-value">{displayValue()}</div>
        )}
      </div>

      {/* Footer: Change badge & Description */}
      <div className="stat-card-footer">
        {loading ? (
          <div className="skeleton stat-desc-skeleton" />
        ) : (
          <>
            {typeof change === 'number' && (
              <span className={`change-badge ${isPositive ? 'positive' : 'negative'}`}>
                {isPositive ? '↑' : '↓'} {Math.abs(change)}%
              </span>
            )}
            <span className="stat-description">
              {changeLabel && typeof change === 'number' ? changeLabel : description}
            </span>
          </>
        )}
      </div>
    </div>
  );
};

export default StatCard;
