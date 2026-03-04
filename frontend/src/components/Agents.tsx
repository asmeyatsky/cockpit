import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Bot, Plus, X } from 'lucide-react';
import { API_BASE } from '../config';
import { Agent, AddToast } from '../types';
import { LoadingSpinner, SearchBar, Pagination, paginate } from './common';

export function Agents({ addToast }: { addToast: AddToast }) {
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
