import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Server, Play, Square, Trash2 } from 'lucide-react';
import { API_BASE } from '../config';
import { Resource, AddToast } from '../types';
import { LoadingSpinner, SearchBar, Pagination, paginate, ConfirmDialog } from './common';

export function Resources({ addToast }: { addToast: AddToast }) {
  const [resources, setResources] = useState<Resource[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [confirmAction, setConfirmAction] = useState<{ id: string; action: string; name: string } | null>(null);

  useEffect(() => { fetchResources(); }, []);

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
              {search ? 'No matching resources.' : 'Connect a provider to see its resources.'}
            </p>
          )}
        </div>
        <Pagination total={filtered.length} page={page} onPageChange={setPage} />
      </div>

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
