import React, { useState } from 'react';
import { AddToast } from '../types';

export function SettingsPage({ addToast }: { addToast: AddToast }) {
  const [apiUrl, setApiUrl] = useState(() => localStorage.getItem('cockpit_api_url') || 'http://localhost:8000/api');
  const [aiProvider, setAiProvider] = useState(() => localStorage.getItem('cockpit_ai_provider') || 'claude');

  const handleSave = () => {
    localStorage.setItem('cockpit_api_url', apiUrl);
    localStorage.setItem('cockpit_ai_provider', aiProvider);
    addToast('success', 'Settings saved');
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-subtitle">Configure your cockpit</p>
      </div>

      <div className="card">
        <h3 className="card-title">API Configuration</h3>
        <div className="form-group">
          <label className="form-label" htmlFor="settings-api-url">API URL</label>
          <input id="settings-api-url" className="form-input" value={apiUrl} onChange={e => setApiUrl(e.target.value)} />
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor="settings-ai-provider">AI Provider</label>
          <select id="settings-ai-provider" className="form-select" value={aiProvider} onChange={e => setAiProvider(e.target.value)}>
            <option value="claude">Claude</option>
            <option value="openai">OpenAI</option>
            <option value="gemini">Gemini</option>
          </select>
        </div>
        <button className="btn btn-primary" onClick={handleSave}>Save Settings</button>
      </div>
    </div>
  );
}
