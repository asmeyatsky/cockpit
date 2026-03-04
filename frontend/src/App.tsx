import React, { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import axios from 'axios';
import './config';
import { useToast } from './hooks/useToast';
import { ToastContainer } from './components/common';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './components/Dashboard';
import { Providers } from './components/Providers';
import { Resources } from './components/Resources';
import { Agents } from './components/Agents';
import { Costs } from './components/Costs';
import { Templates } from './components/Templates';
import { Workflows } from './components/Workflows';
import { SettingsPage } from './components/Settings';
import { AICopilot } from './components/AICopilot';
import { LoginPage } from './components/LoginPage';

function App() {
  const { toasts, addToast } = useToast();
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!localStorage.getItem('cockpit_token'));
  const [user, setUser] = useState<any>(() => {
    try { return JSON.parse(localStorage.getItem('cockpit_user') || 'null'); } catch { return null; }
  });

  const handleLogin = (token: string, userData: any) => {
    setIsAuthenticated(true);
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('cockpit_token');
    localStorage.removeItem('cockpit_user');
    delete axios.defaults.headers.common['Authorization'];
    setIsAuthenticated(false);
    setUser(null);
  };

  if (!isAuthenticated) {
    return (
      <>
        <LoginPage onLogin={handleLogin} />
        <ToastContainer toasts={toasts} />
      </>
    );
  }

  return (
    <BrowserRouter>
      <div className="app">
        <Sidebar />
        <main className="main-content">
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
            <span style={{ color: 'var(--text-secondary)', marginRight: 12, fontSize: 14, alignSelf: 'center' }}>
              {user?.username} ({user?.role})
            </span>
            <button className="btn btn-secondary" onClick={handleLogout} style={{ fontSize: 13, padding: '6px 14px' }}>
              Logout
            </button>
          </div>
          <Routes>
            <Route path="/" element={<Dashboard addToast={addToast} />} />
            <Route path="/providers" element={<Providers addToast={addToast} />} />
            <Route path="/resources" element={<Resources addToast={addToast} />} />
            <Route path="/agents" element={<Agents addToast={addToast} />} />
            <Route path="/costs" element={<Costs addToast={addToast} />} />
            <Route path="/templates" element={<Templates addToast={addToast} />} />
            <Route path="/workflows" element={<Workflows addToast={addToast} />} />
            <Route path="/settings" element={<SettingsPage addToast={addToast} />} />
          </Routes>
        </main>
        <AICopilot />
        <ToastContainer toasts={toasts} />
      </div>
    </BrowserRouter>
  );
}

export default App;
