import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Cloud, Plus, X } from 'lucide-react';
import { API_BASE } from '../config';
import { Provider, AddToast } from '../types';
import { LoadingSpinner, SearchBar, Pagination, paginate } from './common';

export function Providers({ addToast }: { addToast: AddToast }) {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [formData, setFormData] = useState({ provider_type: 'aws', name: '', region: 'us-east-1', account_id: '' });

  useEffect(() => { fetchProviders(); }, []);

  const fetchProviders = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/providers`);
      setProviders(res.data.providers || []);
    } catch (e) {
      addToast('error', 'Failed to load providers');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post(`${API_BASE}/providers`, formData);
      setShowModal(false);
      addToast('success', `Provider "${formData.name}" created successfully`);
      fetchProviders();
    } catch (e) {
      addToast('error', 'Failed to create provider');
    }
  };

  const handleConnect = async (id: string) => {
    try {
      await axios.post(`${API_BASE}/providers/${id}/connect`);
      addToast('success', 'Provider connected');
      fetchProviders();
    } catch (e) {
      addToast('error', 'Failed to connect provider');
    }
  };

  const filtered = providers.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.provider_type.toLowerCase().includes(search.toLowerCase())
  );
  const paged = paginate(filtered, page);

  if (loading) return <LoadingSpinner />;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Cloud Providers</h1>
        <p className="page-subtitle">Manage your cloud provider connections</p>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Connected Providers</h3>
          <button className="btn btn-primary" onClick={() => setShowModal(true)} aria-label="Add provider">
            <Plus size={16} style={{ marginRight: 8 }} />
            Add Provider
          </button>
        </div>
        <SearchBar value={search} onChange={v => { setSearch(v); setPage(1); }} placeholder="Search providers..." />
        <div className="resource-list">
          {paged.map(provider => (
            <div key={provider.id} className="resource-item">
              <div className="resource-info">
                <div className="resource-icon">
                  <Cloud size={20} aria-hidden="true" />
                </div>
                <div>
                  <div className="resource-name">{provider.name}</div>
                  <div className="resource-type">{provider.provider_type} &bull; {provider.region}</div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span className={`resource-status ${provider.status}`}>
                  {provider.status}
                </span>
                {provider.status === 'disconnected' && (
                  <button className="btn btn-primary" onClick={() => handleConnect(provider.id)}>
                    Connect
                  </button>
                )}
              </div>
            </div>
          ))}
          {paged.length === 0 && (
            <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>
              {search ? 'No matching providers.' : 'No providers connected. Add one to get started.'}
            </p>
          )}
        </div>
        <Pagination total={filtered.length} page={page} onPageChange={setPage} />
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)} role="dialog" aria-modal="true" aria-label="Add Cloud Provider">
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">Add Cloud Provider</h3>
              <button className="icon-btn" onClick={() => setShowModal(false)} aria-label="Close">
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label" htmlFor="provider-type">Provider Type</label>
                  <select
                    id="provider-type"
                    className="form-select"
                    value={formData.provider_type}
                    onChange={e => setFormData({ ...formData, provider_type: e.target.value })}
                  >
                    <option value="aws">AWS</option>
                    <option value="azure">Azure</option>
                    <option value="gcp">Google Cloud</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="provider-name">Name</label>
                  <input
                    id="provider-name"
                    className="form-input"
                    value={formData.name}
                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                    placeholder="my-provider"
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="provider-region">Region</label>
                  <input
                    id="provider-region"
                    className="form-input"
                    value={formData.region}
                    onChange={e => setFormData({ ...formData, region: e.target.value })}
                    placeholder="us-east-1"
                    required
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Add Provider
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
