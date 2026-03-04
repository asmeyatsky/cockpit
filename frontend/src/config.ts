import axios from 'axios';

export const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';
export const WS_BASE = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';

// Auth: configure axios to send JWT token with every request
const token = localStorage.getItem('cockpit_token');
if (token) {
  axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
}
