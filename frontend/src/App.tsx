import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { 
  Cloud, Server, Bot, DollarSign, 
  Activity, Plus, Play, Square, Trash2,
  MessageSquare, X, Send, Bell, Settings,
  FileText, GitBranch, Zap
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
    <div className="sidebar">
      <div className="logo">Cockpit</div>
      {navItems.map(item => (
        <Link
          key={item.path}
          to={item.path}
          className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
        >
          <item.icon size={20} />
          {item.label}
        </Link>
      ))}
    </div>
  );
}

function Dashboard() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);

  useEffect(() => {
    fetchData();
    setupWebSocket();
  }, []);

  const setupWebSocket = () => {
    const ws = new WebSocket(`${WS_BASE}/ws`);
    
    ws.onmessage = (event) => {
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
    };

    return () => ws.close();
  };

  const fetchData = async () => {
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
      console.error(e);
    }
  };

  const runningResources = resources.filter(r => r.state === 'running').length;
  const activeAgents = agents.filter(a => a.status === 'active').length;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">Overview of your cloud infrastructure</p>
      </div>

      {notifications.length > 0 && (
        <div className="notifications-bar">
          <Bell size={16} />
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
                  <Server size={20} />
                </div>
                <div>
                  <div className="resource-name">{resource.name}</div>
                  <div className="resource-type">{resource.resource_type} • {resource.region}</div>
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

function Providers() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({ provider_type: 'aws', name: '', region: 'us-east-1', account_id: '' });

  useEffect(() => {
    fetchProviders();
  }, []);

  const fetchProviders = async () => {
    try {
      const res = await axios.get(`${API_BASE}/providers`);
      setProviders(res.data.providers || []);
    } catch (e) {
      console.error(e);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post(`${API_BASE}/providers`, formData);
      setShowModal(false);
      fetchProviders();
    } catch (e) {
      console.error(e);
    }
  };

  const handleConnect = async (id: string) => {
    try {
      await axios.post(`${API_BASE}/providers/${id}/connect`);
      fetchProviders();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Cloud Providers</h1>
        <p className="page-subtitle">Manage your cloud provider connections</p>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Connected Providers</h3>
          <button className="btn btn-primary" onClick={() => setShowModal(true)}>
            <Plus size={16} style={{ marginRight: 8 }} />
            Add Provider
          </button>
        </div>
        <div className="resource-list">
          {providers.map(provider => (
            <div key={provider.id} className="resource-item">
              <div className="resource-info">
                <div className="resource-icon">
                  <Cloud size={20} />
                </div>
                <div>
                  <div className="resource-name">{provider.name}</div>
                  <div className="resource-type">{provider.provider_type} • {provider.region}</div>
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
          {providers.length === 0 && (
            <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>
              No providers connected. Add one to get started.
            </p>
          )}
        </div>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">Add Cloud Provider</h3>
              <button className="icon-btn" onClick={() => setShowModal(false)}>
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Provider Type</label>
                  <select 
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
                  <label className="form-label">Name</label>
                  <input 
                    className="form-input"
                    value={formData.name}
                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                    placeholder="my-provider"
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Region</label>
                  <input 
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

function Resources() {
  const [resources, setResources] = useState<Resource[]>([]);

  useEffect(() => {
    fetchResources();
  }, []);

  const fetchResources = async () => {
    try {
      const res = await axios.get(`${API_BASE}/resources`);
      setResources(res.data.resources || []);
    } catch (e) {
      console.error(e);
    }
  };

  const handleAction = async (id: string, action: string) => {
    try {
      await axios.post(`${API_BASE}/resources/${id}/${action}`);
      fetchResources();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Resources</h1>
        <p className="page-subtitle">Manage your infrastructure resources</p>
      </div>

      <div className="card">
        <div className="resource-list">
          {resources.map(resource => (
            <div key={resource.id} className="resource-item">
              <div className="resource-info">
                <div className="resource-icon">
                  <Server size={20} />
                </div>
                <div>
                  <div className="resource-name">{resource.name}</div>
                  <div className="resource-type">{resource.resource_type} • {resource.region}</div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span className={`resource-status ${resource.state}`}>
                  {resource.state}
                </span>
                <div className="actions">
                  {resource.state === 'stopped' && (
                    <button className="icon-btn" onClick={() => handleAction(resource.id, 'start')} title="Start">
                      <Play size={16} />
                    </button>
                  )}
                  {resource.state === 'running' && (
                    <button className="icon-btn" onClick={() => handleAction(resource.id, 'stop')} title="Stop">
                      <Square size={16} />
                    </button>
                  )}
                  <button className="icon-btn" onClick={() => handleAction(resource.id, 'terminate')} title="Terminate">
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </div>
          ))}
          {resources.length === 0 && (
            <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>
              No resources yet. Add a provider and create resources.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function Agents() {
  const [agents, setAgents] = useState<Agent[]>([]);

  useEffect(() => {
    fetchAgents();
  }, []);

  const fetchAgents = async () => {
    try {
      const res = await axios.get(`${API_BASE}/agents`);
      setAgents(res.data.agents || []);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">AI Agents</h1>
        <p className="page-subtitle">Manage your AI agents</p>
      </div>

      <div className="card">
        <div className="resource-list">
          {agents.map(agent => (
            <div key={agent.id} className="resource-item">
              <div className="resource-info">
                <div className="resource-icon">
                  <Bot size={20} />
                </div>
                <div>
                  <div className="resource-name">{agent.name}</div>
                  <div className="resource-type">{agent.provider} • {agent.model}</div>
                </div>
              </div>
              <span className={`resource-status ${agent.status}`}>
                {agent.status}
              </span>
            </div>
          ))}
          {agents.length === 0 && (
            <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>
              No agents configured.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function Costs() {
  const [costs, setCosts] = useState<any>(null);

  const fetchCosts = async () => {
    try {
      const res = await axios.get(`${API_BASE}/costs/sample-provider-id`);
      setCosts(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchCosts();
  }, []);

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Cost Analysis</h1>
        <p className="page-subtitle">Monitor and optimize your cloud costs</p>
      </div>

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
    </div>
  );
}

function Templates() {
  const templates = [
    { id: '1', name: 'Web Server', description: 'EC2 with load balancer', provider: 'AWS' },
    { id: '2', name: 'Database', description: 'RDS PostgreSQL', provider: 'AWS' },
    { id: '3', name: 'Kubernetes', description: 'EKS cluster', provider: 'AWS' },
  ];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Templates</h1>
        <p className="page-subtitle">Infrastructure templates</p>
      </div>

      <div className="card">
        <div className="resource-list">
          {templates.map(template => (
            <div key={template.id} className="resource-item">
              <div className="resource-info">
                <div className="resource-icon">
                  <FileText size={20} />
                </div>
                <div>
                  <div className="resource-name">{template.name}</div>
                  <div className="resource-type">{template.description}</div>
                </div>
              </div>
              <button className="btn btn-primary">Deploy</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Workflows() {
  const workflows = [
    { id: '1', name: 'Deploy App', description: 'Build and deploy to production', status: 'active' },
    { id: '2', name: 'Scale Infrastructure', description: 'Auto-scale based on load', status: 'active' },
  ];

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
                  <GitBranch size={20} />
                </div>
                <div>
                  <div className="resource-name">{workflow.name}</div>
                  <div className="resource-type">{workflow.description}</div>
                </div>
              </div>
              <button className="btn btn-primary">
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

function Settings() {
  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-subtitle">Configure your cockpit</p>
      </div>

      <div className="card">
        <h3 className="card-title">API Configuration</h3>
        <div className="form-group">
          <label className="form-label">API URL</label>
          <input className="form-input" defaultValue="http://localhost:8000/api" />
        </div>
        <div className="form-group">
          <label className="form-label">AI Provider</label>
          <select className="form-select">
            <option value="claude">Claude</option>
            <option value="openai">OpenAI</option>
            <option value="gemini">Gemini</option>
          </select>
        </div>
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
      content: "Hi! I'm your AI infrastructure co-pilot. You can ask me to:\n\n• Create cloud providers and resources\n• Start, stop, or terminate instances\n• Analyze costs and generate reports\n• Configure monitoring and alerts\n\nWhat would you like to do?",
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
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
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

    setMessages(prev => [...prev, userMessage]);
    ws.send(JSON.stringify({ type: 'message', content: input }));
    setInput('');
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.95 }}
          className="copilot-panel"
        >
          <div className="copilot-header">
            <MessageSquare size={20} />
            <span className="copilot-title">AI Co-pilot</span>
            <button 
              className="icon-btn" 
              style={{ marginLeft: 'auto', background: 'rgba(255,255,255,0.1)' }}
              onClick={() => setIsOpen(false)}
            >
              <X size={16} />
            </button>
          </div>
          
          <div className="copilot-messages">
            {messages.map(msg => (
              <div key={msg.id} className={`message ${msg.role}`}>
                <div className="message-content">
                  {msg.content.split('\n').map((line, i) => (
                    <React.Fragment key={i}>
                      {line}
                      {i < msg.content.split('\n').length - 1 && <br />}
                    </React.Fragment>
                  ))}
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
            />
            <button onClick={handleSend}>
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
  return (
    <BrowserRouter>
      <div className="app">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/providers" element={<Providers />} />
            <Route path="/resources" element={<Resources />} />
            <Route path="/agents" element={<Agents />} />
            <Route path="/costs" element={<Costs />} />
            <Route path="/templates" element={<Templates />} />
            <Route path="/workflows" element={<Workflows />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
        <AICopilot />
      </div>
    </BrowserRouter>
  );
}

export default App;
