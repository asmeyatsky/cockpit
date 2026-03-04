import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Server, Bell } from 'lucide-react';
import { API_BASE, WS_BASE } from '../config';
import { Provider, Resource, Agent, Notification, AddToast } from '../types';
import { LoadingSpinner } from './common';

export function Dashboard({ addToast }: { addToast: AddToast }) {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);

  // 1.6: Proper WebSocket cleanup
  useEffect(() => {
    fetchData();

    const wsToken = localStorage.getItem('cockpit_token');
    const ws = new WebSocket(`${WS_BASE}/ws${wsToken ? `?token=${wsToken}` : ''}`);

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
