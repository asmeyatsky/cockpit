import React, { useState } from 'react';
import axios from 'axios';
import { API_BASE } from '../config';

export function LoginPage({ onLogin }: { onLogin: (token: string, user: any) => void }) {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const url = isRegister ? `${API_BASE}/auth/register` : `${API_BASE}/auth/login`;
      const body = isRegister
        ? { username, email, password }
        : { username, password };
      const res = await axios.post(url, body);
      const { token, user } = res.data;
      localStorage.setItem('cockpit_token', token);
      localStorage.setItem('cockpit_user', JSON.stringify(user));
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      onLogin(token, user);
    } catch (e: any) {
      setError(e?.response?.data?.detail || (isRegister ? 'Registration failed' : 'Login failed'));
    } finally {
      setLoading(false);
    }
  };

  const toggleMode = () => {
    setIsRegister(!isRegister);
    setError('');
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg-primary)',
    }}>
      <div style={{ width: 400 }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <h1 style={{
            fontSize: 36, fontWeight: 700,
            background: 'var(--gradient)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>
            Cockpit
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: 8 }}>
            Agentic Cloud Modernization Platform
          </p>
        </div>
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: 20 }}>
            {isRegister ? 'Create Account' : 'Sign In'}
          </h3>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label" htmlFor="login-user">Username</label>
              <input
                id="login-user" className="form-input" value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="Enter username" required autoFocus
              />
            </div>
            {isRegister && (
              <div className="form-group">
                <label className="form-label" htmlFor="login-email">Email</label>
                <input
                  id="login-email" className="form-input" type="email" value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@example.com" required
                />
              </div>
            )}
            <div className="form-group">
              <label className="form-label" htmlFor="login-pass">Password</label>
              <input
                id="login-pass" className="form-input" type="password" value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Enter password" required
              />
            </div>
            {error && (
              <p style={{ color: 'var(--error)', fontSize: 14, marginBottom: 16 }}>{error}</p>
            )}
            <button
              type="submit" className="btn btn-primary"
              style={{ width: '100%', padding: 14 }}
              disabled={loading}
            >
              {loading
                ? (isRegister ? 'Creating account...' : 'Signing in...')
                : (isRegister ? 'Create Account' : 'Sign In')
              }
            </button>
          </form>
          <p style={{ textAlign: 'center', marginTop: 16, fontSize: 14, color: 'var(--text-secondary)' }}>
            {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
            <button
              onClick={toggleMode}
              style={{
                background: 'none', border: 'none', color: 'var(--accent)',
                cursor: 'pointer', fontSize: 14, padding: 0, textDecoration: 'underline',
              }}
            >
              {isRegister ? 'Sign In' : 'Register'}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
