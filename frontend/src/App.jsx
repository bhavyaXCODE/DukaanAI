import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import { VoiceProvider } from './context/VoiceContext';
import Sidebar from './components/Sidebar';

import Dashboard from './pages/Dashboard';
import VoiceKhata from './pages/VoiceKhata';
import ScanBook from './pages/ScanBook';
import Customers from './pages/Customers';
import Transactions from './pages/Transactions';
import Promises from './pages/Promises';
import Reports from './pages/Reports';
import Settings from './pages/Settings';
import './App.css';

function App() {
  return (
    <AppProvider>
      <VoiceProvider>
        <BrowserRouter>
          <div className="app-container">
            {/* Fixed 260px Left Sidebar */}
            <Sidebar />

            {/* Scrollable Main Content Area */}
            <main className="main-content">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/voice" element={<VoiceKhata />} />
                <Route path="/scan" element={<ScanBook />} />
                <Route path="/customers" element={<Customers />} />
                <Route path="/transactions" element={<Transactions />} />
                <Route path="/promises" element={<Promises />} />
                <Route path="/reports" element={<Reports />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </main>
          </div>
        </BrowserRouter>
      </VoiceProvider>
    </AppProvider>
  );
}

export default App;
