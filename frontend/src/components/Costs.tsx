import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE } from '../config';
import { Provider, AddToast } from '../types';
import { LoadingSpinner } from './common';

export function Costs({ addToast }: { addToast: AddToast }) {
  const [costs, setCosts] = useState<any>(null);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [selectedProvider, setSelectedProvider] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProviders();
  }, []);

  const fetchProviders = async () => {
    try {
      const res = await axios.get(`${API_BASE}/providers`);
      const provs = res.data.providers || [];
      setProviders(provs);
      if (provs.length > 0) {
        setSelectedProvider(provs[0].id);
        fetchCosts(provs[0].id);
      } else {
        setLoading(false);
      }
    } catch (e) {
      addToast('error', 'Failed to load providers');
      setLoading(false);
    }
  };

  const fetchCosts = async (providerId: string) => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/costs/${providerId}`);
      setCosts(res.data);
    } catch (e) {
      addToast('error', 'Failed to load cost data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Cost Analysis</h1>
        <p className="page-subtitle">Monitor and optimize your cloud costs</p>
      </div>

      {providers.length > 1 && (
        <div className="form-group" style={{ marginBottom: 24 }}>
          <label className="form-label" htmlFor="cost-provider">Provider</label>
          <select id="cost-provider" className="form-select" value={selectedProvider}
            onChange={e => { setSelectedProvider(e.target.value); fetchCosts(e.target.value); }}>
            {providers.map(p => <option key={p.id} value={p.id}>{p.name} ({p.provider_type})</option>)}
          </select>
        </div>
      )}

      {providers.length === 0 ? (
        <div className="card">
          <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>
            No providers connected. Add a provider to see cost analysis.
          </p>
        </div>
      ) : (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">Current Month</div>
            <div className="stat-value">${costs?.current_month_cost?.amount || '0'}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Forecast</div>
            <div className="stat-value warning">${costs?.monthly_forecast?.amount || '0'}</div>
          </div>
        </div>
      )}
    </div>
  );
}
