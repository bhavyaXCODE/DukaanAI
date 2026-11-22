import React, { createContext, useContext, useState, useEffect } from 'react';

const AppContext = createContext();

export const AppProvider = ({ children }) => {
  const [demoMode, setDemoMode] = useState(
    process.env.REACT_APP_DEMO_MODE === 'false' ? false : true
  );

  const [currentLanguage, setCurrentLanguage] = useState(() => {
    return localStorage.getItem('dukaanai_lang') || 'kn-IN';
  });

  const [shopInfo, setShopInfo] = useState({
    id: parseInt(process.env.REACT_APP_SHOP_ID, 10) || 1,
    name: 'Sri Manjunatha Provision Store',
    ownerName: 'Ramesh Gowda',
    username: 'manjunatha_store',
    language: 'kn-IN',
    address: '4th Main, Near Bus Stop, Malleshwaram, Bengaluru',
    demoMode: true,
  });

  useEffect(() => {
    localStorage.setItem('dukaanai_lang', currentLanguage);
    setShopInfo((prev) => ({
      ...prev,
      language: currentLanguage,
      demoMode: demoMode,
    }));
  }, [currentLanguage, demoMode]);
// NEW: simple counter for cross‑page refresh signalling
const [refreshTrigger, setRefreshTrigger] = useState(0);
const incrementRefresh = () => setRefreshTrigger((c) => c + 1);

useEffect(() => {
  const handleGlobalRefresh = () => {
    setRefreshTrigger((c) => c + 1);
  };
  window.addEventListener('dukaanai:refresh', handleGlobalRefresh);
  return () => window.removeEventListener('dukaanai:refresh', handleGlobalRefresh);
}, []);

  const value = {
    shopInfo,
    setShopInfo,
    currentLanguage,
    setCurrentLanguage,
    demoMode,
    setDemoMode,
    // expose refresh utilities
    refreshTrigger,
    incrementRefresh,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};

export default AppContext;
