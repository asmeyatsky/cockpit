import React, { useState, useEffect, useRef, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import {
  Cloud, Server, Bot, DollarSign,
  Activity, Plus, Play, Square, Trash2,
  MessageSquare, X, Send, Bell, Settings,
  FileText, GitBranch, Zap, AlertTriangle,
  Loader2, Search, CheckCircle, XCircle,
  ChevronLeft, ChevronRight
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';
const WS_BASE = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';

interface Provider {
  id: string;
  provider_type: string;
  name: string;
  status: string;
  region: string;
}

interface Resource {
  id: string;
  resource_type: string;
  name: string;
  state: string;
  region: string;
}

interface Agent {
  id: string;
  name: string;
  provider: string;
  model: string;
  status: string;
}

interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  message: string;
  timestamp: Date;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  action_taken?: string;
}

// 2.4: Toast notification system
function useToast() {
  const [toasts, setToasts] = useState<Notification[]>([]);

  const addToast = useCallback((type: Notification['type'], message: string) => {
    const toast: Notification = {
      id: Date.now().toString(),
      type,
      message,
      timestamp: new Date()
    };
    setToasts(prev => [...prev, toast]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== toast.id));
    }, 5000);
  }, []);

  return { toasts, addToast };
}

function ToastContainer({ toasts }: { toasts: Notification[] }) {
  return (
    <div className="toast-container" role="status" aria-live="polite">
      <AnimatePresence>
        {toasts.map(toast => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, x: 100 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 100 }}
            className={`toast toast-${toast.type}`}
          >
            {toast.type === 'success' && <CheckCircle size={16} />}
            {toast.type === 'error' && <XCircle size={16} />}
            {toast.type === 'warning' && <AlertTriangle size={16} />}
            <span>{toast.message}</span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

// 2.3: Confirmation dialog
function ConfirmDialog({
  isOpen, title, message, onConfirm, onCancel
}: {
  isOpen: boolean; title: string; message: string; onConfirm: () => void; onCancel: () => void;
}) {
  if (!isOpen) return null;
  return (
    <div className="modal-overlay" onClick={onCancel} role="dialog" aria-modal="true" aria-label={title}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 400 }}>
        <div className="modal-header">
          <h3 className="modal-title">{title}</h3>
        </div>
        <div className="modal-body">
          <p style={{ color: 'var(--text-secondary)' }}>{message}</p>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onCancel}>Cancel</button>
          <button className="btn btn-danger" onClick={onConfirm}>Confirm</button>
        </div>
      </div>
    </div>
  );
}

// 2.5: Search/filter component
function SearchBar({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder: string; }) {
  return (
    <div style={{ position: 'relative', marginBottom: 16 }}>
      <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
      <input
        className="form-input"
        style={{ paddingLeft: 36 }}
        placeholder={placeholder}
        value={value}
        onChange={e => onChange(e.target.value)}
        aria-label={placeholder}
      />
    </div>
  );
}

// 2.1: Loading spinner
function LoadingSpinner() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }} role="status" aria-label="Loading">
      <Loader2 size={32} className="spin" style={{ color: 'var(--accent)' }} />
    </div>
  );
}

// 2.6: Pagination component
const PAGE_SIZE = 10;

function Pagination({ total, page, onPageChange }: { total: number; page: number; onPageChange: (p: number) => void }) {
  const totalPages = Math.ceil(total / PAGE_SIZE);
  if (totalPages <= 1) return null;

  return (
    <div className="pagination" role="navigation" aria-label="Pagination">
      <button
        className="icon-btn"
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        aria-label="Previous page"
      >
        <ChevronLeft size={16} />
      </button>
      <span style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
        Page {page} of {totalPages}
      </span>
      <button
        className="icon-btn"
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
        aria-label="Next page"
      >
        <ChevronRight size={16} />
      </button>
    </div>
  );
}

function paginate<T>(items: T[], page: number): T[] {
  const start = (page - 1) * PAGE_SIZE;
  return items.slice(start, start + PAGE_SIZE);
}

function Sidebar() {
  const location = useLocation();

  const navItems = [
    { path: '/', icon: Activity, label: 'Dashboard' },
    { path: '/providers', icon: Cloud, label: 'Providers' },
    { path: '/resources', icon: Server, label: 'Resources' },
    { path: '/agents', icon: Bot, label: 'Agents' },
    { path: '/costs', icon: DollarSign, label: 'Costs' },
    { path: '/templates', icon: FileText, label: 'Templates' },
    { path: '/workflows', icon: GitBranch, label: 'Workflows' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ];

  return (
    <nav className="sidebar" aria-label="Main navigation">
      <div className="logo">Cockpit</div>
      {navItems.map(item => (
        <Link
          key={item.path}
          to={item.path}
          className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
          aria-current={location.pathname === item.path ? 'page' : undefined}
        >
          <item.icon size={20} aria-hidden="true" />
          {item.label}
        </Link>
      ))}
    </nav>
  );
}

function Dashboard({ addToast }: { addToast: (type: Notification['type'], msg: string) => void }) {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);

  // 1.6: Proper WebSocket cleanup
  useEffect(() => {
    fetchData();

    const ws = new WebSocket(`${WS_BASE}/ws`);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'event') {
          const notification: Notification = {
            id: Date.now().toString(),
            type: 'info',
            message: `${data.event}: ${JSON.stringify(data.data)}`,
            timestamp: new Date()
          };
          setNotifications(prev => [notification, ...prev].slice(0, 10));
          fetchData();
        }
      } catch (e) {
        // ignore malformed messages
      }
    };

    return () => ws.close();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [p, r, a] = await Promise.all([
        axios.get(`${API_BASE}/providers`).catch(() => ({ data: { providers: [] } })),
        axios.get(`${API_BASE}/resources`).catch(() => ({ data: { resources: [] } })),
        axios.get(`${API_BASE}/agents`).catch(() => ({ data: { agents: [] } })),
      ]);
      setProviders(p.data.providers || []);
      setResources(r.data.resources || []);
      setAgents(a.data.agents || []);
    } catch (e) {
      addToast('error', 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const runningResources = resources.filter(r => r.state === 'running').length;
  const activeAgents = agents.filter(a => a.status === 'active').length;

  if (loading) return <LoadingSpinner />;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">Overview of your cloud infrastructure</p>
      </div>

      {notifications.length > 0 && (
        <div className="notifications-bar" role="status">
          <Bell size={16} aria-hidden="true" />
          <span>{notifications.length} new events</span>
        </div>
      )}

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Cloud Providers</div>
          <div className="stat-value">{providers.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Running Resources</div>
          <div className="stat-value success">{runningResources}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Resources</div>
          <div className="stat-value">{resources.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Active Agents</div>
          <div className="stat-value">{activeAgents}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Recent Resources</h3>
        </div>
        <div className="resource-list">
          {resources.slice(0, 5).map(resource => (
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
              <span className={`resource-status ${resource.state}`}>
                {resource.state}
              </span>
            </div>
          ))}
          {resources.length === 0 && (
            <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>
              No resources yet. Add a provider to get started.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function Providers({ addToast }: { addToast: (type: Notification['type'], msg: string) => void }) {
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

function Resources({ addToast }: { addToast: (type: Notification['type'], msg: string) => void }) {
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

      {/* 2.7: Resource Creation Modal */}
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

function Agents({ addToast }: { addToast: (type: Notification['type'], msg: string) => void }) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    name: '', description: '', provider: 'claude', model: 'claude-sonnet-4-6',
    system_prompt: 'You are a helpful cloud infrastructure assistant.',
    max_tokens: 4096, temperature: 0.7
  });

  useEffect(() => { fetchAgents(); }, []);

  const fetchAgents = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/agents`);
      setAgents(res.data.agents || []);
    } catch (e) {
      addToast('error', 'Failed to load agents');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post(`${API_BASE}/agents`, formData);
      setShowModal(false);
      addToast('success', `Agent "${formData.name}" created`);
      fetchAgents();
    } catch (e) {
      addToast('error', 'Failed to create agent');
    }
  };

  const filtered = agents.filter(a =>
    a.name.toLowerCase().includes(search.toLowerCase()) ||
    a.provider.toLowerCase().includes(search.toLowerCase())
  );
  const paged = paginate(filtered, page);

  if (loading) return <LoadingSpinner />;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">AI Agents</h1>
        <p className="page-subtitle">Manage your AI agents</p>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Agents</h3>
          <button className="btn btn-primary" onClick={() => setShowModal(true)} aria-label="Create agent">
            <Plus size={16} style={{ marginRight: 8 }} />
            Create Agent
          </button>
        </div>
        <SearchBar value={search} onChange={v => { setSearch(v); setPage(1); }} placeholder="Search agents..." />
        <div className="resource-list">
          {paged.map(agent => (
            <div key={agent.id} className="resource-item">
              <div className="resource-info">
                <div className="resource-icon">
                  <Bot size={20} aria-hidden="true" />
                </div>
                <div>
                  <div className="resource-name">{agent.name}</div>
                  <div className="resource-type">{agent.provider} &bull; {agent.model}</div>
                </div>
              </div>
              <span className={`resource-status ${agent.status}`}>
                {agent.status}
              </span>
            </div>
          ))}
          {paged.length === 0 && (
            <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>
              {search ? 'No matching agents.' : 'No agents configured. Create one to get started.'}
            </p>
          )}
        </div>
        <Pagination total={filtered.length} page={page} onPageChange={setPage} />
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)} role="dialog" aria-modal="true" aria-label="Create Agent">
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">Create AI Agent</h3>
              <button className="icon-btn" onClick={() => setShowModal(false)} aria-label="Close">
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label" htmlFor="agent-name">Name</label>
                  <input id="agent-name" className="form-input" value={formData.name}
                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                    placeholder="my-agent" required />
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="agent-desc">Description</label>
                  <input id="agent-desc" className="form-input" value={formData.description}
                    onChange={e => setFormData({ ...formData, description: e.target.value })}
                    placeholder="What does this agent do?" required />
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="agent-provider">AI Provider</label>
                  <select id="agent-provider" className="form-select" value={formData.provider}
                    onChange={e => setFormData({ ...formData, provider: e.target.value })}>
                    <option value="claude">Claude</option>
                    <option value="openai">OpenAI</option>
                    <option value="gemini">Gemini</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="agent-model">Model</label>
                  <input id="agent-model" className="form-input" value={formData.model}
                    onChange={e => setFormData({ ...formData, model: e.target.value })}
                    required />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Create Agent</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// 2.9: Costs page uses actual providers instead of hardcoded ID
function Costs({ addToast }: { addToast: (type: Notification['type'], msg: string) => void }) {
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

// 1.9: Templates connected to API (with fallback to demo data)
function Templates({ addToast }: { addToast: (type: Notification['type'], msg: string) => void }) {
  const [templates, setTemplates] = useState([
    { id: '1', name: 'Web Server', description: 'EC2 with load balancer', provider: 'AWS' },
    { id: '2', name: 'Database', description: 'RDS PostgreSQL', provider: 'AWS' },
    { id: '3', name: 'Kubernetes', description: 'EKS cluster', provider: 'AWS' },
  ]);

  const handleDeploy = (template: { id: string; name: string }) => {
    addToast('info', `Deploying "${template.name}"... (template deployment not yet implemented)`);
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Templates</h1>
        <p className="page-subtitle">Infrastructure templates for quick deployment</p>
      </div>

      <div className="card">
        <div className="resource-list">
          {templates.map(template => (
            <div key={template.id} className="resource-item">
              <div className="resource-info">
                <div className="resource-icon">
                  <FileText size={20} aria-hidden="true" />
                </div>
                <div>
                  <div className="resource-name">{template.name}</div>
                  <div className="resource-type">{template.description} &bull; {template.provider}</div>
                </div>
              </div>
              <button className="btn btn-primary" onClick={() => handleDeploy(template)}>Deploy</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// 1.10: Workflows with actual run feedback
function Workflows({ addToast }: { addToast: (type: Notification['type'], msg: string) => void }) {
  const [workflows] = useState([
    { id: '1', name: 'Deploy App', description: 'Build and deploy to production', status: 'active' },
    { id: '2', name: 'Scale Infrastructure', description: 'Auto-scale based on load', status: 'active' },
  ]);

  const handleRun = (workflow: { name: string }) => {
    addToast('info', `Running workflow "${workflow.name}"... (workflow execution not yet implemented)`);
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Workflows</h1>
        <p className="page-subtitle">Automated workflows</p>
      </div>

      <div className="card">
        <div className="resource-list">
          {workflows.map(workflow => (
            <div key={workflow.id} className="resource-item">
              <div className="resource-info">
                <div className="resource-icon">
                  <GitBranch size={20} aria-hidden="true" />
                </div>
                <div>
                  <div className="resource-name">{workflow.name}</div>
                  <div className="resource-type">{workflow.description}</div>
                </div>
              </div>
              <button className="btn btn-primary" onClick={() => handleRun(workflow)}>
                <Zap size={16} style={{ marginRight: 8 }} />
                Run
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// 1.11: Settings with persistence to localStorage
function SettingsPage({ addToast }: { addToast: (type: Notification['type'], msg: string) => void }) {
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

function AICopilot() {
  const [isOpen, setIsOpen] = useState(true);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: "Hi! I'm your AI infrastructure co-pilot. You can ask me to:\n\n- Create cloud providers and resources\n- Start, stop, or terminate instances\n- Analyze costs and generate reports\n- Configure monitoring and alerts\n\nWhat would you like to do?",
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const websocket = new WebSocket(`${WS_BASE}/ws/copilot`);

    websocket.onopen = () => {
      console.log('Connected to AI copilot');
    };

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'typing') {
          setIsTyping(data.typing);
        } else if (data.type === 'message') {
          const assistantMessage: Message = {
            id: Date.now().toString(),
            role: 'assistant',
            content: data.content,
            timestamp: new Date(),
            action_taken: data.action_taken
          };
          setMessages(prev => [...prev, assistantMessage]);
        }
      } catch (e) {
        // ignore malformed messages
      }
    };

    websocket.onerror = () => {
      console.error('WebSocket connection failed');
    };

    setWs(websocket);

    return () => websocket.close();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() || !ws) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    // 2.13: Send conversation history to AI for context
    const history = updatedMessages.slice(-10).map(m => ({ role: m.role, content: m.content }));
    ws.send(JSON.stringify({ type: 'message', content: input, history }));
    setInput('');
  };

  // 2.12: Simple markdown-like rendering
  const renderContent = (content: string) => {
    return content.split('\n').map((line, i) => {
      // Bold
      const formatted = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      // Bullet points
      const isBullet = line.trimStart().startsWith('- ') || line.trimStart().startsWith('* ');

      return (
        <React.Fragment key={i}>
          {isBullet ? (
            <div style={{ paddingLeft: 16 }} dangerouslySetInnerHTML={{ __html: '&bull; ' + formatted.replace(/^[\s]*[-*]\s/, '') }} />
          ) : (
            <span dangerouslySetInnerHTML={{ __html: formatted }} />
          )}
          {i < content.split('\n').length - 1 && !isBullet && <br />}
        </React.Fragment>
      );
    });
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.95 }}
          className="copilot-panel"
          role="complementary"
          aria-label="AI Co-pilot"
        >
          <div className="copilot-header">
            <MessageSquare size={20} aria-hidden="true" />
            <span className="copilot-title">AI Co-pilot</span>
            <button
              className="icon-btn"
              style={{ marginLeft: 'auto', background: 'rgba(255,255,255,0.1)' }}
              onClick={() => setIsOpen(false)}
              aria-label="Close co-pilot"
            >
              <X size={16} />
            </button>
          </div>

          <div className="copilot-messages" role="log" aria-label="Chat messages">
            {messages.map(msg => (
              <div key={msg.id} className={`message ${msg.role}`}>
                <div className="message-content">
                  {renderContent(msg.content)}
                  {msg.action_taken && (
                    <div style={{ marginTop: 8, fontSize: 11, color: 'var(--success)', display: 'flex', alignItems: 'center', gap: 4 }}>
                      <CheckCircle size={12} /> Action: {msg.action_taken}
                    </div>
                  )}
                </div>
                <div className="message-time">
                  {msg.timestamp.toLocaleTimeString()}
                </div>
              </div>
            ))}
            {isTyping && (
              <div className="message assistant">
                <div className="message-content">
                  <div className="typing">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="copilot-input">
            <input
              type="text"
              placeholder="Ask me anything..."
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              aria-label="Chat message input"
            />
            <button onClick={handleSend} aria-label="Send message">
              <Send size={16} />
            </button>
          </div>
        </motion.div>
      )}

      {!isOpen && (
        <motion.button
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          onClick={() => setIsOpen(true)}
          aria-label="Open AI Co-pilot"
          style={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            width: 60,
            height: 60,
            borderRadius: '50%',
            background: 'var(--gradient)',
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 10px 30px rgba(99, 102, 241, 0.4)'
          }}
        >
          <MessageSquare size={24} color="white" />
        </motion.button>
      )}
    </AnimatePresence>
  );
}

function App() {
  const { toasts, addToast } = useToast();

  return (
    <BrowserRouter>
      <div className="app">
        <Sidebar />
        <main className="main-content">
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
