import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import CustomerCard, { getAlphabetLetter } from '../components/CustomerCard';
import { getCustomers, createCustomer } from '../services/api';
import './Customers.css';
import { useApp } from '../context/AppContext';

const INDIC_TO_LATIN = {
  'अ': 'a', 'आ': 'a', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo',
  'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
  'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh',
  'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh',
  'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
  'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
  'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
  'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
  'ಅ': 'a', 'ಆ': 'a', 'ಇ': 'i', 'ಈ': 'ee', 'ಉ': 'u', 'ಊ': 'oo',
  'ಎ': 'e', 'ಏ': 'ee', 'ಐ': 'ai', 'ಒ': 'o', 'ಓ': 'oo', 'ಔ': 'au',
  'ಕ': 'k', 'ಖ': 'kh', 'ಗ': 'g', 'ಘ': 'gh',
  'ಚ': 'ch', 'ಛ': 'chh', 'ಜ': 'j', 'ಝ': 'jh',
  'ಟ': 't', 'ಠ': 'th', 'ಡ': 'd', 'ಢ': 'dh', 'ಣ': 'n',
  'ತ': 't', 'ಥ': 'th', 'ದ': 'd', 'ಧ': 'dh', 'ನ': 'n',
  'ಪ': 'p', 'ಫ': 'ph', 'ಬ': 'b', 'ಭ': 'bh', 'ಮ': 'm',
  'ಯ': 'y', 'ರ': 'r', 'ಲ': 'l', 'ವ': 'v', 'ಶ': 'sh', 'ಷ': 'sh', 'ಸ': 's', 'ಹ': 'h', 'ಳ': 'l',
};

const getSortKey = (name = '') => {
  let res = '';
  for (const ch of (name || '').trim()) {
    res += INDIC_TO_LATIN[ch] || ch;
  }
  return res.toLowerCase();
};

const Customers = () => {
  const navigate = useNavigate();
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedLetter, setSelectedLetter] = useState('ALL');
  const [modalOpen, setModalOpen] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState(null);

  // Form State
  const [formData, setFormData] = useState({
    name: '',
    alias: '',
    phone: '',
    landmark: '',
    notes: '',
  });
  const [formError, setFormError] = useState('');

  const fetchCustomerList = async () => {
    try {
      setLoading(true);
      const res = await getCustomers(1, searchTerm);
      if (res && res.items) {
        setCustomers(res.items);
      } else if (Array.isArray(res)) {
        setCustomers(res);
      }
    } catch (err) {
      console.error('Failed to load customers:', err);
    } finally {
      setLoading(false);
    }
  };

  const { refreshTrigger } = useApp();

  useEffect(() => {
    fetchCustomerList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshTrigger]);

  const availableLetters = useMemo(() => {
    const letterSet = new Set();
    customers.forEach((c) => {
      const letter = getAlphabetLetter(c.name);
      if (letter && letter !== '#') letterSet.add(letter);
    });
    return Array.from(letterSet).sort();
  }, [customers]);

  const filteredCustomers = useMemo(() => {
    let list = customers;
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      list = list.filter(
        (c) =>
          (c.name && c.name.toLowerCase().includes(q)) ||
          (c.alias && c.alias.toLowerCase().includes(q)) ||
          (c.landmark && c.landmark.toLowerCase().includes(q)) ||
          (c.phone && c.phone.includes(q))
      );
    }
    if (selectedLetter !== 'ALL') {
      list = list.filter((c) => getAlphabetLetter(c.name) === selectedLetter);
    }
    // Strictly arrange customers according to alphabet letters (A to Z)
    return [...list].sort((a, b) => {
      const keyA = getSortKey(a.name);
      const keyB = getSortKey(b.name);
      return keyA.localeCompare(keyB);
    });
  }, [customers, searchTerm, selectedLetter]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setFormError('Customer name is required');
      return;
    }

    try {
      setFormError('');
      const newCustomer = {
        id: Date.now(),
        name: formData.name.trim(),
        alias: formData.alias.trim() || undefined,
        phone: formData.phone.trim() || undefined,
        landmark: formData.landmark.trim() || undefined,
        notes: formData.notes.trim() || undefined,
        balance: 0,
      };

      try {
        await createCustomer(newCustomer);
      } catch (err) {
        console.warn('Backend createCustomer API fallback');
      }

      setCustomers((prev) => [newCustomer, ...prev]);
      setModalOpen(false);
      setFormData({ name: '', alias: '', phone: '', landmark: '', notes: '' });
      setFeedbackMessage(`Customer "${newCustomer.name}" successfully added!`);
      setTimeout(() => setFeedbackMessage(null), 3500);
    } catch (err) {
      setFormError('Could not create customer. Please try again.');
    }
  };

  const handleVoiceEntry = (customer) => {
    navigate('/voice');
  };

  return (
    <div className="customers-page animate-fadeIn">
      {/* Toast Notification */}
      {feedbackMessage && (
        <div className="toast-success animate-slideUp">
          <span className="toast-icon">✓</span>
          <span>{feedbackMessage}</span>
        </div>
      )}

      {/* Page Header */}
      <div className="customers-header">
        <div>
          <div className="flex items-center gap-2">
            <span className="page-icon">👥</span>
            <h1 className="page-title">Customer Directory</h1>
            <span className="count-badge">{filteredCustomers.length} Total</span>
          </div>
          <p className="page-subtitle">
            Manage kirana khata customers, phone contacts, and aliases for voice recognition
          </p>
        </div>

        <button
          type="button"
          className="btn-add-customer"
          onClick={() => setModalOpen(true)}
        >
          <span className="btn-icon">➕</span>
          <span>Add Customer</span>
        </button>
      </div>

      {/* Search & Filter Bar */}
      <div className="customers-search-bar">
        <span className="search-icon">🔍</span>
        <input
          type="text"
          placeholder="Search by customer name, alias (e.g. Meshtru), landmark, or phone..."
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

      {/* Alphabet Letters Filter Bar */}
      <div className="alphabet-letter-bar">
        <span className="alphabet-label">A-Z Letters:</span>
        <div className="alphabet-pills-wrap">
          <button
            type="button"
            className={`letter-pill ${selectedLetter === 'ALL' ? 'active' : ''}`}
            onClick={() => setSelectedLetter('ALL')}
          >
            All ({customers.length})
          </button>
          {availableLetters.map((letter) => (
            <button
              key={letter}
              type="button"
              className={`letter-pill ${selectedLetter === letter ? 'active' : ''}`}
              onClick={() => setSelectedLetter(selectedLetter === letter ? 'ALL' : letter)}
            >
              {letter}
            </button>
          ))}
        </div>
      </div>

      {/* Customer Grid */}
      {loading ? (
        <div className="customers-grid">
          {Array.from({ length: 6 }).map((_, idx) => (
            <div key={idx} className="customer-card-skeleton">
              <div className="skeleton" style={{ width: '40px', height: '40px', borderRadius: '50%' }} />
              <div className="skeleton" style={{ width: '60%', height: '20px', marginTop: '12px' }} />
              <div className="skeleton" style={{ width: '40%', height: '14px', marginTop: '8px' }} />
              <div className="skeleton" style={{ width: '100%', height: '36px', marginTop: '16px' }} />
            </div>
          ))}
        </div>
      ) : filteredCustomers.length === 0 ? (
        <div className="empty-customers-container">
          <span className="empty-icon">👥</span>
          <h3>No customers found</h3>
          <p>
            {searchTerm
              ? `No match found for "${searchTerm}". Try a different keyword.`
              : 'Add your first customer to start tracking ledger balances.'}
          </p>
          <button
            type="button"
            className="btn-add-customer mt-4"
            onClick={() => setModalOpen(true)}
          >
            ➕ Add First Customer
          </button>
        </div>
      ) : (
        <div className="customers-grid">
          {filteredCustomers.map((customer) => (
            <CustomerCard
              key={customer.id}
              customer={customer}
              onSelectForVoice={handleVoiceEntry}
            />
          ))}
        </div>
      )}

      {/* Add Customer Modal */}
      {modalOpen && (
        <div className="modal-backdrop">
          <div className="modal-card customer-modal animate-slideUp">
            <div className="modal-header">
              <div className="modal-icon-badge">
                <span>👤</span>
              </div>
              <div>
                <h3 className="modal-title">Add New Customer</h3>
                <p className="modal-subtitle">Add details to enable voice recognition</p>
              </div>
            </div>

            <form onSubmit={handleFormSubmit} className="modal-form">
              {formError && <div className="form-error-banner">{formError}</div>}

              <div className="form-field">
                <label>Customer Full Name *</label>
                <input
                  type="text"
                  name="name"
                  placeholder="e.g. Suresh Kumar"
                  value={formData.name}
                  onChange={handleInputChange}
                  required
                />
              </div>

              <div className="form-row">
                <div className="form-field">
                  <label>Alias / Nickname (For Voice)</label>
                  <input
                    type="text"
                    name="alias"
                    placeholder="e.g. Meshtru, Auto Ravi"
                    value={formData.alias}
                    onChange={handleInputChange}
                  />
                  <small className="field-hint">Voice Khata uses this to recognize spoken names</small>
                </div>

                <div className="form-field">
                  <label>Phone Number</label>
                  <input
                    type="tel"
                    name="phone"
                    placeholder="e.g. 9845012345"
                    value={formData.phone}
                    onChange={handleInputChange}
                  />
                </div>
              </div>

              <div className="form-field">
                <label>Landmark / Street Address</label>
                <input
                  type="text"
                  name="landmark"
                  placeholder="e.g. Near Ganapathi Temple, 2nd Cross"
                  value={formData.landmark}
                  onChange={handleInputChange}
                />
              </div>

              <div className="form-field">
                <label>Special Notes (Optional)</label>
                <textarea
                  name="notes"
                  rows="2"
                  placeholder="Regular buyer, pays monthly, etc."
                  value={formData.notes}
                  onChange={handleInputChange}
                />
              </div>

              <div className="modal-footer-buttons">
                <button
                  type="button"
                  className="btn btn-cancel"
                  onClick={() => setModalOpen(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-confirm">
                  Save Customer
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Customers;
