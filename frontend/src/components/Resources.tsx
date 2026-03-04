import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Server, Plus, X, Play, Square, Trash2 } from 'lucide-react';
import { API_BASE } from '../config';
import { Provider, Resource, AddToast } from '../types';
import { LoadingSpinner, SearchBar, Pagination, paginate, ConfirmDialog } from './common';

export function Resources({ addToast }: { addToast: AddToast }) {
  const [resources, setResources] = useState<Resource[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [confirmAction, setConfirmAction] = useState<{ id: string; action: string; name: string } | null>(null);
  const [createForm, setCreateForm] = useState({
    provider_id: '', resource_type: 'vm', name: '', region: 'us-east-1', config: '{}'
  });

  useEffect(() => { fetchResources(); fetchProviders(); }, []);

  const fetchResources = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/resources`);
      setResources(res.data.resources || []);
    } catch (e) {
      addToast('error', 'Failed to load resources');
    } finally {
      setLoading(false);
    }
  };

  const fetchProviders = async () => {
    try {
      const res = await axios.get(`${API_BASE}/providers`);
      const provs = res.data.providers || [];
      setProviders(provs);
      if (provs.length > 0 && !createForm.provider_id) {
        setCreateForm(f => ({ ...f, provider_id: provs[0].id }));
      }
    } catch (_) {}
  };

  const handleAction = async (id: string, action: string) => {
    try {
      await axios.post(`${API_BASE}/resources/${id}/${action}`);
      addToast('success', `Resource ${action}ed successfully`);
      fetchResources();
    } catch (e) {
      addToast('error', `Failed to ${action} resource`);
    }
  };

  const handleTerminate = (id: string, name: string) => {
    setConfirmAction({ id, action: 'terminate', name });
  };

  const handleCreateResource = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      let config = {};
      try { config = JSON.parse(createForm.config); } catch (_) {}
      await axios.post(`${API_BASE}/resources`, {
        provider_id: createForm.provider_id,
        resource_type: createForm.resource_type,
        name: createForm.name,
        region: createForm.region,
        config,
      });
      setShowCreateModal(false);
      addToast('success', `Resource "${createForm.name}" created`);
      setCreateForm({ provider_id: providers[0]?.id || '', resource_type: 'vm', name: '', region: 'us-east-1', config: '{}' });
      fetchResources();
    } catch (e) {
      addToast('error', 'Failed to create resource');
    }
  };

  const filtered = resources.filter(r =>
    r.name.toLowerCase().includes(search.toLowerCase()) ||
    r.resource_type.toLowerCase().includes(search.toLowerCase())
  );
  const paged = paginate(filtered, page);

  if (loading) return <LoadingSpinner />;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Resources</h1>
        <p className="page-subtitle">Manage your infrastructure resources</p>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Resources</h3>
          <button className="btn btn-primary" onClick={() => setShowCreateModal(true)} aria-label="Create resource">
            <Plus size={16} style={{ marginRight: 8 }} />
            Create Resource
          </button>
        </div>
        <SearchBar value={search} onChange={v => { setSearch(v); setPage(1); }} placeholder="Search resources..." />
        <div className="resource-list">
          {paged.map(resource => (
            <div key={resource.id} className="resource-item">
              <div className="resource-info">
                <div className="resource-icon">
                  <Server size={20} aria-hidden="true" />
                </div>
                <div>
                  <div className="resource-name">{resource.name}</div>
                  <div className="resource-type">{resource.resource_type} &bull; {resource.region}</div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span className={`resource-status ${resource.state}`}>
                  {resource.state}
                </span>
                <div className="actions">
                  {resource.state === 'stopped' && (
                    <button className="icon-btn" onClick={() => handleAction(resource.id, 'start')} title="Start" aria-label={`Start ${resource.name}`}>
                      <Play size={16} />
                    </button>
                  )}
                  {resource.state === 'running' && (
                    <button className="icon-btn" onClick={() => handleAction(resource.id, 'stop')} title="Stop" aria-label={`Stop ${resource.name}`}>
                      <Square size={16} />
                    </button>
                  )}
                  <button className="icon-btn" onClick={() => handleTerminate(resource.id, resource.name)} title="Terminate" aria-label={`Terminate ${resource.name}`}>
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </div>
          ))}
          {paged.length === 0 && (
            <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>
              {search ? 'No matching resources.' : 'No resources yet. Create one to get started.'}
            </p>
          )}
        </div>
        <Pagination total={filtered.length} page={page} onPageChange={setPage} />
      </div>

      {/* Resource Creation Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)} role="dialog" aria-modal="true" aria-label="Create Resource">
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">Create Resource</h3>
              <button className="icon-btn" onClick={() => setShowCreateModal(false)} aria-label="Close">
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleCreateResource}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label" htmlFor="res-provider">Provider</label>
                  <select id="res-provider" className="form-select" value={createForm.provider_id}
                    onChange={e => setCreateForm({ ...createForm, provider_id: e.target.value })}>
                    {providers.map(p => <option key={p.id} value={p.id}>{p.name} ({p.provider_type})</option>)}
                  </select>
                  {providers.length === 0 && (
                    <p style={{ color: 'var(--warning)', fontSize: 12, marginTop: 4 }}>Add a provider first.</p>
                  )}
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="res-type">Resource Type</label>
                  <select id="res-type" className="form-select" value={createForm.resource_type}
                    onChange={e => setCreateForm({ ...createForm, resource_type: e.target.value })}>
                    <option value="vm">Virtual Machine</option>
                    <option value="database">Database</option>
                    <option value="storage">Storage</option>
                    <option value="network">Network</option>
                    <option value="container">Container</option>
                    <option value="kubernetes">Kubernetes Cluster</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="res-name">Name</label>
                  <input id="res-name" className="form-input" value={createForm.name}
                    onChange={e => setCreateForm({ ...createForm, name: e.target.value })}
                    placeholder="my-resource" required />
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="res-region">Region</label>
                  <input id="res-region" className="form-input" value={createForm.region}
                    onChange={e => setCreateForm({ ...createForm, region: e.target.value })}
                    placeholder="us-east-1" required />
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="res-config">Configuration (JSON)</label>
                  <input id="res-config" className="form-input" value={createForm.config}
                    onChange={e => setCreateForm({ ...createForm, config: e.target.value })}
                    placeholder='{"instance_type": "t3.medium"}' />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={providers.length === 0}>Create Resource</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <ConfirmDialog
        isOpen={!!confirmAction}
        title="Terminate Resource"
        message={`Are you sure you want to terminate "${confirmAction?.name}"? This action cannot be undone.`}
        onConfirm={() => {
          if (confirmAction) handleAction(confirmAction.id, confirmAction.action);
          setConfirmAction(null);
        }}
        onCancel={() => setConfirmAction(null)}
      />
    </div>
  );
}
