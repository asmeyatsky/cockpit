import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Cloud, Server, Bot, DollarSign,
  Activity, FileText, GitBranch, Settings
} from 'lucide-react';

export function Sidebar() {
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
